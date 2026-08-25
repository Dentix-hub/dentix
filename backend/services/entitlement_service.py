"""
DENTIX Entitlement Service
Centralized evaluation of tenant entitlements, limits, and read/write capabilities.
Enforces the fundamental clinical invariant:
- Clinical-history reads (Patient, Dental Chart, Treatment history, Prescriptions) are PERMANENTLY PERMITTED.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.core.config import get_subscription_enforcement_mode
from backend.models.tenant import Tenant
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
)


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
    ):
        self.tenant_id = tenant_id
        self.status = status
        self.mode = mode
        self.can_read_clinical = can_read_clinical
        self.can_write_clinical = can_write_clinical
        self.can_write_billable = can_write_billable
        self.can_create_appointments = can_create_appointments
        self.reason = reason

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
        }


class EntitlementService:
    @staticmethod
    def evaluate_tenant_entitlements(
        tenant: Tenant,
        now: Optional[datetime] = None,
        override_mode: Optional[str] = None,
    ) -> EntitlementEvaluation:
        """
        Evaluate full entitlement set for a given tenant.
        """
        mode = override_mode or get_subscription_enforcement_mode()
        current_time = now or datetime.now(timezone.utc)
        norm_status = normalize_state(getattr(tenant, "subscription_status", "trial"))

        # Check explicit timestamp bounds if active/grace
        is_past_end = False
        if tenant.subscription_end_date and tenant.subscription_end_date < current_time:
            is_past_end = True

        is_past_grace = False
        if tenant.grace_period_until and tenant.grace_period_until < current_time:
            is_past_grace = True

        effective_status = norm_status
        if norm_status in {SubscriptionState.ACTIVE.value, SubscriptionState.TRIAL.value}:
            if is_past_end:
                effective_status = (
                    SubscriptionState.EXPIRED_READ_ONLY.value
                    if is_past_grace
                    else SubscriptionState.GRACE.value
                )

        # Invariant: Clinical-history read is ALWAYS permitted
        can_read_clinical = True

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
            )

        # In 'enforce' mode:
        if effective_status in {SubscriptionState.ACTIVE.value, SubscriptionState.TRIAL.value, SubscriptionState.GRACE.value}:
            return EntitlementEvaluation(
                tenant_id=tenant.id,
                status=effective_status,
                mode=mode,
                can_read_clinical=True,
                can_write_clinical=True,
                can_write_billable=True,
                can_create_appointments=True,
                reason=None,
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
        )
