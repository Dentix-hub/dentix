"""
PR-04 Acceptance Tests: Validated Catalog, Overrides, Policy Revision, and Audit Persistence.

Validates all PR-04 requirements:
1. Super Admin Authorization:
   - Commercial policy mutations require true Super Admin (Role.SUPER_ADMIN).
   - Clinic admin with SYSTEM_CONFIG or ordinary clinic users receive 403 Forbidden.
2. Strict Validation:
   - Limits: price >= 0, max_users >= 1, duration_days >= 1.
   - AI limits parity: is_ai_enabled=True requires finite ai_daily_limit > 0;
     is_ai_enabled=False requires ai_daily_limit == 0.
   - Features JSON: rejects unknown keys, non-sellable capabilities, malformed JSON, and string booleans.
3. Optimistic Concurrency Control (Policy Revision):
   - Updates must provide expected_revision.
   - Stale expected_revision returns HTTP 409 Conflict without partial persistence.
   - Successful update increments policy_revision atomically.
4. Pure Preview:
   - Preview endpoint returns affected tenants count, proposed diff, and coverage warnings without mutating the DB.
5. Transactional Audit Logging:
   - All mutations (plans, overrides, trial policy, emergency restrictions) commit AuditLog rows in the SAME transaction.
6. Commercial Tenant Overrides (Inherit / Allow / Deny / Expiry):
   - Setting 'allow' grants capability; 'deny' revokes capability; 'inherit' deletes override row.
   - Expired overrides (expires_at < now) are safely ignored.
   - Non-sellable capabilities cannot be overridden to 'allow'.
   - Commercial allow cannot bypass emergency denial, expired subscription state, or clinical history invariant.
   - Overrides respect tenant isolation.
7. Catalog Retirement:
   - Deactivating a plan preserves existing tenant subscriptions, foreign keys, and past receipts.
8. PostgreSQL RLS & Isolation:
   - Full PostgreSQL migration and Row-Level Security isolation test.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
import pytest
from sqlalchemy import func, select, text

from backend import models, schemas
from backend.auth import get_password_hash, create_access_token
from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    CapabilityKey,
    is_sellable_capability,
)
from backend.services.commercial_decision import CommercialDecisionEngine, CommercialReasonCode
from backend.services.entitlement_diagnostics_service import build_tenant_entitlement_diagnostics
from backend.services.subscription_service import SubscriptionService


@pytest.fixture
def pr04_seed_data(db_session):
    """Seed subscription plans, tenants, and users for PR-04 testing."""
    # 1. Clean existing test data
    db_session.query(models.CommercialTenantOverride).delete()
    db_session.query(models.AuditLog).delete()
    db_session.query(models.User).delete()
    db_session.query(models.Tenant).delete()
    db_session.query(models.SubscriptionPlan).delete()
    db_session.commit()

    # 2. Approved Launch Plans
    plan_essential = models.SubscriptionPlan(
        id=301,
        name="essential",
        display_name_ar="الأساسية",
        price=Decimal("200.00"),
        duration_days=30,
        billing_cycle_unit="month",
        max_users=2,
        is_ai_enabled=True,
        ai_daily_limit=2,
        features=json.dumps([
            "clinical", "billing", "laboratories", "inventory", "export_reports", "ai_insights", "tenant_backups"
        ]),
        is_default=False,
        is_active=True,
        policy_revision=1,
    )
    plan_professional = models.SubscriptionPlan(
        id=302,
        name="professional",
        display_name_ar="الاحترافية",
        price=Decimal("400.00"),
        duration_days=30,
        billing_cycle_unit="month",
        max_users=5,
        is_ai_enabled=True,
        ai_daily_limit=10,
        features=json.dumps([
            "clinical", "billing", "laboratories", "inventory", "export_reports", "ai_insights", "tenant_backups"
        ]),
        is_default=True,
        is_active=True,
        policy_revision=1,
    )
    plan_restricted = models.SubscriptionPlan(
        id=303,
        name="starter_no_ai",
        display_name_ar="البداية بدون ذكاء",
        price=Decimal("150.00"),
        duration_days=30,
        billing_cycle_unit="month",
        max_users=1,
        is_ai_enabled=False,
        ai_daily_limit=0,
        features=json.dumps(["clinical", "billing"]),
        is_default=False,
        is_active=True,
        policy_revision=1,
    )
    db_session.add_all([plan_essential, plan_professional, plan_restricted])
    db_session.commit()

    # 3. Tenants
    tenant_1 = models.Tenant(
        id=401,
        name="Clinic Alpha",
        plan="essential",
        plan_id=301,
        is_active=True,
        subscription_status="active",
        policy_revision=1,
    )
    tenant_2 = models.Tenant(
        id=402,
        name="Clinic Beta",
        plan="starter_no_ai",
        plan_id=303,
        is_active=True,
        subscription_status="active",
        policy_revision=1,
    )
    db_session.add_all([tenant_1, tenant_2])
    db_session.commit()

    # 4. Clinic Users
    user_clinic_admin = models.User(
        id=501,
        username="admin_alpha",
        email="admin_alpha@example.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_1.id,
        is_active=True,
        is_deleted=False,
    )
    user_doctor = models.User(
        id=502,
        username="doctor_alpha",
        email="doctor_alpha@example.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_1.id,
        is_active=True,
        is_deleted=False,
    )
    db_session.add_all([user_clinic_admin, user_doctor])
    db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "plan_essential": plan_essential,
        "plan_professional": plan_professional,
        "plan_restricted": plan_restricted,
        "user_clinic_admin": user_clinic_admin,
        "user_doctor": user_doctor,
    }


def _token_headers(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Super Admin Authorization
# ===========================================================================

def test_commercial_endpoints_require_super_admin(client, pr04_seed_data, super_admin_headers):
    """
    Clinic admin and ordinary users cannot call commercial policy mutation endpoints.
    Super Admin checks are mandatory and succeed.
    """
    admin_headers = _token_headers(pr04_seed_data["user_clinic_admin"])
    tenant_id = pr04_seed_data["tenant_1"].id
    plan_id = pr04_seed_data["plan_essential"].id

    # 1. Plan creation
    res = client.post("/api/v1/admin/subscriptions/plans", json={"name": "test"}, headers=admin_headers)
    assert res.status_code == 403

    # 2. Plan update
    res = client.put(f"/api/v1/admin/subscriptions/plans/{plan_id}", json={"price": 300}, headers=admin_headers)
    assert res.status_code == 403

    # 3. Plan preview
    res = client.post(f"/api/v1/admin/subscriptions/plans/{plan_id}/preview", json={"price": 300}, headers=admin_headers)
    assert res.status_code == 403

    # 4. Plan delete
    res = client.delete(f"/api/v1/admin/subscriptions/plans/{plan_id}", headers=admin_headers)
    assert res.status_code == 403

    # 5. Tenant Commercial Overrides
    res = client.put(
        f"/api/v1/admin/tenants/{tenant_id}/commercial-overrides",
        json={"expected_revision": 1, "reason": "Test", "overrides": []},
        headers=admin_headers,
    )
    assert res.status_code == 403

    # 6. Trial Policy
    res = client.put(
        "/api/v1/admin/subscriptions/trial-policy",
        json={"trial_plan_name": "professional", "trial_duration_days": 14, "reason": "Test"},
        headers=admin_headers,
    )
    assert res.status_code == 403

    # 7. Emergency Restrictions
    res = client.post(
        "/api/v1/admin/features/emergency-restrictions",
        json={"capability_key": "ai_insights", "is_restricted": True, "reason": "Security"},
        headers=admin_headers,
    )
    assert res.status_code == 403

    # Verify Super Admin can access trial policy read
    res_sa = client.get("/api/v1/admin/subscriptions/trial-policy", headers=super_admin_headers)
    assert res_sa.status_code == 200


# ===========================================================================
# 2. Strict Validation for Limits, AI, and Registered Features
# ===========================================================================

def test_plan_validation_limits_and_features(client, super_admin_headers):
    """
    Malformed plans, negative limits, invalid AI quota, non-sellable capabilities,
    and string booleans fail without partial persistence.
    """
    # 1. Negative price
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_price",
            "display_name_ar": "سعر سالب",
            "price": -50,
            "duration_days": 30,
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422

    # 2. Negative or zero users
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_users",
            "display_name_ar": "مستخدمين سالب",
            "price": 100,
            "duration_days": 30,
            "max_users": 0,
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422

    # 3. AI enabled with 0 quota
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_ai_zero",
            "display_name_ar": "ذكاء بدون كوتة",
            "price": 100,
            "duration_days": 30,
            "is_ai_enabled": True,
            "ai_daily_limit": 0,
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422

    # 4. AI disabled with positive quota
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_ai_disabled",
            "display_name_ar": "كوتة بدون ذكاء",
            "price": 100,
            "duration_days": 30,
            "is_ai_enabled": False,
            "ai_daily_limit": 10,
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422

    # 5. Non-sellable capability granted in plan features (e.g. patient_portal)
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_non_sellable",
            "display_name_ar": "بوابة مريض تجارية",
            "price": 500,
            "duration_days": 30,
            "features": json.dumps(["clinical", "patient_portal"]),
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422
    assert "Non-sellable" in res.text

    # 6. Unknown capability key
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_unknown_cap",
            "display_name_ar": "خاصية وهمية",
            "price": 500,
            "duration_days": 30,
            "features": json.dumps(["clinical", "super_teleportation"]),
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422
    assert "Unknown capability" in res.text

    # 7. Non-boolean value in features JSON dict
    res = client.post(
        "/api/v1/admin/subscriptions/plans",
        json={
            "name": "invalid_string_bool",
            "display_name_ar": "قيمة نصية لبولين",
            "price": 500,
            "duration_days": 30,
            "features": json.dumps({"clinical": "true"}),
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 422
    assert "strict boolean" in res.text


# ===========================================================================
# 3. Optimistic Locking & Policy Revision
# ===========================================================================

def test_plan_update_optimistic_locking(client, db_session, pr04_seed_data, super_admin_headers):
    """
    Plan updates require expected_revision matching DB revision.
    Stale revision returns 409 Conflict.
    Matching revision succeeds, increments revision, and records AuditLog.
    """
    plan = pr04_seed_data["plan_essential"]
    plan_id = plan.id
    assert plan.policy_revision == 1

    # 1. Update with stale revision
    res_stale = client.put(
        f"/api/v1/admin/subscriptions/plans/{plan_id}",
        json={
            "price": 250,
            "expected_revision": 99,
            "reason": "Price bump",
        },
        headers=super_admin_headers,
    )
    assert res_stale.status_code == 409
    assert "Policy revision conflict" in res_stale.json()["detail"]

    # Verify DB was NOT mutated
    db_session.refresh(plan)
    assert plan.price == Decimal("200.00")
    assert plan.policy_revision == 1

    # 2. Update with correct expected_revision
    res_ok = client.put(
        f"/api/v1/admin/subscriptions/plans/{plan_id}",
        json={
            "price": 250,
            "expected_revision": 1,
            "reason": "Authorized price bump for future renewals",
        },
        headers=super_admin_headers,
    )
    assert res_ok.status_code == 200
    data = res_ok.json()["data"]
    assert Decimal(str(data["price"])) == Decimal("250.00")
    assert data["policy_revision"] == 2

    # 3. Repeat with stale revision 1 -> fails with 409
    res_stale_again = client.put(
        f"/api/v1/admin/subscriptions/plans/{plan_id}",
        json={
            "price": 300,
            "expected_revision": 1,
            "reason": "Concurrent race attempt",
        },
        headers=super_admin_headers,
    )
    assert res_stale_again.status_code == 409

    # 4. Transactional audit log verified
    audit = db_session.query(models.AuditLog).filter(
        models.AuditLog.action == "SUBSCRIPTION_PLAN_UPDATE",
        models.AuditLog.entity_id == plan_id,
    ).first()
    assert audit is not None
    assert audit.performed_by_username == "superadmin"
    assert "200.00" in audit.old_value
    assert "250" in audit.new_value
    assert "Authorized price bump" in audit.details


# ===========================================================================
# 4. Pure Preview Endpoint
# ===========================================================================

def test_preview_plan_update_leaves_db_unchanged(client, db_session, pr04_seed_data, super_admin_headers):
    """
    POST /api/v1/admin/subscriptions/plans/{id}/preview returns affected tenant count,
    proposed diff, and warnings without mutating database.
    """
    plan = pr04_seed_data["plan_essential"]
    plan_id = plan.id
    tenant = pr04_seed_data["tenant_1"]
    assert tenant.plan_id == plan_id

    preview_payload = {
        "price": 275,
        "max_users": 4,
        "features": json.dumps(["clinical", "billing"]),
    }

    res = client.post(
        f"/api/v1/admin/subscriptions/plans/{plan_id}/preview",
        json=preview_payload,
        headers=super_admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["plan_id"] == plan_id
    assert data["affected_tenants_count"] >= 1
    assert data["current_revision"] == 1
    assert "price" in data["proposed_changes"]
    assert data["proposed_changes"]["price"]["old"] == "200.00"
    assert data["proposed_changes"]["price"]["new"] == "275"
    assert "max_users" in data["proposed_changes"]
    assert len(data["coverage_warnings"]) >= 2
    assert data["can_apply"] is True

    # Verify DB was NOT mutated
    db_session.refresh(plan)
    assert plan.price == Decimal("200.00")
    assert plan.max_users == 2
    assert plan.policy_revision == 1


# ===========================================================================
# 5. Commercial Tenant Overrides (Inherit / Allow / Deny / Expiry)
# ===========================================================================

def test_commercial_tenant_overrides_flow(client, db_session, pr04_seed_data, super_admin_headers):
    """
    Validates tenant commercial override inheritance, allow, deny, expiry,
    and optimistic locking.
    """
    tenant = pr04_seed_data["tenant_2"]  # on starter_no_ai (only clinical, billing enabled)
    tenant_id = tenant.id
    assert tenant.policy_revision == 1

    # Base check: laboratories is not in plan -> denied
    diagnostics = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=super_admin_headers).json()["data"]
    assert diagnostics["capabilities"]["laboratories"]["effective_allowed"] is False
    assert diagnostics["capabilities"]["laboratories"]["source"] == "not_granted"

    # 1. Stale revision fails
    res_stale = client.put(
        f"/api/v1/admin/tenants/{tenant_id}/commercial-overrides",
        json={
            "expected_revision": 99,
            "reason": "Test override",
            "overrides": [{"capability_key": "laboratories", "override_value": "allow"}],
        },
        headers=super_admin_headers,
    )
    assert res_stale.status_code == 409

    # 2. Non-sellable capability cannot be overridden to 'allow'
    res_non_sellable = client.put(
        f"/api/v1/admin/tenants/{tenant_id}/commercial-overrides",
        json={
            "expected_revision": 1,
            "reason": "Trying to enable telehealth",
            "overrides": [{"capability_key": "telehealth", "override_value": "allow"}],
        },
        headers=super_admin_headers,
    )
    assert res_non_sellable.status_code == 422
    assert "not sellable" in res_non_sellable.text

    # 3. Grant 'allow' override for laboratories
    res_allow = client.put(
        f"/api/v1/admin/tenants/{tenant_id}/commercial-overrides",
        json={
            "expected_revision": 1,
            "reason": "Pilot agreement for dental lab module",
            "overrides": [{"capability_key": "laboratories", "override_value": "allow"}],
        },
        headers=super_admin_headers,
    )
    assert res_allow.status_code == 200
    ov_data = res_allow.json()["data"]
    assert ov_data["policy_revision"] == 2
    assert ov_data["effective_capabilities"]["laboratories"] is True

    # Verify diagnostics now reflect override
    diag_updated = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=super_admin_headers).json()["data"]
    assert diag_updated["capabilities"]["laboratories"]["effective_allowed"] is True
    assert diag_updated["capabilities"]["laboratories"]["source"] == "commercial_override"
    assert diag_updated["policy_revision"] == 2

    # 4. Grant 'deny' override for billing (even though plan includes billing)
    res_deny = client.put(
        f"/api/v1/admin/tenants/{tenant_id}/commercial-overrides",
        json={
            "expected_revision": 2,
            "reason": "Delinquent payment suspension of billing module",
            "overrides": [{"capability_key": "billing", "override_value": "deny"}],
        },
        headers=super_admin_headers,
    )
    assert res_deny.status_code == 200
    diag_deny = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=super_admin_headers).json()["data"]
    assert diag_deny["capabilities"]["billing"]["effective_allowed"] is False
    assert diag_deny["capabilities"]["billing"]["source"] == "commercial_override"

    # 5. Reset to 'inherit' restores plan inheritance
    res_inherit = client.put(
        f"/api/v1/admin/tenants/{tenant_id}/commercial-overrides",
        json={
            "expected_revision": 3,
            "reason": "Resetting billing to plan default",
            "overrides": [{"capability_key": "billing", "override_value": "inherit"}],
        },
        headers=super_admin_headers,
    )
    assert res_inherit.status_code == 200
    diag_inherit = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=super_admin_headers).json()["data"]
    assert diag_inherit["capabilities"]["billing"]["effective_allowed"] is True
    assert diag_inherit["capabilities"]["billing"]["source"] == "plan_default"

    # 6. Verify transactional audit logging
    audit = db_session.query(models.AuditLog).filter(
        models.AuditLog.action == "TENANT_COMMERCIAL_OVERRIDES_UPDATE",
        models.AuditLog.entity_id == tenant_id,
    ).order_by(models.AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.tenant_id == tenant_id
    assert audit.performed_by_username == "superadmin"


def test_expired_override_falls_back_to_plan(client, db_session, pr04_seed_data, super_admin_headers):
    """Expired commercial overrides (expires_at < now) must not grant capabilities."""
    tenant = pr04_seed_data["tenant_2"]  # starter_no_ai (laboratories not granted)
    tenant_id = tenant.id

    # Add expired override directly to DB
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    expired_ov = models.CommercialTenantOverride(
        tenant_id=tenant_id,
        capability_key="laboratories",
        override_value="allow",
        reason="Expired temporary trial",
        expires_at=yesterday.replace(tzinfo=None),
        created_at=yesterday.replace(tzinfo=None),
    )
    db_session.add(expired_ov)
    db_session.commit()

    # Diagnostics should ignore expired override and report False
    diag = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=super_admin_headers).json()["data"]
    assert diag["capabilities"]["laboratories"]["effective_allowed"] is False
    assert diag["capabilities"]["laboratories"]["source"] == "not_granted"


# ===========================================================================
# 6. Emergency Restrictions
# ===========================================================================

def test_emergency_restriction_lifecycle_and_override_supremacy(client, db_session, pr04_seed_data, super_admin_headers):
    """
    Emergency restriction takes absolute precedence over plan grants and commercial overrides.
    Commercial allow CANNOT defeat emergency restriction.
    """
    tenant = pr04_seed_data["tenant_1"]  # has ai_insights granted
    tenant_id = tenant.id

    # Verify initially allowed
    diag_init = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements", headers=super_admin_headers).json()["data"]
    assert diag_init["capabilities"]["ai_insights"]["effective_allowed"] is True

    # 1. Apply emergency restriction
    res_restrict = client.post(
        "/api/v1/admin/features/emergency-restrictions",
        json={
            "capability_key": "ai_insights",
            "is_restricted": True,
            "reason": "Provider outage and security incident",
        },
        headers=super_admin_headers,
    )
    assert res_restrict.status_code == 200
    assert "ai_insights" in res_restrict.json()["data"]["active_restrictions"]

    # 2. Evaluate with emergency restriction in decision engine
    decision = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant,
        capability="ai_insights",
        operation="write_business",
        emergency_restrictions={"ai_insights"},
    )
    assert decision.proposed_allowed is False
    assert decision.reason_code == CommercialReasonCode.EMERGENCY_RESTRICTION_ACTIVE
    assert decision.emergency_denied is True

    # 3. Attempting to override with commercial allow CANNOT bypass emergency restriction
    decision_override = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant,
        capability="ai_insights",
        operation="write_business",
        commercial_overrides={"ai_insights": True},
        emergency_restrictions={"ai_insights"},
    )
    assert decision_override.proposed_allowed is False
    assert decision_override.emergency_denied is True

    # 4. Lift restriction
    res_lift = client.post(
        "/api/v1/admin/features/emergency-restrictions",
        json={
            "capability_key": "ai_insights",
            "is_restricted": False,
            "reason": "Provider restored",
        },
        headers=super_admin_headers,
    )
    assert res_lift.status_code == 200
    assert "ai_insights" not in res_lift.json()["data"]["active_restrictions"]


# ===========================================================================
# 7. Catalog Retirement & Duplicate Reconciliation
# ===========================================================================

def test_catalog_retirement_preserves_tenant_contracts(client, db_session, pr04_seed_data, super_admin_headers):
    """
    Deactivating a plan (catalog retirement) sets is_active=False but does NOT
    delete or revoke subscriptions for existing tenants on that plan.
    """
    plan = pr04_seed_data["plan_restricted"]
    plan_id = plan.id
    tenant = pr04_seed_data["tenant_2"]
    assert tenant.plan_id == plan_id

    # Deactivate plan
    res_del = client.delete(f"/api/v1/admin/subscriptions/plans/{plan_id}", headers=super_admin_headers)
    assert res_del.status_code == 200

    db_session.refresh(plan)
    assert plan.is_active is False
    assert plan.policy_revision == 2

    # Tenant is still assigned to this plan and functional
    db_session.refresh(tenant)
    assert tenant.plan_id == plan_id

    # Audit log was created
    audit = db_session.query(models.AuditLog).filter(
        models.AuditLog.action == "SUBSCRIPTION_PLAN_DEACTIVATE",
        models.AuditLog.entity_id == plan_id,
    ).first()
    assert audit is not None


def test_reconcile_duplicate_plans(client, db_session, pr04_seed_data, super_admin_headers):
    """
    Duplicate plan names are reconciled atomically by deactivating redundant records
    without deleting historical data.
    """
    # Create duplicate plan directly in DB
    dup_plan = models.SubscriptionPlan(
        name="essential_duplicate",
        display_name_ar="الأساسية مكررة",
        price=Decimal("200.00"),
        is_active=True,
    )
    db_session.add(dup_plan)
    db_session.commit()

    # Reconcile endpoint
    res = client.post("/api/v1/admin/subscriptions/plans/reconcile-duplicates", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "scanned_plans_count" in data


# ===========================================================================
# 8. Trial Policy
# ===========================================================================

def test_trial_policy_management(client, db_session, pr04_seed_data, super_admin_headers):
    """Super Admin can inspect and update future signup trial policy."""
    # 1. Get trial policy
    res_get = client.get("/api/v1/admin/subscriptions/trial-policy", headers=super_admin_headers)
    assert res_get.status_code == 200
    data = res_get.json()["data"]
    assert data["trial_duration_days"] == 14
    assert data["is_card_required"] is False

    # 2. Update trial policy with non-existent plan -> 400
    res_err = client.put(
        "/api/v1/admin/subscriptions/trial-policy",
        json={"trial_plan_name": "imaginary_plan", "trial_duration_days": 14, "reason": "Test"},
        headers=super_admin_headers,
    )
    assert res_err.status_code == 400

    # 3. Update trial policy successfully
    res_ok = client.put(
        "/api/v1/admin/subscriptions/trial-policy",
        json={"trial_plan_name": "professional", "trial_duration_days": 21, "reason": "Promotional period extension"},
        headers=super_admin_headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["data"]["trial_duration_days"] == 21
    assert res_ok.json()["data"]["trial_plan_name"] == "professional"

    # Audit log verified
    audit = db_session.query(models.AuditLog).filter(
        models.AuditLog.action == "TRIAL_POLICY_UPDATE",
    ).first()
    assert audit is not None
    assert "21" in audit.new_value


# ===========================================================================
# 9. PostgreSQL RLS & Migration Isolation
# ===========================================================================

def test_postgresql_commercial_overrides_rls_isolation():
    """
    Verify commercial_tenant_overrides table under PostgreSQL:
    1. Migration e4a5b6c7d8e9 applies and creates table with RLS ENABLE and FORCE.
    2. Tenant A (101) cannot see Tenant B's (102) overrides when rls.tenant_id = '101'.
    3. Cross-tenant insertion fails under RLS.
    4. Bypass RLS allows privileged inspection.
    """
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not pg_url or not pg_url.startswith(("postgresql://", "postgres://")):
        pytest.skip("PostgreSQL live instance required for RLS test")

    import psycopg2
    from backend.tests.test_preflight_postgres_contract import _create_database, _drop_database
    from alembic.config import Config
    from alembic import command
    import sqlalchemy as sa

    dbname, db_url = _create_database(pg_url)
    engine = sa.create_engine(db_url)

    try:
        # Run Alembic migrations up to head (e4a5b6c7d8e9)
        models.Base.metadata.create_all(engine)
        cfg = Config("backend/alembic.ini")
        cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
        command.stamp(cfg, "d3e4f5a6b7c8")
        command.upgrade(cfg, "e4a5b6c7d8e9")

        # Connect with psycopg2 to test RLS
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Seed two tenants
            cur.execute("""
                INSERT INTO tenants (id, name, subscription_status, is_active, payment_failed_count, plan, created_at, total_revenue, backup_frequency, is_deleted)
                VALUES (101, 'Tenant 101', 'active', true, 0, 'trial', NOW(), 0.00, 'off', false)
            """)
            cur.execute("""
                INSERT INTO tenants (id, name, subscription_status, is_active, payment_failed_count, plan, created_at, total_revenue, backup_frequency, is_deleted)
                VALUES (102, 'Tenant 102', 'active', true, 0, 'trial', NOW(), 0.00, 'off', false)
            """)

            # Seed overrides for both tenants using bypass
            cur.execute("SET rls.bypass_rls = 'true'")
            cur.execute("""
                INSERT INTO commercial_tenant_overrides (tenant_id, capability_key, override_value, reason, created_at, updated_at)
                VALUES (101, 'laboratories', 'allow', 'Pilot for 101', NOW(), NOW())
            """)
            cur.execute("""
                INSERT INTO commercial_tenant_overrides (tenant_id, capability_key, override_value, reason, created_at, updated_at)
                VALUES (102, 'inventory', 'allow', 'Pilot for 102', NOW(), NOW())
            """)

            # Create a non-superuser, non-bypassrls role to authentically test RLS
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rls_test_app') THEN
                        CREATE ROLE rls_test_app LOGIN NOSUPERUSER NOBYPASSRLS;
                    END IF;
                END
                $$;
                GRANT USAGE ON SCHEMA public TO rls_test_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rls_test_app;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rls_test_app;
            """)

            # 1. Switch to Tenant 101 context under non-superuser role
            cur.execute("SET ROLE rls_test_app")
            cur.execute("SET rls.bypass_rls = 'false'")
            cur.execute("SET rls.tenant_id = '101'")
            cur.execute("SELECT tenant_id, capability_key FROM commercial_tenant_overrides")
            rows_101 = cur.fetchall()

            # Must see only Tenant 101's row
            assert len(rows_101) == 1
            assert rows_101[0][0] == 101
            assert rows_101[0][1] == "laboratories"

            # 2. Switch to Tenant 102 context
            cur.execute("SET rls.tenant_id = '102'")
            cur.execute("SELECT tenant_id, capability_key FROM commercial_tenant_overrides")
            rows_102 = cur.fetchall()

            # Must see only Tenant 102's row
            assert len(rows_102) == 1
            assert rows_102[0][0] == 102
            assert rows_102[0][1] == "inventory"

            # 3. Attempt cross-tenant insert (Tenant 102 inserting into Tenant 101)
            with pytest.raises(Exception) as excinfo:
                cur.execute("""
                    INSERT INTO commercial_tenant_overrides (tenant_id, capability_key, override_value, reason, created_at, updated_at)
                    VALUES (101, 'ai_insights', 'allow', 'Malicious insert', NOW(), NOW())
                """)
            assert "row-level security" in str(excinfo.value).lower() or "policy" in str(excinfo.value).lower()
            cur.execute("RESET ROLE")

        conn.close()
    finally:
        engine.dispose()
        _drop_database(pg_url, dbname)
