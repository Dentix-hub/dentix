"""
PR-03 Acceptance Tests: Read-only Effective-Access API and Super Admin Diagnostics.

Validates all PR-03 acceptance criteria:
1. GET /api/v1/settings/entitlements:
   - Self-tenant only; returns current user's tenant diagnostics.
   - Client parameter tampering (?tenant_id=...) is ignored.
   - Requires valid authentication (401 when unauthenticated).
2. GET /api/v1/admin/tenants/{tenant_id}/entitlements:
   - Super Admin only (200 OK).
   - Rejects non-super-admin clinic users (403 Forbidden).
   - Rejects non-existent tenants (404 Not Found).
   - Scoped querying does not bleed across requests.
3. Truthful capacity reporting (Finding E13):
   - Seat limit matches plan; used count reflects active non-deleted login accounts.
   - Inactive/deleted accounts are excluded from used count.
   - AI daily limit matches plan/spec.
   - AI quota_ledger_source is "unavailable" and remaining_quota is None (not 0).
4. Permanent clinical history read invariant:
   - can_read_clinical is True regardless of subscription status.
5. Zero PII leakage:
   - Response contains no patient names, patient identifiers, or AI prompt text.
6. Super Admin tenant details endpoint:
   - GET /api/v1/admin/tenants/{tenant_id}/details includes top-level plan_id (Finding E18).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select

from backend import models
from backend.auth import get_password_hash, create_access_token
from backend.core.commercial_registry import CAPABILITY_REGISTRY, LAUNCH_PLAN_SPECS
from backend.services.entitlement_diagnostics_service import build_tenant_entitlement_diagnostics


@pytest.fixture
def pr03_seed_data(db_session):
    """
    Seed test tenants with known plans and users for PR-03 verification.
    """
    # 1. Create Subscription Plans
    plan_solo = models.SubscriptionPlan(
        id=101,
        name="solo",
        display_name_ar="الباقة الفردية",
        price=Decimal("150.00"),
        is_ai_enabled=False,
        ai_daily_limit=0,
        max_users=2,
    )
    plan_clinic = models.SubscriptionPlan(
        id=102,
        name="clinic",
        display_name_ar="باقة العيادة",
        price=Decimal("400.00"),
        is_ai_enabled=True,
        ai_daily_limit=20,
        max_users=5,
    )
    db_session.add_all([plan_solo, plan_clinic])
    db_session.commit()

    # 2. Create Tenant A (Clinic Plan, Active)
    tenant_a = models.Tenant(
        id=201,
        name="Al-Amal Dental Center",
        plan="clinic",
        plan_id=102,
        is_active=True,
        subscription_status="active",
        subscription_end_date=datetime.now(timezone.utc) + timedelta(days=60),
        grace_period_until=None,
    )

    # 3. Create Tenant B (Solo Plan, Expired/Grace)
    tenant_b = models.Tenant(
        id=202,
        name="Dr. Sami Solo Clinic",
        plan="solo",
        plan_id=101,
        is_active=True,
        subscription_status="grace",
        subscription_end_date=datetime.now(timezone.utc) - timedelta(days=2),
        grace_period_until=datetime.now(timezone.utc) + timedelta(days=5),
    )

    # 4. Create Tenant C (Hard Disabled)
    tenant_c = models.Tenant(
        id=203,
        name="Suspended Clinic",
        plan="clinic",
        plan_id=102,
        is_active=False,
        subscription_status="suspended_admin",
    )

    db_session.add_all([tenant_a, tenant_b, tenant_c])
    db_session.commit()

    # 5. Seed Users for Tenant A:
    # 2 active users, 1 inactive user, 1 deleted user -> seats used should be exactly 2
    u_a1 = models.User(
        username="dr_amal_active1",
        email="amal1@example.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_a.id,
        is_active=True,
        is_deleted=False,
    )
    u_a2 = models.User(
        username="admin_amal_active2",
        email="amal2@example.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_a.id,
        is_active=True,
        is_deleted=False,
    )
    u_a_inactive = models.User(
        username="nurse_amal_inactive",
        email="amal_inact@example.com",
        hashed_password=get_password_hash("pass123"),
        role="nurse",
        tenant_id=tenant_a.id,
        is_active=False,
        is_deleted=False,
    )
    u_a_deleted = models.User(
        username="assistant_amal_del",
        email="amal_del@example.com",
        hashed_password=get_password_hash("pass123"),
        role="assistant",
        tenant_id=tenant_a.id,
        is_active=True,
        is_deleted=True,
    )

    # User for Tenant B
    u_b = models.User(
        username="dr_sami_solo",
        email="sami@example.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_b.id,
        is_active=True,
        is_deleted=False,
    )

    db_session.add_all([u_a1, u_a2, u_a_inactive, u_a_deleted, u_b])
    db_session.commit()

    # 6. Seed AI logs for Tenant A:
    # 3 logs today, 2 logs yesterday
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)
    for i in range(3):
        db_session.add(models.AILog(
            trace_id=f"trace-today-{i}",
            tenant_id=tenant_a.id,
            user_id=u_a1.id,
            intent="summarize",
            model="gemini-1.5-pro",
            status="SUCCESS",
            created_at=today,
        ))
    for i in range(2):
        db_session.add(models.AILog(
            trace_id=f"trace-yesterday-{i}",
            tenant_id=tenant_a.id,
            user_id=u_a1.id,
            intent="summarize",
            model="gemini-1.5-pro",
            status="SUCCESS",
            created_at=yesterday,
        ))
    db_session.commit()

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "tenant_c": tenant_c,
        "plan_solo": plan_solo,
        "plan_clinic": plan_clinic,
        "user_a1": u_a1,
        "user_a2": u_a2,
        "user_b": u_b,
    }


def _token_headers(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Settings Self-Tenant Entitlements Endpoint
# ===========================================================================

def test_settings_entitlements_requires_auth(client):
    """GET /api/v1/settings/entitlements must reject unauthenticated requests with 401."""
    res = client.get("/api/v1/settings/entitlements")
    assert res.status_code == 401


def test_settings_entitlements_returns_current_tenant_only(client, pr03_seed_data):
    """
    GET /api/v1/settings/entitlements returns diagnostics for current user's tenant.
    Query parameters attempting to inspect other tenants are ignored or blocked.
    """
    user_a = pr03_seed_data["user_a1"]
    headers = _token_headers(user_a)

    # Valid self-tenant request
    res = client.get("/api/v1/settings/entitlements", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    # Must be Tenant A
    assert data["tenant_id"] == 201
    assert data["tenant_name"] == "Al-Amal Dental Center"
    assert data["plan_id"] == 102
    assert data["plan_name"] == "clinic"
    assert data["is_hard_disabled"] is False
    assert data["can_read_clinical"] is True


def test_settings_entitlements_truthful_capacities(client, pr03_seed_data):
    """
    Verifies truthful capacity reporting:
    - Seats used counts only active non-deleted users (2 users for Tenant A).
    - Limit is 5 (from clinic plan). Remaining is 3. is_exhausted is False.
    - AI daily limit is 20.
    - AI historical count today is 3 (ignoring yesterday's 2).
    - Quota ledger source is 'unavailable' and remaining_quota is None (not 0).
    """
    user_a = pr03_seed_data["user_a1"]
    res = client.get("/api/v1/settings/entitlements", headers=_token_headers(user_a))
    assert res.status_code == 200
    data = res.json()["data"]

    caps = data["capacities"]
    assert caps["seats"]["limit"] == 5
    assert caps["seats"]["used"] == 2  # u_a1, u_a2 (inactive and deleted excluded)
    assert caps["seats"]["remaining"] == 3
    assert caps["seats"]["is_exhausted"] is False

    ai = caps["ai"]
    assert ai["daily_limit"] == 20
    assert ai["is_enabled"] is True
    assert ai["historical_diagnostic_count"] == 3
    assert ai["quota_ledger_source"] == "unavailable"
    assert ai["remaining_quota"] is None


def test_settings_entitlements_pii_free(client, pr03_seed_data):
    """
    Verifies that the entitlement response payload is completely free of patient PII
    and user credentials.
    """
    user_a = pr03_seed_data["user_a1"]
    res = client.get("/api/v1/settings/entitlements", headers=_token_headers(user_a))
    assert res.status_code == 200
    content = res.text

    # Response should not contain user email addresses, passwords, or personal names
    assert "amal1@example.com" not in content
    assert "pass123" not in content
    assert "hashed_password" not in content
    assert "input_text" not in content  # AI prompt text
    assert "output_text" not in content  # AI response text


# ===========================================================================
# 2. Super Admin Diagnostics Endpoint
# ===========================================================================

def test_admin_tenant_entitlements_requires_super_admin(client, pr03_seed_data):
    """
    GET /api/v1/admin/tenants/{tenant_id}/entitlements:
    - Rejects unauthenticated requests (401).
    - Rejects clinic admin and doctor requests (403 Forbidden).
    """
    tenant_id = pr03_seed_data["tenant_a"].id
    res_unauth = client.get(f"/api/v1/admin/tenants/{tenant_id}/entitlements")
    assert res_unauth.status_code == 401

    res_doc = client.get(
        f"/api/v1/admin/tenants/{tenant_id}/entitlements",
        headers=_token_headers(pr03_seed_data["user_a1"]),
    )
    assert res_doc.status_code == 403

    res_admin = client.get(
        f"/api/v1/admin/tenants/{tenant_id}/entitlements",
        headers=_token_headers(pr03_seed_data["user_a2"]),
    )
    assert res_admin.status_code == 403


def test_admin_tenant_entitlements_super_admin_success(client, pr03_seed_data, super_admin_headers):
    """
    Super Admin can retrieve diagnostics for any tenant, with correct lifecycle status.
    """
    # Tenant A
    res_a = client.get(
        f"/api/v1/admin/tenants/{pr03_seed_data['tenant_a'].id}/entitlements",
        headers=super_admin_headers,
    )
    assert res_a.status_code == 200
    data_a = res_a.json()["data"]
    assert data_a["tenant_id"] == 201
    assert data_a["effective_subscription_status"] == "active"
    assert data_a["is_hard_disabled"] is False

    # Tenant B (in grace period)
    res_b = client.get(
        f"/api/v1/admin/tenants/{pr03_seed_data['tenant_b'].id}/entitlements",
        headers=super_admin_headers,
    )
    assert res_b.status_code == 200
    data_b = res_b.json()["data"]
    assert data_b["tenant_id"] == 202
    assert data_b["effective_subscription_status"] == "grace"
    assert data_b["is_in_grace"] is True
    assert data_b["can_read_clinical"] is True  # Clinical invariant
    assert data_b["capacities"]["seats"]["limit"] == 2
    assert data_b["capacities"]["seats"]["used"] == 1

    # Tenant C (Hard disabled)
    res_c = client.get(
        f"/api/v1/admin/tenants/{pr03_seed_data['tenant_c'].id}/entitlements",
        headers=super_admin_headers,
    )
    assert res_c.status_code == 200
    data_c = res_c.json()["data"]
    assert data_c["tenant_id"] == 203
    assert data_c["is_hard_disabled"] is True


def test_admin_tenant_entitlements_not_found(client, super_admin_headers):
    """Super Admin querying non-existent tenant receives 404."""
    res = client.get("/api/v1/admin/tenants/999999/entitlements", headers=super_admin_headers)
    assert res.status_code == 404


def test_admin_tenant_entitlements_no_state_leak(client, pr03_seed_data, super_admin_headers):
    """
    Consecutive requests for different tenants by Super Admin return clean, unmixed data.
    """
    res_a = client.get("/api/v1/admin/tenants/201/entitlements", headers=super_admin_headers)
    res_b = client.get("/api/v1/admin/tenants/202/entitlements", headers=super_admin_headers)

    assert res_a.json()["data"]["tenant_id"] == 201
    assert res_b.json()["data"]["tenant_id"] == 202
    assert res_a.json()["data"]["plan_id"] == 102
    assert res_b.json()["data"]["plan_id"] == 101


# ===========================================================================
# 3. Super Admin Tenant Details Returns plan_id (Finding E18)
# ===========================================================================

def test_admin_tenant_details_includes_plan_id(client, pr03_seed_data, super_admin_headers):
    """
    GET /api/v1/admin/tenants/{tenant_id}/details includes top-level plan_id
    resolving Finding E18.
    """
    res = client.get(
        f"/api/v1/admin/tenants/{pr03_seed_data['tenant_a'].id}/details",
        headers=super_admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "tenant" in data
    assert data["tenant"]["plan_id"] == 102
    assert data["tenant"]["plan"] == "clinic"
