"""
DENTIX Commercial Decision Engine.

Composes commercial plan grants, subscription lifecycle state, rollout availability,
emergency restrictions, and clinical history invariants into one typed, explainable
commercial decision with shadow evaluation support.

Formula:
allow = (is_clinical_history_read) OR
        (valid commercial grant AND
         operation allowed by subscription state AND
         rollout available AND
         no emergency restriction).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    CapabilityKey,
    OperationClass,
    canonicalize_capability_key,
    canonicalize_plan_name,
    is_sellable_capability,
)
from backend.core.config import get_subscription_enforcement_mode
from backend.services.commercial_adapter import resolve_effective_plan_capabilities
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class CommercialReasonCode(str, Enum):
    ALLOWED = "ALLOWED"
    CLINICAL_HISTORY_INVARIANT = "CLINICAL_HISTORY_INVARIANT"
    COMMERCIAL_GRANT_DISABLED = "COMMERCIAL_GRANT_DISABLED"
    CAPABILITY_NOT_SELLABLE = "CAPABILITY_NOT_SELLABLE"
    CAPABILITY_UNKNOWN = "CAPABILITY_UNKNOWN"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    EMERGENCY_RESTRICTION_ACTIVE = "EMERGENCY_RESTRICTION_ACTIVE"
    ROLLOUT_DISABLED = "ROLLOUT_DISABLED"
    MISSING_PLAN = "MISSING_PLAN"
    INVALID_PLAN_CONFIG = "INVALID_PLAN_CONFIG"


class CommercialDecision:
    """Typed result of a commercial capability decision."""

    def __init__(
        self,
        tenant_id: int,
        capability: str,
        operation: str,
        allowed: bool,
        proposed_allowed: bool,
        is_shadow: bool,
        mode: str,
        reason_code: CommercialReasonCode,
        explanation_en: str,
        explanation_ar: str,
        commercial_grant: bool,
        subscription_state_allowed: bool,
        rollout_allowed: bool,
        emergency_denied: bool,
        is_clinical_history_read: bool,
        plan_id: Optional[int] = None,
        plan_name: Optional[str] = None,
        policy_revision: int = 1,
        diagnostics: Optional[Dict[str, Any]] = None,
    ):
        self.tenant_id = tenant_id
        self.capability = capability
        self.operation = operation
        self.allowed = allowed
        self.proposed_allowed = proposed_allowed
        self.is_shadow = is_shadow
        self.mode = mode
        self.reason_code = reason_code
        self.explanation_en = explanation_en
        self.explanation_ar = explanation_ar
        self.commercial_grant = commercial_grant
        self.subscription_state_allowed = subscription_state_allowed
        self.rollout_allowed = rollout_allowed
        self.emergency_denied = emergency_denied
        self.is_clinical_history_read = is_clinical_history_read
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.policy_revision = policy_revision
        self.diagnostics = diagnostics or {}

    @property
    def is_discrepancy(self) -> bool:
        """True if shadow mode actual allowed differs from proposed policy."""
        return self.allowed != self.proposed_allowed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "capability": self.capability,
            "operation": self.operation,
            "allowed": self.allowed,
            "proposed_allowed": self.proposed_allowed,
            "is_shadow": self.is_shadow,
            "is_discrepancy": self.is_discrepancy,
            "mode": self.mode,
            "reason_code": self.reason_code.value,
            "explanation_en": self.explanation_en,
            "explanation_ar": self.explanation_ar,
            "commercial_grant": self.commercial_grant,
            "subscription_state_allowed": self.subscription_state_allowed,
            "rollout_allowed": self.rollout_allowed,
            "emergency_denied": self.emergency_denied,
            "is_clinical_history_read": self.is_clinical_history_read,
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "policy_revision": self.policy_revision,
            "diagnostics": self.diagnostics,
        }


class CommercialDecisionEngine:
    """Evaluates commercial capability access with shadow mode support."""

    @staticmethod
    def evaluate_capability(
        tenant: Any,
        capability: str,
        operation: str = OperationClass.WRITE_BUSINESS.value,
        now: Optional[datetime] = None,
        override_mode: Optional[str] = None,
        commercial_overrides: Optional[Dict[str, bool]] = None,
        emergency_restrictions: Optional[Set[str]] = None,
        rollout_resolver: Optional[Callable[[str, int], bool]] = None,
        policy_revision: int = 1,
    ) -> CommercialDecision:
        """
        Evaluate single capability decision for a tenant.
        """
        tenant_id = getattr(tenant, "id", 0)
        mode = override_mode or get_subscription_enforcement_mode()
        current_time = _as_utc(now or datetime.now(timezone.utc))
        effective_revision = getattr(tenant, "policy_revision", policy_revision) or policy_revision

        canon_cap = canonicalize_capability_key(capability)
        diagnostics: Dict[str, Any] = {
            "raw_capability": capability,
            "canonical_capability": canon_cap,
            "mode": mode,
            "timestamp": current_time.isoformat() if current_time else None,
        }

        # 0. Capability Unknown check
        if not canon_cap or canon_cap not in CAPABILITY_REGISTRY:
            return CommercialDecision(
                tenant_id=tenant_id,
                capability=capability,
                operation=operation,
                allowed=True if mode in {"off", "observe"} else False,
                proposed_allowed=False,
                is_shadow=mode != "enforce",
                mode=mode,
                reason_code=CommercialReasonCode.CAPABILITY_UNKNOWN,
                explanation_en=f"Unknown capability '{capability}'.",
                explanation_ar=f"خاصية غير معروفة '{capability}'.",
                commercial_grant=False,
                subscription_state_allowed=False,
                rollout_allowed=False,
                emergency_denied=False,
                is_clinical_history_read=False,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        cap_defn = CAPABILITY_REGISTRY[canon_cap]

        # Subscription status & timestamps resolution
        raw_status = getattr(tenant, "subscription_status", "trial")
        norm_status = normalize_state(raw_status)
        sub_end = _as_utc(getattr(tenant, "subscription_end_date", None))
        grace_end = _as_utc(getattr(tenant, "grace_period_until", None))
        future_start = _as_utc(getattr(tenant, "future_plan_start_date", None))
        future_plan_id = getattr(tenant, "future_plan_id", None)

        is_past_end = bool(sub_end and sub_end < current_time)
        is_in_grace = bool(grace_end and current_time <= grace_end)
        has_future_started = bool(
            future_plan_id and future_start and current_time >= future_start
        )

        effective_status = norm_status
        if norm_status == SubscriptionState.TRIAL.value:
            if has_future_started:
                effective_status = SubscriptionState.ACTIVE.value
            elif is_past_end:
                effective_status = SubscriptionState.EXPIRED_READ_ONLY.value
        elif norm_status == SubscriptionState.ACTIVE.value:
            if is_past_end:
                effective_status = (
                    SubscriptionState.GRACE.value
                    if is_in_grace
                    else SubscriptionState.EXPIRED_READ_ONLY.value
                )
        elif norm_status == SubscriptionState.GRACE.value and not is_in_grace:
            effective_status = SubscriptionState.EXPIRED_READ_ONLY.value

        try:
            plan = getattr(tenant, "subscription_plan", None)
        except Exception:
            plan = tenant.__dict__.get("subscription_plan") if hasattr(tenant, "__dict__") else None
        plan_name = getattr(plan, "name", getattr(tenant, "plan", None))
        plan_id = getattr(plan, "id", getattr(tenant, "plan_id", None))

        if has_future_started:
            try:
                future_plan = getattr(tenant, "future_plan", None)
            except Exception:
                future_plan = tenant.__dict__.get("future_plan") if hasattr(tenant, "__dict__") else None
            if future_plan:
                plan = future_plan
                plan_name = getattr(future_plan, "name", plan_name)
                plan_id = future_plan.id

        diagnostics["effective_status"] = effective_status
        diagnostics["is_past_end"] = is_past_end
        diagnostics["is_in_grace"] = is_in_grace
        diagnostics["plan_name"] = plan_name
        diagnostics["plan_id"] = plan_id

        # 1. Clinical History Invariant
        is_history_read = (
            operation == OperationClass.READ_HISTORY.value
            and canon_cap == CapabilityKey.CLINICAL.value
        )
        if is_history_read:
            return CommercialDecision(
                tenant_id=tenant_id,
                capability=canon_cap,
                operation=operation,
                allowed=True,
                proposed_allowed=True,
                is_shadow=False,
                mode=mode,
                reason_code=CommercialReasonCode.CLINICAL_HISTORY_INVARIANT,
                explanation_en="Clinical history read is permanently permitted.",
                explanation_ar="الاطلاع على السجلات الطبية متاح بشكل دائم دون قيود تجارية.",
                commercial_grant=True,
                subscription_state_allowed=True,
                rollout_allowed=True,
                emergency_denied=False,
                is_clinical_history_read=True,
                plan_id=plan_id,
                plan_name=plan_name,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        # 2. Emergency Denial Check (Distinct hard restriction)
        emergency_denied = bool(
            emergency_restrictions and canon_cap in emergency_restrictions
        )
        if emergency_denied:
            diagnostics["emergency_restricted"] = True
            proposed_allowed = False
            reason_code = CommercialReasonCode.EMERGENCY_RESTRICTION_ACTIVE
            explanation_en = f"Capability '{canon_cap}' is disabled under platform emergency restriction."
            explanation_ar = f"الخاصية '{cap_defn.display_name_ar}' معطلة بأمر حظر طارئ للمنصة."
            allowed = True if mode in {"off", "observe"} else False

            return CommercialDecision(
                tenant_id=tenant_id,
                capability=canon_cap,
                operation=operation,
                allowed=allowed,
                proposed_allowed=proposed_allowed,
                is_shadow=mode != "enforce",
                mode=mode,
                reason_code=reason_code,
                explanation_en=explanation_en,
                explanation_ar=explanation_ar,
                commercial_grant=False,
                subscription_state_allowed=True,
                rollout_allowed=True,
                emergency_denied=True,
                is_clinical_history_read=False,
                plan_id=plan_id,
                plan_name=plan_name,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        # 3. Sellable capability check
        if not cap_defn.is_sellable:
            diagnostics["is_sellable"] = False
            proposed_allowed = False
            reason_code = CommercialReasonCode.CAPABILITY_NOT_SELLABLE
            explanation_en = f"Capability '{canon_cap}' is experimental or unproven for commercial launch."
            explanation_ar = f"الخاصية '{cap_defn.display_name_ar}' غير مفعّلة في الإصدار التجاري الحالي."
            allowed = True if mode in {"off", "observe"} else False

            return CommercialDecision(
                tenant_id=tenant_id,
                capability=canon_cap,
                operation=operation,
                allowed=allowed,
                proposed_allowed=proposed_allowed,
                is_shadow=mode != "enforce",
                mode=mode,
                reason_code=reason_code,
                explanation_en=explanation_en,
                explanation_ar=explanation_ar,
                commercial_grant=False,
                subscription_state_allowed=True,
                rollout_allowed=True,
                emergency_denied=False,
                is_clinical_history_read=False,
                plan_id=plan_id,
                plan_name=plan_name,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        # 4. Commercial Grant Check
        norm_features = resolve_effective_plan_capabilities(
            plan=plan,
            commercial_overrides=commercial_overrides,
        )
        commercial_grant = norm_features.capabilities.get(canon_cap, False)
        diagnostics["unmapped_plan_keys"] = norm_features.unmapped_keys
        diagnostics["plan_warnings"] = norm_features.warnings

        if not commercial_grant:
            if plan is None:
                reason_code = CommercialReasonCode.MISSING_PLAN
                explanation_en = "Tenant has no assigned subscription plan. Access denied."
                explanation_ar = "لا توجد باقة اشتراك مخصصة للعيادة. تم رفض الوصول."
            elif not norm_features.is_valid_config:
                reason_code = CommercialReasonCode.INVALID_PLAN_CONFIG
                explanation_en = f"Invalid or unrecognized plan configuration for '{plan_name}'."
                explanation_ar = f"إعدادات باقة غير صالحة للباقة '{plan_name}'."
            else:
                reason_code = CommercialReasonCode.COMMERCIAL_GRANT_DISABLED
                explanation_en = f"Capability '{canon_cap}' is not included in subscription plan '{plan_name}'."
                explanation_ar = f"الخاصية '{cap_defn.display_name_ar}' غير مشمولة في باقة الاشتراك '{plan_name}'."

            proposed_allowed = False
            allowed = True if mode in {"off", "observe"} else False

            return CommercialDecision(
                tenant_id=tenant_id,
                capability=canon_cap,
                operation=operation,
                allowed=allowed,
                proposed_allowed=proposed_allowed,
                is_shadow=mode != "enforce",
                mode=mode,
                reason_code=reason_code,
                explanation_en=explanation_en,
                explanation_ar=explanation_ar,
                commercial_grant=False,
                subscription_state_allowed=True,
                rollout_allowed=True,
                emergency_denied=False,
                is_clinical_history_read=False,
                plan_id=plan_id,
                plan_name=plan_name,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        # 5. Subscription Lifecycle State Check
        state_allowed = True
        state_reason = CommercialReasonCode.ALLOWED
        state_msg_en = "Operation permitted by active subscription."
        state_msg_ar = "العملية مسموح بها بموجب الاشتراك النشط."

        if effective_status in {
            SubscriptionState.ACTIVE.value,
            SubscriptionState.TRIAL.value,
            SubscriptionState.GRACE.value,
        }:
            state_allowed = True
        elif effective_status == SubscriptionState.EXPIRED_READ_ONLY.value:
            state_allowed = False
            state_reason = CommercialReasonCode.SUBSCRIPTION_EXPIRED
            state_msg_en = "Subscription expired. Only clinical history read is permitted."
            state_msg_ar = "انتهى اشتراك العيادة. متاح فقط قراءة السجلات الطبية."
        elif effective_status == SubscriptionState.SUSPENDED_ADMIN.value:
            state_allowed = False
            state_reason = CommercialReasonCode.TENANT_SUSPENDED
            state_msg_en = "Tenant is administratively suspended."
            state_msg_ar = "تم إيقاف حساب العيادة إدارياً."
        elif effective_status == SubscriptionState.CANCELLED.value:
            state_allowed = False
            state_reason = CommercialReasonCode.SUBSCRIPTION_CANCELLED
            state_msg_en = "Subscription has been cancelled."
            state_msg_ar = "تم إلغاء اشتراك العيادة."
        else:
            state_allowed = False
            state_reason = CommercialReasonCode.SUBSCRIPTION_EXPIRED
            state_msg_en = f"Unknown or expired subscription status '{effective_status}'."
            state_msg_ar = f"حالة اشتراك غير نشطة '{effective_status}'."

        if not state_allowed:
            proposed_allowed = False
            allowed = True if mode in {"off", "observe"} else False
            return CommercialDecision(
                tenant_id=tenant_id,
                capability=canon_cap,
                operation=operation,
                allowed=allowed,
                proposed_allowed=proposed_allowed,
                is_shadow=mode != "enforce",
                mode=mode,
                reason_code=state_reason,
                explanation_en=state_msg_en,
                explanation_ar=state_msg_ar,
                commercial_grant=True,
                subscription_state_allowed=False,
                rollout_allowed=True,
                emergency_denied=False,
                is_clinical_history_read=False,
                plan_id=plan_id,
                plan_name=plan_name,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        # 6. Rollout Check (if capability is bound to a feature flag)
        rollout_allowed = True
        if cap_defn.rollout_flag_key and rollout_resolver:
            try:
                rollout_allowed = rollout_resolver(cap_defn.rollout_flag_key, tenant_id)
            except Exception as e:
                diagnostics["rollout_resolver_error"] = str(e)
                rollout_allowed = False

        if not rollout_allowed:
            proposed_allowed = False
            allowed = True if mode in {"off", "observe"} else False
            return CommercialDecision(
                tenant_id=tenant_id,
                capability=canon_cap,
                operation=operation,
                allowed=allowed,
                proposed_allowed=proposed_allowed,
                is_shadow=mode != "enforce",
                mode=mode,
                reason_code=CommercialReasonCode.ROLLOUT_DISABLED,
                explanation_en=f"Capability '{canon_cap}' is disabled by clinical rollout policy.",
                explanation_ar=f"الخاصية '{cap_defn.display_name_ar}' معطلة ضمن سياسة التدريج العيادي.",
                commercial_grant=True,
                subscription_state_allowed=True,
                rollout_allowed=False,
                emergency_denied=False,
                is_clinical_history_read=False,
                plan_id=plan_id,
                plan_name=plan_name,
                policy_revision=effective_revision,
                diagnostics=diagnostics,
            )

        # 7. Final Grant: All conditions met
        proposed_allowed = True
        allowed = True  # Permitted in all modes
        return CommercialDecision(
            tenant_id=tenant_id,
            capability=canon_cap,
            operation=operation,
            allowed=allowed,
            proposed_allowed=proposed_allowed,
            is_shadow=mode != "enforce",
            mode=mode,
            reason_code=CommercialReasonCode.ALLOWED,
            explanation_en=f"Capability '{canon_cap}' authorized.",
            explanation_ar=f"الخاصية '{cap_defn.display_name_ar}' مفعّلة ومصرح بها.",
            commercial_grant=True,
            subscription_state_allowed=True,
            rollout_allowed=True,
            emergency_denied=False,
            is_clinical_history_read=False,
            plan_id=plan_id,
            plan_name=plan_name,
            policy_revision=effective_revision,
            diagnostics=diagnostics,
        )
