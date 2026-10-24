import pytest
from httpx import AsyncClient, ASGITransport

from backend import models
from backend.main import app
from backend.auth import create_access_token


@pytest.mark.asyncio
async def test_get_next_visit_requests_http(async_db_session):
    tenant = models.Tenant(name="NVR Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="receptionist_nvr",
        email="receptionist_nvr@example.com",
        role="receptionist",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.commit()

    token = create_access_token(data={"sub": user.username, "tenant_id": tenant.id, "role": user.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/next-visit-requests?status=all",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["data"] == []
