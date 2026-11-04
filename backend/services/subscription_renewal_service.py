"""Transactional, durable, idempotent manual subscription renewal."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.commercial_registry import canonicalize_plan_name
from backend.services.subscription_calendar import (
    add_calendar_months,
    calculate_grace_period,
)
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
    elif request.extension_days:
        base = current_end if current_end and current_end > now else now
        calculated_end = base + timedelta(days=request.extension_days)
    else:
        # Default calendar month renewal with preserved billing day anchor
        base = current_end if current_end and current_end > now else now
        calc_end, anchor = add_calendar_months(
            base,
            months=1,
            anchor_day=tenant.billing_day_anchor,
            tz_name=tenant.timezone or "Africa/Cairo",
        )
        calculated_end = _utc(calc_end)
        tenant.billing_day_anchor = anchor

    # Task 10: Scheduled downgrade activation at renewal
    if tenant.scheduled_downgrade_plan_id:
        downgrade_plan = await db.get(
            models.SubscriptionPlan, tenant.scheduled_downgrade_plan_id
        )
        if downgrade_plan:
            from backend.services.account_admission_service import AccountAdmissionService

            active_count = await AccountAdmissionService.get_active_account_count(
                db, tenant.id
            )
            if (
                downgrade_plan.max_users is not None
                and active_count > downgrade_plan.max_users
            ):
                raise SubscriptionRenewalError(
                    400,
                    f"Cannot activate scheduled downgrade to '{downgrade_plan.name}': tenant currently has {active_count} active accounts, exceeding target limit of {downgrade_plan.max_users}. Deactivate accounts before renewal.",
                )
            plan = downgrade_plan
            tenant.scheduled_downgrade_plan_id = None

    old_status = current_state
    old_end = tenant.subscription_end_date

    # Task 6: Payment / renewal during trial preserves remaining trial days
    if current_state == SubscriptionState.TRIAL.value and current_end and current_end > now:
        new_status = SubscriptionState.TRIAL.value
        # If renewing plan differs from current trial plan (Professional), store as future assignment
        if plan and canonicalize_plan_name(plan.name) != canonicalize_plan_name(tenant.plan):
            tenant.future_plan_id = plan.id
            tenant.future_plan_start_date = current_end
        elif plan:
            tenant.plan_id = plan.id
            tenant.plan = plan.name
    else:
        new_status = validate_transition(old_status, SubscriptionState.ACTIVE.value)
        if plan:
            tenant.plan_id = plan.id
            tenant.plan = plan.name

    tenant.subscription_status = new_status
    tenant.subscription_end_date = calculated_end
    tenant.grace_period_until = calculate_grace_period(calculated_end)
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
