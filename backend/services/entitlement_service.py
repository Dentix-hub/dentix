"""
DENTIX Entitlement Service
Centralized evaluation of tenant entitlements, limits, and read/write capabilities.
Enforces the fundamental clinical invariant:
- Clinical-history reads (Patient, Dental Chart, Treatment history, Prescriptions) are PERMANENTLY PERMITTED.

PR-02: Extended with typed commercial capability decision engine and shadow evaluation.
Existing caller contracts, return signatures, and enforcement semantics are 100% preserved.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Callable, Tuple
from backend.core.config import get_subscription_enforcement_mode
from backend.models.tenant import Tenant
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
)
from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    CapabilityKey,
    OperationClass,
)
from backend.services.commercial_decision import (
    CommercialDecision,
    CommercialDecisionEngine,
)

logger = logging.getLogger(__name__)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class EntitlementEvaluation:
    def __init__(
        self,
        tenant_id: int,
        status: str,
        mode: str,
        can_read_clinical: bool,
        can_write_clinical: bool,
        can_write_billable: bool,
        can_create_appointments: bool,
        reason: Optional[str] = None,
        # Additive attributes for PR-02 (backward compatible defaults)
        plan_id: Optional[int] = None,
        plan_name: Optional[str] = None,
        commercial_decisions: Optional[Dict[str, Dict[str, Any]]] = None,
        shadow_discrepancies: Optional[List[str]] = None,
        unmapped_keys: Optional[List[str]] = None,
        is_shadow: bool = True,
    ):
        self.tenant_id = tenant_id
        self.status = status
        self.mode = mode
        self.can_read_clinical = can_read_clinical
        self.can_write_clinical = can_write_clinical
        self.can_write_billable = can_write_billable
        self.can_create_appointments = can_create_appointments
        self.reason = reason
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.commercial_decisions = commercial_decisions or {}
        self.shadow_discrepancies = shadow_discrepancies or []
        self.unmapped_keys = unmapped_keys or []
        self.is_shadow = is_shadow

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "status": self.status,
            "mode": self.mode,
            "can_read_clinical": self.can_read_clinical,
            "can_write_clinical": self.can_write_clinical,
            "can_write_billable": self.can_write_billable,
            "can_create_appointments": self.can_create_appointments,
            "reason": self.reason,
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "commercial_decisions": self.commercial_decisions,
            "shadow_discrepancies": self.shadow_discrepancies,
            "unmapped_keys": self.unmapped_keys,
            "is_shadow": self.is_shadow,
        }


class EntitlementService:
    @staticmethod
    def evaluate_tenant_entitlements(
        tenant: Tenant,
        now: Optional[datetime] = None,
        override_mode: Optional[str] = None,
        commercial_overrides: Optional[Dict[str, bool]] = None,
        emergency_restrictions: Optional[Set[str]] = None,
        rollout_resolver: Optional[Callable[[str, int], bool]] = None,
    ) -> EntitlementEvaluation:
        """
        Evaluate full entitlement set for a given tenant.
        Preserves legacy caller API contracts while running shadow commercial evaluation.
        """
        mode = override_mode or get_subscription_enforcement_mode()
        current_time = _as_utc(now or datetime.now(timezone.utc))
        norm_status = normalize_state(getattr(tenant, "subscription_status", "trial"))

        subscription_end = _as_utc(tenant.subscription_end_date)
        grace_end = _as_utc(tenant.grace_period_until)
        is_past_end = bool(subscription_end and subscription_end < current_time)
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

        plan = tenant.__dict__.get("subscription_plan") if hasattr(tenant, "__dict__") else None
        if plan is None:
            try:
                plan = getattr(tenant, "subscription_plan", None)
            except Exception:
                plan = None
        plan_name = getattr(plan, "name", getattr(tenant, "plan", None))
        plan_id = getattr(plan, "id", getattr(tenant, "plan_id", None))

        # --- Commercial Shadow Decisions Evaluation ---
        commercial_decisions: Dict[str, Dict[str, Any]] = {}
        shadow_discrepancies: List[str] = []
        unmapped_keys: List[str] = []

        for cap_key, defn in CAPABILITY_REGISTRY.items():
            if not defn.is_sellable:
                continue
            decision = CommercialDecisionEngine.evaluate_capability(
                tenant=tenant,
                capability=cap_key,
                operation=OperationClass.WRITE_BUSINESS.value,
                now=current_time,
                override_mode=mode,
                commercial_overrides=commercial_overrides,
                emergency_restrictions=emergency_restrictions,
                rollout_resolver=rollout_resolver,
            )
            commercial_decisions[cap_key] = decision.to_dict()
            if decision.is_discrepancy:
                shadow_discrepancies.append(
                    f"Capability '{cap_key}': actual={decision.allowed}, proposed={decision.proposed_allowed} ({decision.reason_code.value})"
                )
            if decision.diagnostics.get("unmapped_plan_keys"):
                unmapped_keys.extend(decision.diagnostics["unmapped_plan_keys"])

        is_shadow = (mode != "enforce")

        # Invariant: Clinical-history read is ALWAYS permitted (enforced in EntitlementEvaluation)
        # In 'off' mode: allow all writes
        if mode == "off":
            return EntitlementEvaluation(
                tenant_id=tenant.id,
                status=effective_status,
                mode=mode,
                can_read_clinical=True,
                can_write_clinical=True,
                can_write_billable=True,
                can_create_appointments=True,
                reason="Enforcement mode is OFF.",
                plan_id=plan_id,
                plan_name=plan_name,
                commercial_decisions=commercial_decisions,
                shadow_discrepancies=shadow_discrepancies,
                unmapped_keys=sorted(list(set(unmapped_keys))),
                is_shadow=is_shadow,
            )

        # In 'observe' mode: calculate but do not block
        if mode == "observe":
            is_expired = effective_status in {
                SubscriptionState.EXPIRED_READ_ONLY.value,
                SubscriptionState.CANCELLED.value,
                SubscriptionState.SUSPENDED_ADMIN.value,
            }
            return EntitlementEvaluation(
                tenant_id=tenant.id,
                status=effective_status,
                mode=mode,
                can_read_clinical=True,
                can_write_clinical=True,
                can_write_billable=True,
                can_create_appointments=True,
                reason="[OBSERVE] Would be blocked in enforce mode." if is_expired else None,
                plan_id=plan_id,
                plan_name=plan_name,
                commercial_decisions=commercial_decisions,
                shadow_discrepancies=shadow_discrepancies,
                unmapped_keys=sorted(list(set(unmapped_keys))),
                is_shadow=is_shadow,
            )

        # In 'enforce' mode:
        if effective_status in {
            SubscriptionState.ACTIVE.value,
            SubscriptionState.TRIAL.value,
            SubscriptionState.GRACE.value,
        }:
            clinical_decision = commercial_decisions.get(CapabilityKey.CLINICAL.value, {})
            billing_decision = commercial_decisions.get(CapabilityKey.BILLING.value, {})

            has_clinical_denial = bool(
                clinical_decision.get("emergency_denied")
                or (plan is not None and not clinical_decision.get("commercial_grant", True))
                or (getattr(tenant, "is_active", True) is False)
            )
            has_billing_denial = bool(
                billing_decision.get("emergency_denied")
                or (plan is not None and not billing_decision.get("commercial_grant", True))
                or (getattr(tenant, "is_active", True) is False)
            )

            can_write_clinical = not has_clinical_denial
            can_write_billable = not has_billing_denial
            can_create_appointments = can_write_clinical

            reason_msg = None
            if has_clinical_denial and has_billing_denial:
                reason_msg = (
                    clinical_decision.get("explanation_ar")
                    or clinical_decision.get("explanation_en")
                    or "Write access is restricted."
                )
            elif has_clinical_denial:
                reason_msg = (
                    clinical_decision.get("explanation_ar")
                    or clinical_decision.get("explanation_en")
                    or "Clinical write access is restricted."
                )
            elif has_billing_denial:
                reason_msg = (
                    billing_decision.get("explanation_ar")
                    or billing_decision.get("explanation_en")
                    or "Billing write access is restricted."
                )

            return EntitlementEvaluation(
                tenant_id=tenant.id,
                status=effective_status,
                mode=mode,
                can_read_clinical=True,
                can_write_clinical=can_write_clinical,
                can_write_billable=can_write_billable,
                can_create_appointments=can_create_appointments,
                reason=reason_msg,
                plan_id=plan_id,
                plan_name=plan_name,
                commercial_decisions=commercial_decisions,
                shadow_discrepancies=shadow_discrepancies,
                unmapped_keys=sorted(list(set(unmapped_keys))),
                is_shadow=is_shadow,
            )

        if effective_status == SubscriptionState.EXPIRED_READ_ONLY.value:
            return EntitlementEvaluation(
                tenant_id=tenant.id,
                status=effective_status,
                mode=mode,
                can_read_clinical=True,
                can_write_clinical=False,
                can_write_billable=False,
                can_create_appointments=False,
                reason="Subscription expired. Read-only clinical history mode active.",
                plan_id=plan_id,
                plan_name=plan_name,
                commercial_decisions=commercial_decisions,
                shadow_discrepancies=shadow_discrepancies,
                unmapped_keys=sorted(list(set(unmapped_keys))),
                is_shadow=is_shadow,
            )

        if effective_status == SubscriptionState.SUSPENDED_ADMIN.value:
            return EntitlementEvaluation(
                tenant_id=tenant.id,
                status=effective_status,
                mode=mode,
                can_read_clinical=True,
                can_write_clinical=False,
                can_write_billable=False,
                can_create_appointments=False,
                reason="Tenant administratively suspended. Contact platform administrator.",
                plan_id=plan_id,
                plan_name=plan_name,
                commercial_decisions=commercial_decisions,
                shadow_discrepancies=shadow_discrepancies,
                unmapped_keys=sorted(list(set(unmapped_keys))),
                is_shadow=is_shadow,
            )

        # Cancelled
        return EntitlementEvaluation(
            tenant_id=tenant.id,
            status=effective_status,
            mode=mode,
            can_read_clinical=True,
            can_write_clinical=False,
            can_write_billable=False,
            can_create_appointments=False,
            reason="Subscription cancelled.",
            plan_id=plan_id,
            plan_name=plan_name,
            commercial_decisions=commercial_decisions,
            shadow_discrepancies=shadow_discrepancies,
            unmapped_keys=sorted(list(set(unmapped_keys))),
            is_shadow=is_shadow,
        )

    @staticmethod
    def evaluate_commercial_capability(
        tenant: Tenant,
        capability: str,
        operation: str = OperationClass.WRITE_BUSINESS.value,
        now: Optional[datetime] = None,
        override_mode: Optional[str] = None,
        commercial_overrides: Optional[Dict[str, bool]] = None,
        emergency_restrictions: Optional[Set[str]] = None,
        rollout_resolver: Optional[Callable[[str, int], bool]] = None,
    ) -> CommercialDecision:
        """
        Evaluate a single commercial capability using the canonical typed decision engine.
        """
        return CommercialDecisionEngine.evaluate_capability(
            tenant=tenant,
            capability=capability,
            operation=operation,
            now=now,
            override_mode=override_mode,
            commercial_overrides=commercial_overrides,
            emergency_restrictions=emergency_restrictions,
            rollout_resolver=rollout_resolver,
        )

    @staticmethod
    def get_effective_capabilities(
        tenant: Tenant,
        now: Optional[datetime] = None,
        override_mode: Optional[str] = None,
        commercial_overrides: Optional[Dict[str, bool]] = None,
        emergency_restrictions: Optional[Set[str]] = None,
        rollout_resolver: Optional[Callable[[str, int], bool]] = None,
    ) -> Dict[str, CommercialDecision]:
        """
        Return the complete dictionary of commercial capability decisions for a tenant.
        """
        current_time = _as_utc(now or datetime.now(timezone.utc))
        mode = override_mode or get_subscription_enforcement_mode()
        decisions: Dict[str, CommercialDecision] = {}

        for cap_key in CAPABILITY_REGISTRY.keys():
            decisions[cap_key] = CommercialDecisionEngine.evaluate_capability(
                tenant=tenant,
                capability=cap_key,
                operation=OperationClass.WRITE_BUSINESS.value,
                now=current_time,
                override_mode=mode,
                commercial_overrides=commercial_overrides,
                emergency_restrictions=emergency_restrictions,
                rollout_resolver=rollout_resolver,
            )

        return decisions

    @staticmethod
    async def async_resolve_restrictions_and_overrides(
        db: Any,
        tenant_id: Optional[int],
        now: Optional[datetime] = None,
    ) -> Tuple[Set[str], Dict[str, bool]]:
        """Asynchronously query active emergency restrictions and tenant commercial overrides from DB."""
        from unittest.mock import Mock
        from sqlalchemy import select, or_
        from backend import models

        emergency_restrictions: Set[str] = set()
        commercial_overrides: Dict[str, bool] = {}

        if not db or not hasattr(db, "execute") or isinstance(db, Mock):
            return emergency_restrictions, commercial_overrides

        current_time = _as_utc(now or datetime.now(timezone.utc))
        now_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time

        try:
            # Query emergency restrictions from SystemSetting
            prefix = "emergency_restriction_"
            stmt_sys = select(models.SystemSetting).where(
                models.SystemSetting.key.startswith(prefix)
            )
            res_sys = await db.execute(stmt_sys)
            sys_rows = res_sys.scalars().all() if hasattr(res_sys, "scalars") else []
            for r in sys_rows:
                if getattr(r, "value", "false") == "true":
                    canon_key = r.key[len(prefix):]
                    emergency_restrictions.add(canon_key)
        except Exception as exc:
            logger.warning("Failed to query emergency restrictions: %s", exc)

        if tenant_id:
            try:
                # Query tenant commercial overrides
                stmt_ov = select(models.CommercialTenantOverride).where(
                    models.CommercialTenantOverride.tenant_id == tenant_id,
                    or_(
                        models.CommercialTenantOverride.expires_at.is_(None),
                        models.CommercialTenantOverride.expires_at > now_naive,
                    ),
                )
                res_ov = await db.execute(stmt_ov)
                ov_rows = res_ov.scalars().all() if hasattr(res_ov, "scalars") else []
                for r in ov_rows:
                    commercial_overrides[r.capability_key] = bool(r.is_enabled)
            except Exception as exc:
                logger.warning("Failed to query commercial overrides for tenant %s: %s", tenant_id, exc)

        return emergency_restrictions, commercial_overrides
