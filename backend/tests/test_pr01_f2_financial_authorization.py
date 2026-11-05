"""
Regression tests for PR-01 F2: Clinic-wide AI financial analysis authorization.

Verifies that POST /api/v1/analytics/ai/analyze-clinic requires true AND:
Permission.AI_CHAT AND Permission.REPORT_READ.

Denial assertions:
- HTTP 403 Forbidden
- get_detailed_analytics was not called
- AIService.analyze_direct was not called
- AI provider was not called
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import select, func
from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.core.permissions import Role, Permission, ROLE_PERMISSIONS, has_permission
from backend.ai.executor import ToolExecutor


@pytest.fixture
def f2_setup(db_session):
    # Authorization tests require a valid paid-AI configuration, not missing-plan fallback.
    plan = models.SubscriptionPlan(name="professional", display_name_ar="Synthetic", price=400, max_users=5, is_ai_enabled=True, ai_daily_limit=10, features='{"clinical":true,"billing":true,"ai_insights":true}')
    db_session.add(plan)
    db_session.flush()
    tenant = models.Tenant(name="Finance Clinic", is_active=True, plan_id=plan.id, plan=plan.name)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Doctor: has AI_CHAT=Yes, REPORT_READ=No
    doctor = models.User(
        username="doc_finance_test",
        email="doc_finance_test@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
    )
    # Admin: has AI_CHAT=Yes, REPORT_READ=Yes
    admin = models.User(
        username="admin_finance_test",
        email="admin_finance_test@test.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant.id,
        is_active=True,
    )
    # Guest: has AI_CHAT=No, REPORT_READ=No
    guest = models.User(
        username="guest_finance_test",
        email="guest_finance_test@test.com",
        hashed_password=get_password_hash("pass123"),
        role="guest",
        tenant_id=tenant.id,
        is_active=True,
    )
    db_session.add_all([doctor, admin, guest])
    db_session.commit()
    for u in (doctor, admin, guest):
        db_session.refresh(u)

    return {
        "tenant": tenant,
        "doctor": doctor,
        "admin": admin,
        "guest": guest,
    }


def _auth_header(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


SAMPLE_STATS_PAYLOAD = {
    "revenue": 50000.0,
    "breakdown": {"expenses": 10000.0, "lab_costs": 5000.0, "material_costs": 3000.0},
    "total_costs": 18000.0,
    "net_profit": 32000.0,
    "margin_percent": 64.0,
}


@patch("backend.routers.analytics_ai_v2.get_detailed_analytics", new_callable=AsyncMock)
@patch("backend.services.ai_service.AIService.analyze_direct", new_callable=AsyncMock)
def test_doctor_lacking_report_read_is_denied_analyze_clinic(
    mock_analyze_direct, mock_get_detailed, client, f2_setup
):
    """
    Matrix: AI_CHAT=Yes, REPORT_READ=No -> DENIED (HTTP 403).
    Ensures get_detailed_analytics, analyze_direct, and provider are not called.
    """
    mock_analyze_direct.return_value = MagicMock(message="mocked")
    doctor = f2_setup["doctor"]
    headers = _auth_header(doctor)

    res = client.post(
        "/api/v1/admin/ai/analyze-clinic",
        json=SAMPLE_STATS_PAYLOAD,
        headers=headers,
    )

    assert res.status_code == 403
    mock_get_detailed.assert_not_called()
    mock_analyze_direct.assert_not_called()


@patch("backend.routers.analytics_ai_v2.get_detailed_analytics", new_callable=AsyncMock)
@patch("backend.services.ai_service.AIService.analyze_direct", new_callable=AsyncMock)
def test_guest_lacking_both_permissions_is_denied_analyze_clinic(
    mock_analyze_direct, mock_get_detailed, client, f2_setup
):
    """
    Matrix: AI_CHAT=No, REPORT_READ=No -> DENIED (HTTP 403).
    """
    guest = f2_setup["guest"]
    headers = _auth_header(guest)

    res = client.post(
        "/api/v1/admin/ai/analyze-clinic",
        json=SAMPLE_STATS_PAYLOAD,
        headers=headers,
    )

    assert res.status_code == 403
    mock_get_detailed.assert_not_called()
    mock_analyze_direct.assert_not_called()


@patch("backend.routers.analytics_ai_v2.get_detailed_analytics", new_callable=AsyncMock)
@patch("backend.services.ai_service.AIService.analyze_direct", new_callable=AsyncMock)
def test_user_with_report_read_but_no_ai_chat_is_denied_analyze_clinic(
    mock_analyze_direct, mock_get_detailed, client, f2_setup, monkeypatch, db_session
):
    """
    R4: Matrix: AI_CHAT=No, REPORT_READ=Yes -> DENIED (HTTP 403).
    Persists test-only role to DB so authentication dependency reloads intended role.
    Verifies that a true-AND check blocks finance-only roles.
    """
    # Create test-only role with REPORT_READ but without AI_CHAT
    test_role = Role.ASSISTANT
    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        test_role,
        {Permission.REPORT_READ},  # Only REPORT_READ, NO AI_CHAT
    )

    user = f2_setup["doctor"]
    user.role = test_role.value
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.role == test_role.value
    assert has_permission(user.role, Permission.REPORT_READ)
    assert not has_permission(user.role, Permission.AI_CHAT)

    headers = _auth_header(user)

    seen = []
    real_has_permission = has_permission

    def spy_has_permission(role, permission):
        seen.append((role, permission.value))
        return real_has_permission(role, permission)

    with patch("backend.core.permissions.has_permission", side_effect=spy_has_permission):
        res = client.post(
            "/api/v1/admin/ai/analyze-clinic",
            json=SAMPLE_STATS_PAYLOAD,
            headers=headers,
        )

    assert res.status_code == 403
    assert any(role == test_role.value for role, _ in seen), f"Intended role was not checked: {seen}"
    mock_get_detailed.assert_not_called()
    mock_analyze_direct.assert_not_called()


@patch("backend.routers.analytics_ai_v2.get_detailed_analytics", new_callable=AsyncMock)
@patch("backend.services.ai_service.AIService.analyze_direct", new_callable=AsyncMock)
def test_admin_with_both_permissions_is_allowed_analyze_clinic(
    mock_analyze_direct, mock_get_detailed, client, f2_setup
):
    """
    Matrix: AI_CHAT=Yes, REPORT_READ=Yes -> ALLOWED (HTTP 200).
    Runs with authenticated tenant context.
    """
    mock_get_detailed.return_value = "Detailed KPI context"
    mock_response = AsyncMock()
    mock_response.message = "Analysis successful"
    mock_analyze_direct.return_value = mock_response

    admin = f2_setup["admin"]
    headers = _auth_header(admin)

    res = client.post(
        "/api/v1/admin/ai/analyze-clinic",
        json=SAMPLE_STATS_PAYLOAD,
        headers=headers,
    )

    assert res.status_code == 200
    mock_get_detailed.assert_called_once()
    mock_analyze_direct.assert_called_once()


@pytest.mark.asyncio
async def test_doctor_cannot_obtain_clinic_revenue_via_dashboard_stats(async_db_session, f2_setup):
    """
    R1: get_dashboard_stats requires APPOINTMENT_READ for operational statistics,
    but period_revenue requires AI_CHAT AND REPORT_READ.
    Doctor has AI_CHAT and APPOINTMENT_READ, but lacks REPORT_READ.
    Revenue must NOT be queried or returned.
    """
    doctor = f2_setup["doctor"]
    admin = f2_setup["admin"]
    tenant_id = f2_setup["tenant"].id

    assert has_permission(doctor.role, Permission.AI_CHAT)
    assert has_permission(doctor.role, Permission.APPOINTMENT_READ)
    assert not has_permission(doctor.role, Permission.REPORT_READ)
    assert has_permission(admin.role, Permission.REPORT_READ)

    # Create patient and payment
    patient = models.Patient(
        tenant_id=tenant_id,
        name="Revenue Test Patient",
        phone="01012345678",
    )
    async_db_session.add(patient)
    await async_db_session.commit()
    await async_db_session.refresh(patient)

    payment = models.Payment(
        tenant_id=tenant_id,
        patient_id=patient.id,
        amount=Decimal("777.00"),
        date=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    async_db_session.add(payment)
    await async_db_session.commit()

    # Doctor executes get_dashboard_stats — spy on SQL to verify NO payments query is executed
    from sqlalchemy import event

    doc_sql = []

    def _capture_doc_sql(conn, cursor, statement, parameters, context, executemany):
        doc_sql.append(statement)

    event.listen(async_db_session.sync_session.bind, "before_cursor_execute", _capture_doc_sql)
    try:
        doc_executor = ToolExecutor(async_db_session, doctor)
        doc_result = await doc_executor.execute("get_dashboard_stats", {"period": "today"})
        doc_inject_result = await doc_executor.execute(
            "get_dashboard_stats", {"period": "today", "include_revenue": True}
        )
    finally:
        event.remove(async_db_session.sync_session.bind, "before_cursor_execute", _capture_doc_sql)

    assert doc_result.get("success") is True
    # Operational stats are present
    assert "period_appointments" in doc_result
    assert "total_patients" in doc_result
    # Revenue is absent for doctor lacking REPORT_READ
    assert "period_revenue" not in doc_result
    assert "period_revenue" not in doc_inject_result
    # Financial payments table must NOT have been queried for unauthorized doctor
    assert not any("payments" in stmt.lower() for stmt in doc_sql), (
        f"Unexpected payments query executed for doctor without REPORT_READ: {doc_sql}"
    )

    # Admin executes get_dashboard_stats -> revenue IS queried and returned
    admin_sql = []

    def _capture_admin_sql(conn, cursor, statement, parameters, context, executemany):
        admin_sql.append(statement)

    event.listen(async_db_session.sync_session.bind, "before_cursor_execute", _capture_admin_sql)
    try:
        admin_executor = ToolExecutor(async_db_session, admin)
        admin_result = await admin_executor.execute("get_dashboard_stats", {"period": "today"})
    finally:
        event.remove(async_db_session.sync_session.bind, "before_cursor_execute", _capture_admin_sql)

    assert admin_result.get("success") is True
    assert "period_revenue" in admin_result
    assert admin_result["period_revenue"] == 777.0
    assert any("payments" in stmt.lower() for stmt in admin_sql)


@pytest.mark.asyncio
async def test_dashboard_stats_cross_tenant_isolation(async_db_session, f2_setup):
    """
    R1: Cross-tenant payments must never be aggregated into another tenant's dashboard revenue.
    """
    admin_1 = f2_setup["admin"]

    # Create Tenant 2
    tenant_2 = models.Tenant(name="Other Tenant Clinic", is_active=True)
    async_db_session.add(tenant_2)
    await async_db_session.commit()
    await async_db_session.refresh(tenant_2)

    patient_2 = models.Patient(
        tenant_id=tenant_2.id,
        name="Tenant 2 Patient",
        phone="01099999999",
    )
    async_db_session.add(patient_2)
    await async_db_session.commit()
    await async_db_session.refresh(patient_2)

    payment_2 = models.Payment(
        tenant_id=tenant_2.id,
        patient_id=patient_2.id,
        amount=Decimal("9999.00"),
        date=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    async_db_session.add(payment_2)
    await async_db_session.commit()

    admin_1_executor = ToolExecutor(async_db_session, admin_1)
    admin_1_result = await admin_1_executor.execute("get_dashboard_stats", {"period": "today"})
    assert admin_1_result.get("success") is True
    # Tenant 2's 9999 payment must NOT appear in Tenant 1's revenue
    assert admin_1_result.get("period_revenue", 0.0) != 9999.0
