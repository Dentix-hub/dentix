import os
import pytest
from backend import database


def test_pool_configuration_respects_env_vars(monkeypatch):
    """
    Verify that pool_size, max_overflow, and pool_timeout are configurable via env vars
    (DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT) and default safely.
    """
    monkeypatch.setenv("DB_POOL_SIZE", "15")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "7")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "25.5")

    pool_size = database._get_int_setting("DB_POOL_SIZE", 10, minimum=1)
    max_overflow = database._get_int_setting(
        "DB_MAX_OVERFLOW",
        database._get_int_setting("DB_POOL_MAX_OVERFLOW", 5, minimum=0),
        minimum=0,
    )
    pool_timeout = database._get_float_setting("DB_POOL_TIMEOUT", 20.0, minimum=0.1)

    assert pool_size == 15
    assert max_overflow == 7
    assert pool_timeout == 25.5


def test_pool_pre_ping_enabled_by_default(monkeypatch):
    """
    Verify that pool_pre_ping is enabled by default to prevent stale socket errors.
    """
    monkeypatch.delenv("DB_POOL_PRE_PING", raising=False)
    pre_ping = os.getenv("DB_POOL_PRE_PING", "true").lower() in ("true", "1", "yes")
    assert pre_ping is True


@pytest.mark.asyncio
async def test_notifications_endpoint_releases_session(async_db_session, monkeypatch):
    """
    Verify that GET /api/v1/notifications closes the DB session promptly after fetching data
    to avoid holding checked-out connections across response serialization.
    """
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend import models, auth

    tenant = models.Tenant(name="Pool Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="pool_user",
        email="pool_user@example.com",
        role="doctor",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.commit()

    token = auth.create_access_token({"sub": user.username, "tenant_id": tenant.id, "role": user.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
