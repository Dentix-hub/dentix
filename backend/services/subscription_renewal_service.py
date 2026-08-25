"""Transactional, durable, idempotent manual subscription renewal."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
    validate_transition,
)


class SubscriptionRenewalError(ValueError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _request_hash(request: schemas.TenantManualRenewalRequest) -> str:
    payload = request.model_dump(mode="json", exclude={"idempotency_key"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def renew_subscription(
    db: AsyncSession,
    *,
    tenant_id: int,
    request: schemas.TenantManualRenewalRequest,
    admin: models.User,
) -> dict:
    request_hash = _request_hash(request)
    tenant = (
        await db.execute(
            select(models.Tenant)
            .where(
                models.Tenant.id == tenant_id,
                models.Tenant.is_deleted == False,  # noqa: E712
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not tenant:
        raise SubscriptionRenewalError(404, "Tenant not found")

    existing = (
        await db.execute(
            select(models.SubscriptionRenewalRequest).where(
                models.SubscriptionRenewalRequest.tenant_id == tenant_id,
                models.SubscriptionRenewalRequest.idempotency_key
                == request.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        if existing.request_hash != request_hash:
            raise SubscriptionRenewalError(
                409, "Idempotency key was already used for a different renewal request"
            )
        result = json.loads(existing.response_json)
        result["is_idempotent_duplicate"] = True
        return result

    current_state = normalize_state(tenant.subscription_status or "trial")
    if current_state in {
        SubscriptionState.SUSPENDED_ADMIN.value,
        SubscriptionState.CANCELLED.value,
    }:
        raise SubscriptionRenewalError(
            409,
            f"Manual renewal cannot reactivate a tenant in '{current_state}' state",
        )

    now = datetime.now(timezone.utc)
    plan = None
    if request.plan_id:
        plan = await db.get(models.SubscriptionPlan, request.plan_id)
        if not plan or not plan.is_active:
            raise SubscriptionRenewalError(404, "Subscription plan not found")

    current_end = _utc(tenant.subscription_end_date) if tenant.subscription_end_date else None
    if request.new_end_date:
        calculated_end = _utc(request.new_end_date)
        if calculated_end <= now:
            raise SubscriptionRenewalError(
                400, "New subscription end date must be in the future"
            )
    else:
        days = request.extension_days or (plan.duration_days if plan else 30)
        base = current_end if current_end and current_end > now else now
        calculated_end = base + timedelta(days=days)

    old_status = current_state
    new_status = validate_transition(old_status, SubscriptionState.ACTIVE.value)
    old_end = tenant.subscription_end_date
    if plan:
        tenant.plan_id = plan.id
        tenant.plan = plan.name
    tenant.subscription_status = new_status
    tenant.subscription_end_date = calculated_end
    tenant.grace_period_until = None
    # Account activation is deliberately independent. Never mutate is_active.

    result = {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "plan": tenant.plan,
        "subscription_status": new_status,
        "subscription_end_date": calculated_end.isoformat(),
        "is_idempotent_duplicate": False,
    }
    record = models.SubscriptionRenewalRequest(
        tenant_id=tenant.id,
        idempotency_key=request.idempotency_key,
        request_hash=request_hash,
        response_json=json.dumps(result, sort_keys=True),
        created_by_id=admin.id,
    )
    db.add(record)
    await db.flush()
    db.add(
        models.AuditLog(
            action="SUBSCRIPTION_MANUAL_RENEW",
            entity_type="Tenant",
            entity_id=tenant.id,
            target_username=tenant.name,
            performed_by_id=admin.id,
            performed_by_username=admin.username,
            old_value=f"status={old_status}, end_date={old_end}",
            new_value=f"status={new_status}, end_date={calculated_end}, plan={tenant.plan}",
            details=(
                f"Manual renewal request record {record.id}. "
                f"Notes: {request.notes or 'None'}"
            ),
            tenant_id=tenant.id,
        )
    )
    await db.commit()
    return result
