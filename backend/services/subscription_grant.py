"""One non-committing period grant for paid receipts and manual renewals.

Callers must lock the tenant and commit the grant with its receipt/idempotency audit.
"""

from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select

from backend import models
from backend.services.account_admission_service import AccountAdmissionService
from backend.services.subscription_period import resolve_subscription_period, utc_naive
from backend.services.subscription_calendar import calculate_grace_period


def paid_billing_anchor(tenant):
    """First paid month anchors to its start, not the earlier registration date."""
    if tenant.subscription_status == "trial" and not tenant.future_plan_id:
        return None
    return tenant.billing_day_anchor


def is_plan_downgrade(current, target) -> bool:
    """Use the same capacity/price definition for receipt grants and admin assignment."""
    return bool(
        current
        and current.id != target.id
        and (
            (target.max_users is not None
             and (current.max_users is None or target.max_users < current.max_users))
            or target.ai_daily_limit < current.ai_daily_limit
            or target.price < current.price
        )
    )


async def grant_subscription_period(
    db, tenant, plan, end: datetime, *, now=None, allow_unassigned=False
):
    now = utc_naive(now or datetime.now(timezone.utc))
    period = resolve_subscription_period(tenant, now)
    old_end = (
        utc_naive(tenant.subscription_end_date)
        if tenant.subscription_end_date
        else None
    )
    if old_end and utc_naive(end) < old_end:
        raise HTTPException(
            400, "A renewal cannot shorten the existing subscription period"
        )
    current = (
        await db.execute(
            select(models.SubscriptionPlan).where(
                models.SubscriptionPlan.id
                == (tenant.future_plan_id if period.future_started else tenant.plan_id)
            )
        )
    ).scalar_one_or_none()
    if not plan:
        plan = (
            await db.get(models.SubscriptionPlan, tenant.future_plan_id)
            if tenant.future_plan_id
            else current
        )
    if not plan:
        if not allow_unassigned:
            raise HTTPException(409, "An explicit subscription plan is required")
        # Legacy dated extensions preserve their API without inventing a commercial plan.
        tenant.subscription_status = "active"
        tenant.subscription_end_date = utc_naive(end)
        tenant.grace_period_until = calculate_grace_period(utc_naive(end))
        return
    if tenant.scheduled_downgrade_plan_id:
        if plan.id not in {tenant.plan_id, tenant.scheduled_downgrade_plan_id}:
            raise HTTPException(
                409, "Resolve the scheduled downgrade before selecting a different plan"
            )
        plan = await db.get(models.SubscriptionPlan, tenant.scheduled_downgrade_plan_id)
    if not plan or not plan.is_active:
        # Existing retired contracts may renew; new assignments must be sellable.
        if not plan or plan.id not in {tenant.plan_id, tenant.future_plan_id}:
            raise HTTPException(409, "Target plan is not available for assignment")
    changed = current is None or current.id != plan.id
    if changed and plan.max_users is not None:
        used = await AccountAdmissionService.get_active_account_count(db, tenant.id)
        if used > plan.max_users:
            raise HTTPException(
                409,
                f"Deactivate accounts explicitly before selecting this plan: {used} active, limit {plan.max_users}",
            )
    lower = is_plan_downgrade(current, plan)
    pending = tenant.future_plan_id and not period.future_started
    if pending and plan.id != tenant.future_plan_id:
        raise HTTPException(
            409, "Resolve the existing future paid assignment before changing it"
        )
    if pending:
        pass  # Preserve the original future start when buying another month early.
    elif period.status == "trial" and old_end and old_end > now:
        # Even same-tier payment needs a paid-start marker; trial itself has no grace.
        tenant.future_plan_id = plan.id
        tenant.future_plan_start_date = old_end
    elif lower and old_end and old_end > now:
        tenant.future_plan_id = plan.id
        tenant.future_plan_start_date = old_end
        tenant.scheduled_downgrade_plan_id = plan.id
    else:
        tenant.plan_id = plan.id
        tenant.plan = plan.name
        tenant.subscription_status = "active"
        tenant.future_plan_id = None
        tenant.future_plan_start_date = None
        tenant.scheduled_downgrade_plan_id = None
    if lower and tenant.future_plan_id:
        tenant.scheduled_downgrade_plan_id = plan.id
    tenant.subscription_end_date = utc_naive(end)
    tenant.grace_period_until = utc_naive(calculate_grace_period(utc_naive(end)))
