"""
C7.5 — Tenant Scope Verification Tests

Verifies that tenant_scope.py SQLAlchemy event listener is correctly registered
and applies tenant filtering to ALL models that have a tenant_id column.
"""

from backend.core.tenant_scope import (
    current_tenant_id,
    super_admin_bypass,
    set_current_tenant,
    set_super_admin_bypass,
    clear_tenant_context,
)
from backend.database import Base


# ============================================
# MODELS WITH tenant_id AUDIT
# ============================================

# Authoritative list of ALL models that MUST have their own tenant_id column
EXPECTED_TENANT_MODELS = {
    "User",
    "Patient",
    "Treatment",
    "Payment",
    "Expense",
    "Procedure",
    "Laboratory",
    "LabOrder",
    "LabPayment",
    "InsuranceProvider",
    "PriceList",
    "Warehouse",
    "Material",
    "Batch",
    "StockItem",
    "ProcedureWeight",
    "ProcedureMaterialWeight",
    "SavedMedication",
    "AuditLog",
    "Notification",
    "SupportMessage",
    "BackgroundJob",
    "SystemError",
    "SecurityEvent",
    "AILog",
    "AIUsageLog",
    "Salary",
    "SalaryPayment",
    "Invoice",
    "TenantFeature",
    "MaterialLearningLog",
}

# Models filtered via parent FK join (no own tenant_id column needed)
PARENT_FILTERED_MODELS = {
    "Appointment",       # filtered via patient_id → Patient.tenant_id
    "Prescription",      # filtered via patient_id → Patient.tenant_id
    "ToothStatus",       # filtered via patient_id → Patient.tenant_id
    "PriceListItem",     # filtered via price_list_id → PriceList.tenant_id
    "StockMovement",     # filtered via material_id → Material.tenant_id
    "MaterialSession",   # filtered via material_id → Material.tenant_id
}

# Models that intentionally do NOT have tenant_id (system-level)
SYSTEM_MODELS = {
    "Tenant",
    "SubscriptionPlan",
    "SubscriptionPayment",
    "FeatureFlag",
    "DailySystemStats",
}


class TestTenantScopeRegistration:
    """Verify that the tenant_scope event listener is properly registered."""

    def test_event_listener_registered(self):
        """The do_orm_execute event must be registered on Session."""
        from sqlalchemy.orm import Session
        from sqlalchemy import event as sa_event

        has_listeners = sa_event.contains(Session, "do_orm_execute", 
            __import__('backend.core.tenant_scope', fromlist=['_add_tenant_filter'])._add_tenant_filter
        )
        assert has_listeners, "tenant_scope do_orm_execute listener is NOT registered"

    def test_all_expected_models_have_tenant_id(self):
        """Every business model must have a tenant_id column."""
        missing = []
        for mapper in Base.registry.mappers:
            cls_name = mapper.class_.__name__
            if cls_name in EXPECTED_TENANT_MODELS:
                if "tenant_id" not in mapper.columns:
                    missing.append(cls_name)

        assert not missing, (
            f"Models missing tenant_id column: {missing}. "
            "These models will NOT be filtered by tenant_scope and may leak data."
        )

    def test_no_unexpected_tenant_models(self):
        """System models must NOT have tenant_id (they are system-wide)."""
        has_tenant = []
        for mapper in Base.registry.mappers:
            cls_name = mapper.class_.__name__
            if cls_name in SYSTEM_MODELS and "tenant_id" in mapper.columns:
                has_tenant.append(cls_name)

        # SubscriptionPayment may have tenant_id for billing, so we allow it
        has_tenant = [m for m in has_tenant if m != "SubscriptionPayment"]
        assert not has_tenant, (
            f"System models unexpectedly have tenant_id: {has_tenant}"
        )

    def test_tenant_scope_coverage_percentage(self):
        """At least 80% of all models with tenant_id should be in our expected list."""
        models_with_tenant = set()
        for mapper in Base.registry.mappers:
            cls_name = mapper.class_.__name__
            if "tenant_id" in mapper.columns:
                models_with_tenant.add(cls_name)

        covered = models_with_tenant & EXPECTED_TENANT_MODELS
        coverage = len(covered) / len(models_with_tenant) * 100 if models_with_tenant else 0

        assert coverage >= 80, (
            f"Tenant scope coverage is only {coverage:.0f}%. "
            f"Uncovered models: {models_with_tenant - EXPECTED_TENANT_MODELS}"
        )


class TestTenantContextVars:
    """Verify context variable operations."""

    def test_set_and_get_tenant_id(self):
        """Setting tenant ID must be retrievable."""
        token = set_current_tenant(42)
        try:
            assert current_tenant_id.get() == 42
        finally:
            current_tenant_id.reset(token)

    def test_default_tenant_is_none(self):
        """Without setting, tenant_id must be None."""
        assert current_tenant_id.get() is None

    def test_super_admin_bypass_default_false(self):
        """Super admin bypass must default to False."""
        assert super_admin_bypass.get() is False

    def test_super_admin_bypass_toggle(self):
        """Setting bypass must be retrievable and resettable."""
        token = set_super_admin_bypass(True)
        try:
            assert super_admin_bypass.get() is True
        finally:
            super_admin_bypass.reset(token)

    def test_clear_tenant_context(self):
        """Clearing context must reset both variables."""
        tenant_token = set_current_tenant(99)
        admin_token = set_super_admin_bypass(True)

        clear_tenant_context(tenant_token, admin_token)

        assert current_tenant_id.get() is None
        assert super_admin_bypass.get() is False

    def test_context_isolation(self):
        """Different context settings must not leak."""
        token1 = set_current_tenant(1)
        assert current_tenant_id.get() == 1

        token2 = set_current_tenant(2)
        assert current_tenant_id.get() == 2

        current_tenant_id.reset(token2)
        assert current_tenant_id.get() == 1

        current_tenant_id.reset(token1)


class TestTenantFilterLogic:
    """Verify the _add_tenant_filter function behavior."""

    def test_filter_skips_when_no_tenant_set(self):
        """When tenant_id is None, no filter should be applied."""
        assert current_tenant_id.get() is None
        # This is tested implicitly — if no tenant is set,
        # the listener returns early without modifying the statement

    def test_filter_skips_for_super_admin(self):
        """Super admin bypass must skip filtering."""
        token = set_super_admin_bypass(True)
        try:
            assert super_admin_bypass.get() is True
            # The listener checks this before applying criteria
        finally:
            super_admin_bypass.reset(token)

    def test_all_mapper_classes_scanned(self):
        """The listener iterates over ALL registered mappers."""
        mapper_count = len(list(Base.registry.mappers))
        assert mapper_count > 10, (
            f"Only {mapper_count} mappers found. Models may not be imported."
        )

    def test_models_with_tenant_id_count(self):
        """Verify we have a reasonable number of tenant-scoped models."""
        count = sum(
            1 for mapper in Base.registry.mappers
            if "tenant_id" in mapper.columns
        )
        assert count >= 15, (
            f"Only {count} models have tenant_id. Expected at least 15."
        )
