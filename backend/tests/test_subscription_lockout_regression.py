"""
Regression test for P01-01 & P01-03: Proving that unconfigured/default startup or subscription expiry
must NOT set tenant.is_active = False or cause total tenant lockout.
"""

from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend import models
from backend.models.tenant import Tenant
from backend.workers.subscription_checker import check_expired_subscriptions


@pytest.mark.asyncio
async def test_subscription_worker_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SUBSCRIPTION_WORKER_ENABLED", raising=False)
    db = AsyncMock()
    count = await check_expired_subscriptions.fn(db)
    assert count == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_subscription_worker_enforce_mode_preserves_is_active(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")

    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    tenant = Tenant(
        id=999,
        name="Test Clinic",
        is_active=True,
        subscription_end_date=past_date,
        grace_period_until=past_date,
        subscription_status="active",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tenant]
    db.execute.return_value = mock_result

    count = await check_expired_subscriptions.fn(db)
    assert count == 1
    assert tenant.subscription_status == "expired"
    assert tenant.is_active is True, "CRITICAL: tenant.is_active must remain True to preserve clinical reads!"


@pytest.mark.asyncio
async def test_subscription_worker_observe_mode_does_not_mutate(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "observe")

    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    tenant = Tenant(
        id=999,
        name="Test Clinic",
        is_active=True,
        subscription_end_date=past_date,
        grace_period_until=past_date,
        subscription_status="active",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tenant]
    db.execute.return_value = mock_result

    count = await check_expired_subscriptions.fn(db)
    assert count == 1
    assert tenant.subscription_status == "active"
    assert tenant.is_active is True
    db.commit.assert_not_called()


@pytest.mark.parametrize("mode", ["off", "observe"])
def test_expired_tenant_can_create_patient_when_enforcement_is_not_active(
    client,
    db_session,
    test_tenant,
    test_user,
    auth_headers,
    monkeypatch,
    mode,
):
    """The auth dependency must honor the centralized safe-mode contract."""
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", mode)
    expired_at = datetime.now(timezone.utc) - timedelta(days=5)
    test_tenant.subscription_status = "active"
    test_tenant.subscription_end_date = expired_at
    test_tenant.grace_period_until = expired_at
    db_session.commit()

    response = client.post(
        "/api/v1/patients",
        headers=auth_headers,
        json={
            "name": "Subscription mode regression patient",
            "phone": "01000000000",
            "age": 30,
        },
    )

    assert response.status_code == 200, response.text
    patient_id = response.json()["data"]["id"]

    treatment_response = client.post(
        "/api/v1/treatments",
        headers=auth_headers,
        json={
            "patient_id": patient_id,
            "tooth_number": 11,
            "procedure": "Subscription mode regression treatment",
            "cost": 100,
            "discount": 0,
            "skip_stock_check": True,
        },
    )

    assert treatment_response.status_code == 200, treatment_response.text


def test_enforced_subscription_denial_is_persisted_without_patient_payload(
    client,
    db_session,
    test_tenant,
    test_user,
    auth_headers,
    super_admin_headers,
    monkeypatch,
):
    """Expected write denials remain observable without persisting clinical input."""
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")
    expired_at = datetime.now(timezone.utc) - timedelta(days=5)
    test_tenant.subscription_status = "expired"
    test_tenant.subscription_end_date = expired_at
    test_tenant.grace_period_until = expired_at
    db_session.commit()

    patient_name = "Never persist this patient name"
    patient_phone = "01999999999"
    untrusted_trace_id = "patient-name-must-not-enter-the-error-log"
    response = client.post(
        "/api/v1/patients",
        headers={**auth_headers, "X-Trace-ID": untrusted_trace_id},
        json={"name": patient_name, "phone": patient_phone, "age": 30},
    )

    assert response.status_code == 403
    db_session.expire_all()
    logged = (
        db_session.query(models.SystemError)
        .filter(models.SystemError.tenant_id == test_tenant.id)
        .order_by(models.SystemError.id.desc())
        .first()
    )
    assert logged is not None
    assert logged.level == "WARNING"
    assert logged.source == "BACKEND"
    assert logged.method == "POST"
    assert logged.path.endswith("/api/v1/patients")
    assert logged.user_id == test_user.id
    assert patient_name not in logged.message
    assert patient_phone not in logged.message
    assert untrusted_trace_id not in logged.message

    admin_response = client.get(
        "/api/v1/admin/system/logs?skip=0&limit=50",
        headers=super_admin_headers,
    )
    assert admin_response.status_code == 200, admin_response.text
    assert any(item["id"] == logged.id for item in admin_response.json()["data"])


def test_csrf_write_denial_is_persisted_without_request_payload(
    client,
    db_session,
    test_tenant,
    test_user,
    monkeypatch,
):
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "off")
    from backend.auth import create_access_token

    token = create_access_token(
        data={
            "sub": test_user.username,
            "role": test_user.role,
            "tenant_id": test_user.tenant_id,
        }
    )
    client.cookies.set("access_token", token)
    patient_name = "Never persist CSRF patient name"
    response = client.post(
        "/api/v1/patients",
        json={"name": patient_name, "phone": "01888888888", "age": 30},
    )

    assert response.status_code == 403
    db_session.expire_all()
    logged = (
        db_session.query(models.SystemError)
        .filter(models.SystemError.tenant_id == test_tenant.id)
        .order_by(models.SystemError.id.desc())
        .first()
    )
    assert logged is not None
    assert logged.message.startswith("HTTP 403 response")
    assert logged.method == "POST"
    assert logged.path.endswith("/api/v1/patients")
    assert patient_name not in logged.message


def test_anonymous_csrf_denial_does_not_create_a_log_flooding_primitive(
    client,
    db_session,
):
    before = db_session.query(models.SystemError).count()

    response = client.post(
        "/api/v1/patients",
        json={"name": "Anonymous payload", "phone": "01777777777", "age": 30},
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.query(models.SystemError).count() == before
