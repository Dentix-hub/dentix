"""
Unit tests for backend/services/entitlement_service.py
"""

from datetime import datetime, timezone, timedelta
import pytest
from backend.models.tenant import Tenant
from backend.services.entitlement_service import EntitlementService


def test_clinical_read_invariant_always_true():
    past = datetime.now(timezone.utc) - timedelta(days=30)
    for status in ["active", "trial", "grace", "expired_read_only", "suspended_admin", "cancelled"]:
        tenant = Tenant(
            id=101,
            name="Clinic 101",
            subscription_status=status,
            subscription_end_date=past,
            grace_period_until=past,
        )
        for mode in ["off", "observe", "enforce"]:
            eval_res = EntitlementService.evaluate_tenant_entitlements(tenant, override_mode=mode)
            assert eval_res.can_read_clinical is True, f"Failed clinical read invariant for status={status}, mode={mode}"


def test_enforce_mode_blocks_billable_writes_when_expired():
    past = datetime.now(timezone.utc) - timedelta(days=10)
    tenant = Tenant(
        id=102,
        name="Expired Clinic",
        subscription_status="expired",
        subscription_end_date=past,
        grace_period_until=past,
    )
    eval_res = EntitlementService.evaluate_tenant_entitlements(tenant, override_mode="enforce")
    assert eval_res.can_read_clinical is True
    assert eval_res.can_write_billable is False
    assert eval_res.can_write_clinical is False
    assert eval_res.can_create_appointments is False
    assert "Read-only clinical history mode active" in eval_res.reason


def test_off_mode_allows_all_writes():
    past = datetime.now(timezone.utc) - timedelta(days=10)
    tenant = Tenant(
        id=103,
        name="Expired Clinic Off Mode",
        subscription_status="expired",
        subscription_end_date=past,
        grace_period_until=past,
    )
    eval_res = EntitlementService.evaluate_tenant_entitlements(tenant, override_mode="off")
    assert eval_res.can_read_clinical is True
    assert eval_res.can_write_billable is True
    assert eval_res.can_write_clinical is True


def test_grace_period_entitlements():
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)
    future = now + timedelta(days=5)
    tenant = Tenant(
        id=104,
        name="Grace Clinic",
        subscription_status="active",
        subscription_end_date=past,
        grace_period_until=future,
    )
    eval_res = EntitlementService.evaluate_tenant_entitlements(tenant, now=now, override_mode="enforce")
    assert eval_res.status == "grace"
    assert eval_res.can_read_clinical is True
    assert eval_res.can_write_billable is True
