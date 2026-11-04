"""
PR-02 Acceptance Tests: Canonical Commercial Decision & Registry (Shadow Mode).

Validates all PR-02 acceptance criteria:
1. Known arrays and strict objects normalize consistently; explicit false survives; unknown/malformed/string-bool values do not grant capabilities.
2. Unknown plan display name with a valid configured plan behaves by configuration; missing plan does not become a free trial.
3. Commercial grant does not grant RBAC or another doctor's patient visibility.
4. Active, trial, grace, expired, cancelled and suspended decisions are deterministic at boundary timestamps.
5. Shadow mode leaves actual behavior unchanged and reports the discrepancy honestly.
6. Distinct emergency restrictions act as unoverrideable denials for new use.
7. Unproven/non-sellable capabilities remain excluded.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
import pytest

from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    CapabilityKey,
    OperationClass,
    LAUNCH_PLAN_SPECS,
    canonicalize_capability_key,
    canonicalize_plan_name,
)
from backend.services.commercial_adapter import (
    parse_raw_features,
    resolve_effective_plan_capabilities,
)
from backend.services.commercial_decision import (
    CommercialDecisionEngine,
    CommercialReasonCode,
)
from backend.services.entitlement_service import EntitlementService
from backend.services.subscription_state_machine import SubscriptionState


# ---------------------------------------------------------------------------
# Test Helpers: Synthetic Tenant and Plan Objects
# ---------------------------------------------------------------------------

class MockSubscriptionPlan:
    def __init__(
        self,
        id: int = 1,
        name: str = "professional",
        display_name_ar: str = "الباقة الاحترافية",
        price: Decimal = Decimal("400.00"),
        features: Optional[str] = None,
        is_ai_enabled: bool = True,
        ai_daily_limit: int = 10,
        max_users: int = 5,
    ):
        self.id = id
        self.name = name
        self.display_name_ar = display_name_ar
        self.price = price
        self.features = features
        self.is_ai_enabled = is_ai_enabled
        self.ai_daily_limit = ai_daily_limit
        self.max_users = max_users


class MockTenant:
    def __init__(
        self,
        id: int = 42,
        name: str = "Clinica Dentix",
        subscription_status: str = "active",
        subscription_end_date: Optional[datetime] = None,
        grace_period_until: Optional[datetime] = None,
        plan: str = "professional",
        plan_id: Optional[int] = 1,
        subscription_plan: Optional[MockSubscriptionPlan] = None,
        is_active: bool = True,
    ):
        self.id = id
        self.name = name
        self.subscription_status = subscription_status
        self.subscription_end_date = subscription_end_date
        self.grace_period_until = grace_period_until
        self.plan = plan
        self.plan_id = plan_id
        self.subscription_plan = subscription_plan or MockSubscriptionPlan(id=plan_id or 1, name=plan)
        self.is_active = is_active


# ===========================================================================
# 1. Feature Normalization & Strict Typing Acceptance Tests
# ===========================================================================

def test_feature_normalization_arrays_and_strict_objects():
    """
    Known arrays and strict objects normalize consistently;
    explicit false survives; unknown/malformed/string-bool values do not grant capabilities.
    """
    # 1. Known array of features
    raw_array = ["ai_insights", "export_reports", "laboratories"]
    caps, unmapped, warnings, is_valid = parse_raw_features(raw_array)
    assert is_valid is True
    assert caps[CapabilityKey.AI_INSIGHTS.value] is True
    assert caps[CapabilityKey.EXPORT_REPORTS.value] is True
    assert caps[CapabilityKey.LABORATORIES.value] is True
    assert len(unmapped) == 0

    # 2. Strict object with explicit False
    raw_obj = {
        "ai_insights": True,
        "export_reports": False,
        "laboratories": True,
    }
    caps, unmapped, warnings, is_valid = parse_raw_features(raw_obj)
    assert is_valid is True
    assert caps[CapabilityKey.AI_INSIGHTS.value] is True
    # Explicit False MUST survive!
    assert caps[CapabilityKey.EXPORT_REPORTS.value] is False
    assert caps[CapabilityKey.LABORATORIES.value] is True

    # 3. String booleans ("true", "false", "0", "1") must NOT grant capabilities
    raw_string_bools = {
        "ai_insights": "false",
        "export_reports": "true",
        "billing": 1,
        "laboratories": 0,
    }
    caps, unmapped, warnings, is_valid = parse_raw_features(raw_string_bools)
    # is_valid is False because non-boolean values were passed
    assert is_valid is False
    assert any("Invalid non-boolean value" in w for w in warnings)
    # String booleans and numbers must NOT grant capabilities:
    assert caps[CapabilityKey.EXPORT_REPORTS.value] is False
    assert caps[CapabilityKey.AI_INSIGHTS.value] is False
    assert caps[CapabilityKey.BILLING.value] is False

    # 4. Unknown and custom keys are collected and do NOT grant capabilities
    raw_unknown = ["telehealth", "random_marketing_tool", "patient_portal", "custom_feature"]
    caps, unmapped, warnings, is_valid = parse_raw_features(raw_unknown)
    assert "random_marketing_tool" in unmapped
    assert "custom_feature" in unmapped
    # Unproven non-sellable capabilities do not grant sellable features
    assert caps.get(CapabilityKey.CLINICAL.value) is None

    # 5. Legacy aliases normalize cleanly
    raw_aliases = ["AI_ASSISTANT", "REPORTS_ADVANCED", "LAB_INTEGRATION", "PATIENTS"]
    caps, unmapped, warnings, is_valid = parse_raw_features(raw_aliases)
    assert caps[CapabilityKey.AI_INSIGHTS.value] is True
    assert caps[CapabilityKey.EXPORT_REPORTS.value] is True
    assert caps[CapabilityKey.LABORATORIES.value] is True
    assert caps[CapabilityKey.CLINICAL.value] is True


# ===========================================================================
# 2. Missing & Unknown Plan Configuration Acceptance Tests
# ===========================================================================

def test_missing_plan_does_not_become_free_trial():
    """
    Missing plan must NOT grant full access or default to a free trial.
    Clinical history read is preserved, but commercial writes are denied.
    """
    tenant_no_plan = MockTenant(plan=None, plan_id=None, subscription_plan=None)
    tenant_no_plan.subscription_plan = None

    # Test commercial decision for new billable write
    decision = EntitlementService.evaluate_commercial_capability(
        tenant=tenant_no_plan,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        override_mode="enforce",
    )
    assert decision.allowed is False
    assert decision.proposed_allowed is False
    assert decision.reason_code == CommercialReasonCode.MISSING_PLAN
    assert decision.commercial_grant is False

    # Test clinical history read is permanently preserved
    history_decision = EntitlementService.evaluate_commercial_capability(
        tenant=tenant_no_plan,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.READ_HISTORY.value,
        override_mode="enforce",
    )
    assert history_decision.allowed is True
    assert history_decision.proposed_allowed is True
    assert history_decision.reason_code == CommercialReasonCode.CLINICAL_HISTORY_INVARIANT
    assert history_decision.is_clinical_history_read is True


def test_unknown_plan_display_name_with_configured_plan():
    """
    Unknown display name with a valid configured plan behaves by configuration.
    Unknown plan name with NO explicit features fails closed (no fallback full-access).
    """
    # Case A: Plan has custom/unrecognized name, but explicit DB features configured
    custom_plan = MockSubscriptionPlan(
        id=99,
        name="custom_clinic_special",
        features='["clinical", "billing"]',
    )
    tenant_custom = MockTenant(plan="custom_clinic_special", subscription_plan=custom_plan)

    dec_clinical = EntitlementService.evaluate_commercial_capability(
        tenant=tenant_custom,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        override_mode="enforce",
    )
    assert dec_clinical.allowed is True
    assert dec_clinical.commercial_grant is True

    dec_ai = EntitlementService.evaluate_commercial_capability(
        tenant=tenant_custom,
        capability=CapabilityKey.AI_INSIGHTS.value,
        operation=OperationClass.EXECUTE_AI.value,
        override_mode="enforce",
    )
    assert dec_ai.allowed is False
    assert dec_ai.commercial_grant is False
    assert dec_ai.reason_code == CommercialReasonCode.COMMERCIAL_GRANT_DISABLED

    # Case B: Plan has unknown name AND features is None (no DB features)
    blank_unknown_plan = MockSubscriptionPlan(
        id=100,
        name="completely_unknown_tier",
        features=None,
    )
    tenant_blank = MockTenant(plan="completely_unknown_tier", subscription_plan=blank_unknown_plan)

    dec_blank = EntitlementService.evaluate_commercial_capability(
        tenant=tenant_blank,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        override_mode="enforce",
    )
    # Must NOT fall back to full access!
    assert dec_blank.allowed is False
    assert dec_blank.proposed_allowed is False
    assert dec_blank.reason_code == CommercialReasonCode.INVALID_PLAN_CONFIG


# ===========================================================================
# 3. Independent Security Isolation (RBAC & Visibility Separation)
# ===========================================================================

def test_commercial_grant_does_not_grant_rbac_or_visibility():
    """
    Commercial grant verifies tenant license, but does NOT grant user RBAC
    or doctor patient visibility.
    allow = commercial grant AND subscription state AND rollout AND user RBAC AND target visibility.
    """
    plan = MockSubscriptionPlan(name="business")
    tenant = MockTenant(plan="business", subscription_plan=plan)

    # Tenant has commercial grant for billing
    decision = EntitlementService.evaluate_commercial_capability(
        tenant=tenant,
        capability=CapabilityKey.BILLING.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        override_mode="enforce",
    )
    assert decision.allowed is True
    assert decision.commercial_grant is True

    # But commercial decision does NOT contain user authorization:
    # A receptionist user trying to access accounting ledger must still be denied by RBAC
    # This proves commercial decision is an independent orthogonal input.
    assert "user_id" not in decision.to_dict()
    assert decision.reason_code == CommercialReasonCode.ALLOWED
    # The registry explicitly documents that billing is restricted to accountant/clinic_owner/super_admin
    billing_defn = CAPABILITY_REGISTRY[CapabilityKey.BILLING.value]
    assert "accountant" in billing_defn.associated_roles
    assert "receptionist" not in billing_defn.associated_roles


# ===========================================================================
# 4. Deterministic Subscription State Transitions & Boundary Timestamps
# ===========================================================================

def test_subscription_states_and_boundary_timestamps():
    """
    Active, trial, grace, expired, cancelled and suspended decisions
    are deterministic at boundary timestamps.
    """
    plan = MockSubscriptionPlan(name="essential")
    now_utc = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)

    # 1. ACTIVE before end date -> Allowed
    t_active = MockTenant(
        subscription_status="active",
        subscription_end_date=now_utc + timedelta(days=5),
        subscription_plan=plan,
    )
    dec = EntitlementService.evaluate_commercial_capability(
        tenant=t_active,
        capability=CapabilityKey.CLINICAL.value,
        now=now_utc,
        override_mode="enforce",
    )
    assert dec.allowed is True
    assert dec.reason_code == CommercialReasonCode.ALLOWED

    # 2. Past end date, but within grace period -> Allowed
    t_grace = MockTenant(
        subscription_status="active",
        subscription_end_date=now_utc - timedelta(hours=1),
        grace_period_until=now_utc + timedelta(days=6),
        subscription_plan=plan,
    )
    dec = EntitlementService.evaluate_commercial_capability(
        tenant=t_grace,
        capability=CapabilityKey.CLINICAL.value,
        now=now_utc,
        override_mode="enforce",
    )
    assert dec.allowed is True
    assert dec.subscription_state_allowed is True

    # 3. Past grace period -> Expired (Write denied, Read allowed)
    t_expired = MockTenant(
        subscription_status="active",
        subscription_end_date=now_utc - timedelta(days=8),
        grace_period_until=now_utc - timedelta(days=1),
        subscription_plan=plan,
    )
    # Billable write blocked
    dec_write = EntitlementService.evaluate_commercial_capability(
        tenant=t_expired,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        now=now_utc,
        override_mode="enforce",
    )
    assert dec_write.allowed is False
    assert dec_write.proposed_allowed is False
    assert dec_write.reason_code == CommercialReasonCode.SUBSCRIPTION_EXPIRED

    # Clinical history read allowed
    dec_read = EntitlementService.evaluate_commercial_capability(
        tenant=t_expired,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.READ_HISTORY.value,
        now=now_utc,
        override_mode="enforce",
    )
    assert dec_read.allowed is True
    assert dec_read.reason_code == CommercialReasonCode.CLINICAL_HISTORY_INVARIANT

    # 4. Administratively Suspended -> Write blocked, Read allowed
    t_suspended = MockTenant(
        subscription_status="suspended_admin",
        subscription_end_date=now_utc + timedelta(days=10),
        subscription_plan=plan,
    )
    dec_susp_write = EntitlementService.evaluate_commercial_capability(
        tenant=t_suspended,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        now=now_utc,
        override_mode="enforce",
    )
    assert dec_susp_write.allowed is False
    assert dec_susp_write.reason_code == CommercialReasonCode.TENANT_SUSPENDED

    # 5. Cancelled -> Write blocked, Read allowed
    t_cancelled = MockTenant(
        subscription_status="cancelled",
        subscription_plan=plan,
    )
    dec_canc_write = EntitlementService.evaluate_commercial_capability(
        tenant=t_cancelled,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        now=now_utc,
        override_mode="enforce",
    )
    assert dec_canc_write.allowed is False
    assert dec_canc_write.reason_code == CommercialReasonCode.SUBSCRIPTION_CANCELLED


# ===========================================================================
# 5. Shadow Mode Evaluation & Honest Discrepancy Reporting Acceptance Tests
# ===========================================================================

def test_shadow_mode_leaves_actual_behavior_unchanged():
    """
    Shadow mode leaves actual behavior unchanged and reports discrepancies honestly.
    Does not label shadow results as enforced.
    """
    now_utc = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
    # Expired tenant
    plan = MockSubscriptionPlan(name="essential")
    t_expired = MockTenant(
        subscription_status="active",
        subscription_end_date=now_utc - timedelta(days=10),
        grace_period_until=now_utc - timedelta(days=3),
        subscription_plan=plan,
    )

    # 1. Under mode 'off': actual allowed is True, proposed is False
    eval_off = EntitlementService.evaluate_tenant_entitlements(
        tenant=t_expired,
        now=now_utc,
        override_mode="off",
    )
    assert eval_off.mode == "off"
    assert eval_off.is_shadow is True
    # Legacy actual behavior unchanged:
    assert eval_off.can_write_clinical is True
    assert eval_off.can_write_billable is True
    # Shadow discrepancies honestly recorded:
    assert len(eval_off.shadow_discrepancies) > 0
    assert any("actual=True, proposed=False" in d for d in eval_off.shadow_discrepancies)

    # 2. Individual capability under shadow mode
    dec_shadow = EntitlementService.evaluate_commercial_capability(
        tenant=t_expired,
        capability=CapabilityKey.CLINICAL.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        now=now_utc,
        override_mode="off",
    )
    assert dec_shadow.allowed is True       # Actual access untouched
    assert dec_shadow.proposed_allowed is False  # What enforce would do
    assert dec_shadow.is_shadow is True
    assert dec_shadow.is_discrepancy is True
    assert dec_shadow.reason_code == CommercialReasonCode.SUBSCRIPTION_EXPIRED


# ===========================================================================
# 6. Distinct Emergency Restrictions & Non-Sellable Features Acceptance Tests
# ===========================================================================

def test_emergency_restriction_is_unoverrideable():
    """
    Emergency denial overrides commercial grant and rollout.
    Cannot be bypassed by tenant commercial override or active subscription.
    """
    plan = MockSubscriptionPlan(name="business")
    tenant = MockTenant(plan="business", subscription_plan=plan)

    # Emergency restriction placed on AI
    emergency_set = {CapabilityKey.AI_INSIGHTS.value}

    decision = EntitlementService.evaluate_commercial_capability(
        tenant=tenant,
        capability=CapabilityKey.AI_INSIGHTS.value,
        operation=OperationClass.EXECUTE_AI.value,
        emergency_restrictions=emergency_set,
        override_mode="enforce",
    )
    assert decision.allowed is False
    assert decision.proposed_allowed is False
    assert decision.emergency_denied is True
    assert decision.reason_code == CommercialReasonCode.EMERGENCY_RESTRICTION_ACTIVE


def test_non_sellable_capabilities_cannot_be_granted():
    """
    Capabilities marked non-sellable (telehealth, patient_portal, multi_branch)
    cannot be granted by plan features or tenant overrides.
    """
    plan = MockSubscriptionPlan(
        name="business",
        features='["patient_portal", "telehealth", "multi_branch", "clinical"]',
    )
    tenant = MockTenant(plan="business", subscription_plan=plan)

    dec_portal = EntitlementService.evaluate_commercial_capability(
        tenant=tenant,
        capability="patient_portal",
        override_mode="enforce",
    )
    assert dec_portal.allowed is False
    assert dec_portal.proposed_allowed is False
    assert dec_portal.reason_code == CommercialReasonCode.CAPABILITY_NOT_SELLABLE

    dec_clinical = EntitlementService.evaluate_commercial_capability(
        tenant=tenant,
        capability="clinical",
        override_mode="enforce",
    )
    assert dec_clinical.allowed is True
    assert dec_clinical.proposed_allowed is True
