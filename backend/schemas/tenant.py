"""Tenant and subscription schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.utils.tenant_time import (
    DEFAULT_TENANT_TIMEZONE,
    validate_timezone_name,
)
from backend.core.money import NonNegativeMoney, PositiveMoney


class TenantBase(BaseModel):
    name: str
    subscription_status: Optional[str] = "active"
    logo: Optional[str] = None
    plan: Optional[str] = "trial"
    is_active: Optional[bool] = True
    subscription_end_date: Optional[datetime] = None
    grace_period_until: Optional[datetime] = None
    auto_suspend_at: Optional[datetime] = None
    backup_frequency: Optional[str] = "off"
    last_backup_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    timezone: str = DEFAULT_TENANT_TIMEZONE

    # Prescription Info
    doctor_name: Optional[str] = None
    doctor_title: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    contact_phone: Optional[str] = None
    print_header_image: Optional[str] = None
    print_footer_image: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return validate_timezone_name(value)


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_end_date: Optional[datetime] = None
    logo: Optional[str] = None
    timezone: Optional[str] = None

    # Backup & System
    backup_frequency: Optional[str] = None

    # Prescription Info
    doctor_name: Optional[str] = None
    doctor_title: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    contact_phone: Optional[str] = None
    print_header_image: Optional[str] = None
    print_footer_image: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return validate_timezone_name(value)


class Tenant(TenantBase):
    id: int
    created_at: datetime
    payment_failed_count: int = 0
    manual_override_reason: Optional[str] = None
    subscription_plan: Optional["SubscriptionPlan"] = None

    model_config = ConfigDict(from_attributes=True)


class TenantWithStats(Tenant):
    total_payments: Optional[float] = 0.0
    active_users_count: Optional[int] = 0
    patients_count: Optional[int] = 0
    days_remaining: Optional[int] = 0
    current_plan_name: Optional[str] = None


class ClinicRegistration(BaseModel):
    clinic_name: str
    admin_username: str
    admin_password: str
    contact_phone: str


class TenantManualRenewalRequest(BaseModel):
    plan_id: Optional[int] = None
    extension_days: Optional[int] = Field(default=None, gt=0, le=3650)
    new_end_date: Optional[datetime] = None
    idempotency_key: str = Field(min_length=8, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)


import json
from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    canonicalize_capability_key,
    is_sellable_capability,
)


def validate_plan_features_json(raw: Optional[str]) -> Optional[str]:
    """Strict validation for plan features JSON string."""
    if raw is None:
        return raw
    cleaned = raw.strip()
    if not cleaned:
        return raw

    if not cleaned.startswith(("{", "[")):
        raise ValueError("features must be a valid JSON array or object string")

    try:
        parsed = json.loads(cleaned)
    except Exception as exc:
        raise ValueError(f"Malformed JSON in features: {exc}")

    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, str):
                raise ValueError("Array elements in features must be strings")
            item_clean = item.strip()
            canon = canonicalize_capability_key(item_clean)
            if not canon or canon not in CAPABILITY_REGISTRY:
                raise ValueError(f"Unknown capability key in features: '{item_clean}'")
            if not is_sellable_capability(canon):
                raise ValueError(f"Non-sellable capability cannot be granted: '{item_clean}'")
    elif isinstance(parsed, dict):
        for k, v in parsed.items():
            if not isinstance(k, str):
                raise ValueError("Dict keys in features must be strings")
            if not isinstance(v, bool):
                raise ValueError(
                    f"Feature '{k}' must have a strict boolean value, got {type(v).__name__}"
                )
            k_clean = k.strip()
            canon = canonicalize_capability_key(k_clean)
            if not canon or canon not in CAPABILITY_REGISTRY:
                raise ValueError(f"Unknown capability key in features: '{k_clean}'")
            if v and not is_sellable_capability(canon):
                raise ValueError(f"Non-sellable capability cannot be granted: '{k_clean}'")
    else:
        raise ValueError("features JSON must be a list or object")

    return cleaned


class SubscriptionPlanBase(BaseModel):
    name: str
    display_name_ar: str
    price: NonNegativeMoney
    duration_days: int = Field(ge=1)
    max_users: Optional[int] = Field(default=None, ge=1)
    max_patients: Optional[int] = Field(default=None, ge=0)
    features: Optional[str] = None
    is_ai_enabled: bool = False
    ai_daily_limit: int = Field(default=0, ge=0)
    ai_features: Optional[str] = None
    is_default: bool = False
    policy_revision: int = 1
    billing_cycle_unit: str = "month"

    @field_validator("features")
    @classmethod
    def check_features(cls, v: Optional[str]) -> Optional[str]:
        return validate_plan_features_json(v)

    @field_validator("billing_cycle_unit")
    @classmethod
    def check_billing_cycle_unit(cls, v: str) -> str:
        unit = v.strip().lower()
        if unit not in {"day", "month", "year"}:
            raise ValueError("billing_cycle_unit must be 'day', 'month', or 'year'")
        return unit

    @model_validator(mode="after")
    def check_ai_limits(self) -> "SubscriptionPlanBase":
        if self.is_ai_enabled and self.ai_daily_limit <= 0:
            raise ValueError("ai_daily_limit must be greater than 0 when is_ai_enabled is True")
        if not self.is_ai_enabled and self.ai_daily_limit > 0:
            raise ValueError("ai_daily_limit must be 0 when is_ai_enabled is False")
        return self


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    display_name_ar: Optional[str] = None
    price: Optional[NonNegativeMoney] = None
    duration_days: Optional[int] = Field(default=None, ge=1)
    max_users: Optional[int] = Field(default=None, ge=1)
    max_patients: Optional[int] = Field(default=None, ge=0)
    features: Optional[str] = None
    is_active: Optional[bool] = None
    is_ai_enabled: Optional[bool] = None
    ai_daily_limit: Optional[int] = Field(default=None, ge=0)
    ai_features: Optional[str] = None
    is_default: Optional[bool] = None
    billing_cycle_unit: Optional[str] = None
    expected_revision: Optional[int] = None
    reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator("features")
    @classmethod
    def check_features(cls, v: Optional[str]) -> Optional[str]:
        return validate_plan_features_json(v)

    @field_validator("billing_cycle_unit")
    @classmethod
    def check_billing_cycle_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        unit = v.strip().lower()
        if unit not in {"day", "month", "year"}:
            raise ValueError("billing_cycle_unit must be 'day', 'month', or 'year'")
        return unit


class SubscriptionPlanPreviewRequest(BaseModel):
    display_name_ar: Optional[str] = None
    price: Optional[NonNegativeMoney] = None
    duration_days: Optional[int] = Field(default=None, ge=1)
    max_users: Optional[int] = Field(default=None, ge=1)
    max_patients: Optional[int] = Field(default=None, ge=0)
    features: Optional[str] = None
    is_active: Optional[bool] = None
    is_ai_enabled: Optional[bool] = None
    ai_daily_limit: Optional[int] = Field(default=None, ge=0)
    ai_features: Optional[str] = None
    is_default: Optional[bool] = None
    billing_cycle_unit: Optional[str] = None

    @field_validator("features")
    @classmethod
    def check_features(cls, v: Optional[str]) -> Optional[str]:
        return validate_plan_features_json(v)


class SubscriptionPlanPreviewResponse(BaseModel):
    plan_id: int
    plan_name: str
    current_revision: int
    affected_tenants_count: int
    proposed_changes: dict[str, dict[str, Any]]
    coverage_warnings: list[str]
    can_apply: bool


class CommercialOverrideItem(BaseModel):
    capability_key: str
    override_value: str = Field(description="'allow', 'deny', or 'inherit'")
    expires_at: Optional[datetime] = None

    @field_validator("override_value")
    @classmethod
    def validate_override_value(cls, v: str) -> str:
        val = v.strip().lower()
        if val not in {"allow", "deny", "inherit"}:
            raise ValueError("override_value must be 'allow', 'deny', or 'inherit'")
        return val

    @field_validator("capability_key")
    @classmethod
    def validate_capability_key(cls, v: str) -> str:
        key = v.strip()
        canon = canonicalize_capability_key(key)
        if not canon or canon not in CAPABILITY_REGISTRY:
            raise ValueError(f"Unknown capability key: '{key}'")
        return canon


class TenantCommercialOverridesUpdateRequest(BaseModel):
    expected_revision: int
    reason: str = Field(min_length=3, max_length=500)
    overrides: list[CommercialOverrideItem]


class CommercialTenantOverrideResponse(BaseModel):
    id: Optional[int] = None
    tenant_id: int
    capability_key: str
    override_value: str
    reason: str
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    created_by_id: Optional[int] = None
    created_by_username: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TenantCommercialOverridesResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    policy_revision: int
    overrides: list[CommercialTenantOverrideResponse]
    effective_capabilities: dict[str, bool]


class TrialPolicyResponse(BaseModel):
    trial_plan_name: str
    trial_plan_id: Optional[int] = None
    trial_duration_days: int
    is_card_required: bool = False
    eligible_plans: list[dict[str, Any]]


class TrialPolicyUpdateRequest(BaseModel):
    trial_plan_name: str
    trial_duration_days: int = Field(ge=1, le=90)
    reason: str = Field(min_length=3, max_length=500)


class EmergencyRestrictionUpdateRequest(BaseModel):
    capability_key: str
    is_restricted: bool
    reason: str = Field(min_length=3, max_length=500)


class EmergencyRestrictionResponse(BaseModel):
    active_restrictions: list[str]
    updated_at: Optional[datetime] = None


class SubscriptionPlan(SubscriptionPlanBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPaymentBase(BaseModel):
    tenant_id: Optional[int] = None
    plan_id: Optional[int] = None
    amount: Optional[NonNegativeMoney] = Decimal("0.00")
    payment_method: Optional[str] = "Unknown"
    notes: Optional[str] = None
    payment_date: Optional[datetime] = None
    paid_by: Optional[str] = None
    provider: Optional[str] = None
    provider_payment_id: Optional[str] = None
    provider_status: Optional[str] = None


class SubscriptionPaymentCreate(SubscriptionPaymentBase):
    tenant_id: int
    plan_id: int
    amount: PositiveMoney
    payment_method: str


class SubscriptionPayment(SubscriptionPaymentBase):
    id: int
    payment_date: datetime
    created_by: Optional[str] = None
    provider: Optional[str] = None
    provider_payment_id: Optional[str] = None
    provider_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCheckoutCreate(BaseModel):
    tenant_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    provider: str = Field(default="manual", min_length=1, max_length=50)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()


class SubscriptionCheckoutSession(BaseModel):
    provider: str
    provider_reference: str
    checkout_url: str
    amount: NonNegativeMoney
    currency: str = "EGP"


class SubscriptionWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=50)
    provider_reference: str = Field(min_length=1, max_length=120)
    provider_payment_id: str = Field(min_length=1, max_length=160)
    provider_status: str = Field(min_length=1, max_length=30)
    tenant_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    amount: PositiveMoney
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    paid_by: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("provider")
    @classmethod
    def normalize_webhook_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


# -------------------------------------------------------------
# PR-02 Additive Commercial Capability Schemas
# -------------------------------------------------------------

class CommercialDecisionSchema(BaseModel):
    capability: str
    operation: str
    allowed: bool
    proposed_allowed: bool
    is_shadow: bool
    is_discrepancy: bool
    mode: str
    reason_code: str
    explanation_en: str
    explanation_ar: str
    commercial_grant: bool
    subscription_state_allowed: bool
    rollout_allowed: bool
    emergency_denied: bool
    is_clinical_history_read: bool
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    policy_revision: int = 1
    diagnostics: dict = Field(default_factory=dict)


class CapabilityMetadataSchema(BaseModel):
    key: str
    display_name_en: str
    display_name_ar: str
    is_sellable: bool
    default_enabled_launch: bool
    allowed_operations: list[str]
    associated_routes: list[str]
    associated_tools: list[str]
    description_en: str = ""
    description_ar: str = ""


class TenantEffectiveEntitlementsResponse(BaseModel):
    tenant_id: int
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    status: str
    mode: str
    is_shadow: bool
    can_read_clinical: bool
    can_write_clinical: bool
    can_write_billable: bool
    can_create_appointments: bool
    commercial_decisions: dict[str, CommercialDecisionSchema]
    shadow_discrepancies: list[str] = Field(default_factory=list)
    unmapped_keys: list[str] = Field(default_factory=list)


# PR-03 Diagnostics Schemas
class CapacitySeatsDiagnostics(BaseModel):
    limit: Optional[int] = None
    used: int
    remaining: Optional[int] = None
    unit: str = "active_login_accounts"
    is_exhausted: bool = False


class CapacityAIDiagnostics(BaseModel):
    is_enabled: bool = False
    daily_limit: int = 0
    historical_diagnostic_count: int = 0
    historical_diagnostic_label: str
    quota_ledger_source: str = "unavailable"
    quota_ledger_note: str
    remaining_quota: Optional[int] = None
    window_reset: str = "clinic_local_midnight"
    timezone: str = "Africa/Cairo"


class CapacitiesDiagnostics(BaseModel):
    seats: CapacitySeatsDiagnostics
    ai: CapacityAIDiagnostics


class CapabilityDiagnosticItem(BaseModel):
    key: str
    display_name_ar: str
    display_name_en: str
    is_sellable: bool
    commercial_grant: bool
    effective_allowed: bool
    proposed_allowed: bool
    is_shadow: bool
    is_discrepancy: bool
    reason_code: str
    explanation_ar: str
    explanation_en: str
    enforcement_status: str
    source: str


class TenantEntitlementDiagnosticsResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    domain: Optional[str] = None
    is_active: bool
    is_hard_disabled: bool
    timezone: str
    plan_id: Optional[int] = None
    plan_name: str
    plan_display_name_ar: str
    plan_display_name_en: str
    raw_subscription_status: str
    effective_subscription_status: str
    subscription_end_date: Optional[str] = None
    grace_period_until: Optional[str] = None
    is_past_end: bool
    is_in_grace: bool
    policy_revision: int = 1
    enforcement_mode: str
    is_shadow: bool
    can_read_clinical: bool
    can_write_clinical: bool
    can_write_billable: bool
    can_create_appointments: bool
    capacities: CapacitiesDiagnostics
    capabilities: dict[str, CapabilityDiagnosticItem]
    configuration_warnings: list[str] = Field(default_factory=list)


