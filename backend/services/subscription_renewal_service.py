"""Transactional, durable, idempotent manual subscription renewal."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.services.subscription_grant import grant_subscription_period, paid_billing_anchor
from backend.services.subscription_period import utc_naive
from fastapi import HTTPException
from backend.services.subscription_calendar import (
    add_calendar_months,
)
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
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
            .with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if not tenant:
        raise SubscriptionRenewalError(404, "Tenant not found")

    receipt_key = "receipt:" + hashlib.sha256(request.idempotency_key.encode()).hexdigest()
    paid = (await db.execute(select(models.SubscriptionRenewalRequest).where(
        models.SubscriptionRenewalRequest.tenant_id == tenant_id,
        models.SubscriptionRenewalRequest.idempotency_key == receipt_key,
    ))).scalar_one_or_none()
    if paid:
        payment_id = json.loads(paid.response_json)["payment_id"]
        receipt = (await db.execute(select(models.SubscriptionPayment).where(
            models.SubscriptionPayment.id == payment_id,
            models.SubscriptionPayment.tenant_id == tenant_id,
        ))).scalar_one()
        if request.extension_days or request.new_end_date or (request.plan_id and request.plan_id != receipt.plan_id):
            raise SubscriptionRenewalError(409, "This key already granted a receipt period; a different extension needs a new operation")
        return {"tenant_id": tenant.id, "tenant_name": tenant.name, "plan": tenant.plan,
                "subscription_status": tenant.subscription_status,
                "subscription_end_date": tenant.subscription_end_date.isoformat(),
                "payment_id": payment_id, "is_idempotent_duplicate": True}

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
        if "tenant_id" not in result:
            raise SubscriptionRenewalError(409, "Operation identity belongs to a receipt, not a separate renewal")
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
        if not plan or (not plan.is_active and plan.id not in {tenant.plan_id, tenant.future_plan_id}):
            raise SubscriptionRenewalError(404, "Subscription plan not found")

    next_anchor = tenant.billing_day_anchor
    current_end = _utc(tenant.subscription_end_date) if tenant.subscription_end_date else None
    if request.new_end_date:
        calculated_end = _utc(request.new_end_date)
        if calculated_end <= now:
            raise SubscriptionRenewalError(
                400, "New subscription end date must be in the future"
            )
    elif request.extension_days:
        base = current_end if current_end and current_end > now else now
        calculated_end = base + timedelta(days=request.extension_days)
    else:
        # Default calendar month renewal with preserved billing day anchor
        base = current_end if current_end and current_end > now else now
        calc_end, anchor = add_calendar_months(
            base,
            months=1,
            anchor_day=paid_billing_anchor(tenant),
            tz_name=tenant.timezone or "Africa/Cairo",
        )
        calculated_end = _utc(calc_end)
        next_anchor = anchor

    old_status = current_state
    old_end = tenant.subscription_end_date
    try:
        await grant_subscription_period(db, tenant, plan, calculated_end, now=now, allow_unassigned=not request.plan_id)
    except HTTPException as exc:
        raise SubscriptionRenewalError(exc.status_code, exc.detail) from exc
    tenant.billing_day_anchor = next_anchor
    calculated_end = utc_naive(calculated_end)
    new_status = tenant.subscription_status

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
