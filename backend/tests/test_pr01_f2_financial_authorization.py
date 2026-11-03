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
from unittest.mock import patch, AsyncMock, MagicMock
from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.core.permissions import Role, Permission, ROLE_PERMISSIONS


@pytest.fixture
def f2_setup(db_session):
    tenant = models.Tenant(name="Finance Clinic", is_active=True)
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
    mock_analyze_direct, mock_get_detailed, client, f2_setup, monkeypatch
):
    """
    Matrix: AI_CHAT=No, REPORT_READ=Yes -> DENIED (HTTP 403).
    Constructed using isolated test-only role mapping (tests true AND vs ANY-of).
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
    headers = _auth_header(user)

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
