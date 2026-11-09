"""Shared guarded assignment for both existing super-admin API routes."""

from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from backend import models
from backend.services.account_admission_service import AccountAdmissionService
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
)
from backend.services.subscription_grant import is_plan_downgrade
from backend.services.subscription_period import resolve_subscription_period, utc_naive
from backend.services.subscription_calendar import add_plan_term


async def assign_plan(db, tenant_id, plan_id, current_user):
    stmt = select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update()
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    curr_state = normalize_state(tenant.subscription_status or "trial")
    if curr_state in {
        SubscriptionState.SUSPENDED_ADMIN.value,
        SubscriptionState.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot assign plan: tenant is in '{curr_state}' state. Explicit reactivation is required.",
        )

    res_plan = await db.execute(
        select(models.SubscriptionPlan)
        .where(models.SubscriptionPlan.id == plan_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    plan = res_plan.scalar_one_or_none()
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period = resolve_subscription_period(tenant, now)
    effective_plan_id = (
        tenant.future_plan_id if period.future_started else tenant.plan_id
    )
    current_plan = (
        await db.get(models.SubscriptionPlan, effective_plan_id)
        if effective_plan_id
        else None
    )
    if tenant.future_plan_id and plan.id != effective_plan_id:
        raise HTTPException(
            409, "Resolve the existing future paid assignment before changing it"
        )
    if is_plan_downgrade(current_plan, plan) and (
        tenant.subscription_end_date is None
        or utc_naive(tenant.subscription_end_date) > now
    ):
        raise HTTPException(
            409,
            "Downgrades take effect at renewal; use schedule-downgrade after reducing active accounts",
        )

    # Lower-cap assignment cannot bypass capacity rules (Task 2):
    active_count = await AccountAdmissionService.get_active_account_count(db, tenant.id)
    if plan.max_users is not None and active_count > plan.max_users:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot assign plan '{plan.name}': tenant currently has {active_count} active accounts, "
                f"which exceeds the target plan cap ({plan.max_users}). Deactivate or delete accounts first."
            ),
        )

    old_plan = tenant.plan
    tenant.plan = plan.name
    tenant.plan_id = plan.id
    # Preserves existing paid/trial time and NEVER alters is_active:
    if not tenant.subscription_end_date:
        try:
            tenant.subscription_end_date, tenant.billing_day_anchor = add_plan_term(
                now,
                plan,
                anchor_day=tenant.billing_day_anchor,
                tz_name=tenant.timezone or "Africa/Cairo",
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    db.add(
        models.AuditLog(
            action="TENANT_ASSIGN_PLAN",
            entity_type="Tenant",
            entity_id=tenant.id,
            target_username=tenant.name,
            performed_by_id=current_user.id,
            performed_by_username=current_user.username,
            old_value=f"plan={old_plan}",
            new_value=f"plan={plan.name}",
            tenant_id=tenant.id,
        )
    )

    await db.commit()
    await db.refresh(tenant)
    return tenant
