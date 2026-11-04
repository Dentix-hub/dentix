"""
DENTIX Entitlement Diagnostics Service.

Provides comprehensive, truthful read-only commercial entitlement diagnostics
for Super Admin inspection and tenant self-inspection.

Invariants (PR-03):
1. No patient identities, names, or prompt texts are returned (PII-free).
2. Missing usage measurement sources return None/unavailable (never coerced to 0).
3. Old AI logs are explicitly labelled as historical diagnostics only, never verified remaining quota.
4. Enforcement mode (off / observe / enforce) is accurately labelled for every capability.
5. Top-level plan_id is always provided.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import models
from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    LAUNCH_PLAN_SPECS,
    canonicalize_plan_name,
)
from backend.core.config import get_subscription_enforcement_mode
from backend.services.commercial_decision import (
    CommercialDecisionEngine,
    CommercialReasonCode,
)
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def build_tenant_entitlement_diagnostics(
    db: AsyncSession,
    tenant_id: int,
) -> Dict[str, Any]:
    """
    Build complete commercial access diagnostics for a given tenant.
    """
    # 1. Fetch Tenant and Plan
    stmt = (
        select(models.Tenant)
        .options(selectinload(models.Tenant.subscription_plan))
        .where(models.Tenant.id == tenant_id)
    )
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise ValueError(f"Tenant with ID {tenant_id} not found")

    plan = tenant.subscription_plan
    if not plan and tenant.plan_id:
        res_plan = await db.execute(
            select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == tenant.plan_id)
        )
        plan = res_plan.scalar_one_or_none()

    current_time = datetime.now(timezone.utc)
    mode = get_subscription_enforcement_mode()
    is_shadow = (mode != "enforce")

    # 2. Plan Identity & Specs
    raw_plan_name = getattr(plan, "name", tenant.plan)
    canon_plan_name = canonicalize_plan_name(raw_plan_name)
    tier_spec = LAUNCH_PLAN_SPECS.get(canon_plan_name) if canon_plan_name else None

    plan_display_ar = (
        getattr(plan, "display_name_ar", None)
        or (tier_spec.display_name_ar if tier_spec else "باقة غير معروفة")
    )
    plan_display_en = tier_spec.display_name_en if tier_spec else "Custom / Unknown Plan"
    plan_id = getattr(plan, "id", tenant.plan_id)

    # 3. Subscription Status & Timestamps
    raw_status = getattr(tenant, "subscription_status", "trial")
    norm_status = normalize_state(raw_status)
    sub_end = _as_utc(tenant.subscription_end_date)
    grace_end = _as_utc(tenant.grace_period_until)

    is_past_end = bool(sub_end and sub_end < current_time)
    is_in_grace = bool(grace_end and current_time <= grace_end)

    effective_status = norm_status
    if norm_status in {SubscriptionState.ACTIVE.value, SubscriptionState.TRIAL.value}:
        if is_past_end:
            effective_status = (
                SubscriptionState.GRACE.value
                if is_in_grace
                else SubscriptionState.EXPIRED_READ_ONLY.value
            )
    elif norm_status == SubscriptionState.GRACE.value and not is_in_grace:
        effective_status = SubscriptionState.EXPIRED_READ_ONLY.value

    # 4. Truthful Capacity Measurements
    # Active login accounts count (Users that are active and not deleted)
    stmt_users = select(func.count(models.User.id)).where(
        models.User.tenant_id == tenant_id,
        models.User.is_active == True,  # noqa: E712
        models.User.is_deleted == False,  # noqa: E712
    )
    active_users_count = (await db.execute(stmt_users)).scalar() or 0

    seat_limit = getattr(plan, "max_users", None)
    if seat_limit is None and tier_spec:
        seat_limit = tier_spec.max_active_users

    remaining_seats = max(0, seat_limit - active_users_count) if seat_limit is not None else None

    # AI Limits and Historical Diagnostic Count
    ai_daily_limit = getattr(plan, "ai_daily_limit", None)
    if ai_daily_limit is None and tier_spec:
        ai_daily_limit = tier_spec.ai_daily_limit
    elif ai_daily_limit is None:
        ai_daily_limit = 0

    is_ai_enabled = getattr(plan, "is_ai_enabled", None)
    if is_ai_enabled is None and tier_spec:
        is_ai_enabled = tier_spec.is_ai_enabled
    elif is_ai_enabled is None:
        is_ai_enabled = False

    # Historical AI requests logged today (diagnostic measurement only)
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    stmt_ai = select(func.count(models.AILog.id)).where(
        models.AILog.tenant_id == tenant_id,
        models.AILog.created_at >= today_start,
    )
    historical_ai_log_count = (await db.execute(stmt_ai)).scalar() or 0

    # 5. Capabilities Matrix
    capabilities_matrix: Dict[str, Dict[str, Any]] = {}
    configuration_warnings: List[str] = []

    if not plan and not canon_plan_name:
        configuration_warnings.append(
            "Tenant has no recognized subscription plan assigned. All commercial capabilities default to disabled."
        )

    # Active Commercial Overrides for this tenant
    active_overrides: Dict[str, bool] = {}
    if hasattr(models, "CommercialTenantOverride"):
        now_naive = current_time.replace(tzinfo=None)
        stmt_ov = select(models.CommercialTenantOverride).where(
            models.CommercialTenantOverride.tenant_id == tenant_id,
            or_(
                models.CommercialTenantOverride.expires_at.is_(None),
                models.CommercialTenantOverride.expires_at > now_naive,
            ),
        )
        ov_rows = (await db.execute(stmt_ov)).scalars().all()
        for r in ov_rows:
            if r.override_value == "allow":
                active_overrides[r.capability_key] = True
            elif r.override_value == "deny":
                active_overrides[r.capability_key] = False

    for cap_key, defn in CAPABILITY_REGISTRY.items():
        decision = CommercialDecisionEngine.evaluate_capability(
            tenant=tenant,
            capability=cap_key,
            operation="write_business",
            now=current_time,
            override_mode=mode,
            commercial_overrides=active_overrides,
        )

        enforcement_status = "not_enforced"
        if mode == "enforce":
            enforcement_status = "enforced"
        elif mode == "observe":
            enforcement_status = "observe_only"

        source = "plan_default"
        if decision.emergency_denied:
            source = "emergency_restriction"
        elif cap_key in active_overrides:
            source = "commercial_override"
        elif not decision.commercial_grant:
            source = "not_granted"

        capabilities_matrix[cap_key] = {
            "key": cap_key,
            "display_name_ar": defn.display_name_ar,
            "display_name_en": defn.display_name_en,
            "is_sellable": defn.is_sellable,
            "commercial_grant": decision.commercial_grant,
            "effective_allowed": decision.proposed_allowed,
            "proposed_allowed": decision.proposed_allowed,
            "runtime_allowed": decision.allowed,
            "is_shadow": decision.is_shadow,
            "is_discrepancy": decision.is_discrepancy,
            "reason_code": decision.reason_code.value,
            "explanation_ar": decision.explanation_ar,
            "explanation_en": decision.explanation_en,
            "enforcement_status": enforcement_status,
            "source": source,
        }

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "domain": tenant.domain,
        "is_active": tenant.is_active,
        "is_hard_disabled": not tenant.is_active,
        "timezone": getattr(tenant, "timezone", "Africa/Cairo") or "Africa/Cairo",

        # Plan & Subscription Lifecycle
        "plan_id": plan_id,
        "plan_name": raw_plan_name or "trial",
        "plan_display_name_ar": plan_display_ar,
        "plan_display_name_en": plan_display_en,
        "raw_subscription_status": raw_status,
        "effective_subscription_status": effective_status,
        "subscription_end_date": sub_end.isoformat() if sub_end else None,
        "grace_period_until": grace_end.isoformat() if grace_end else None,
        "is_past_end": is_past_end,
        "is_in_grace": is_in_grace,
        "policy_revision": getattr(tenant, "policy_revision", 1) or 1,

        # Enforcement & Modes
        "enforcement_mode": mode,
        "is_shadow": is_shadow,
        "can_read_clinical": True,  # Permanent invariant
        "can_write_clinical": (
            True if mode in {"off", "observe"}
            else effective_status in {SubscriptionState.ACTIVE.value, SubscriptionState.TRIAL.value, SubscriptionState.GRACE.value}
        ),
        "can_write_billable": (
            True if mode in {"off", "observe"}
            else effective_status in {SubscriptionState.ACTIVE.value, SubscriptionState.TRIAL.value, SubscriptionState.GRACE.value}
        ),
        "can_create_appointments": (
            True if mode in {"off", "observe"}
            else effective_status in {SubscriptionState.ACTIVE.value, SubscriptionState.TRIAL.value, SubscriptionState.GRACE.value}
        ),

        # Capacities & Measurements (PR-03 Trustworthy Standards)
        "capacities": {
            "seats": {
                "limit": seat_limit,
                "used": active_users_count,
                "remaining": remaining_seats,
                "unit": "active_login_accounts",
                "is_exhausted": bool(seat_limit is not None and active_users_count >= seat_limit),
            },
            "ai": {
                "is_enabled": is_ai_enabled,
                "daily_limit": ai_daily_limit,
                "historical_diagnostic_count": historical_ai_log_count,
                "historical_diagnostic_label": "Old AILog request count for today; historical diagnostics only",
                "quota_ledger_source": "unavailable",
                "quota_ledger_note": "Authoritative reservation ledger is pending implementation in PR-07; remaining quota is unavailable until then",
                "remaining_quota": None,  # NOT zero when unavailable!
                "window_reset": "clinic_local_midnight",
                "timezone": getattr(tenant, "timezone", "Africa/Cairo") or "Africa/Cairo",
            },
        },

        # Capabilities Matrix & Warnings
        "capabilities": capabilities_matrix,
        "configuration_warnings": configuration_warnings,
    }
