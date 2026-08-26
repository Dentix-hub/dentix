from backend import models
from backend.database import get_async_db
from backend.main import app
import anyio


def test_notification_broadcast_invariants(client, super_admin_headers):
    created_tenant = {}

    async def seed():
        async for session in app.dependency_overrides[get_async_db]():
            real_tenant = models.Tenant(
                name="Targeted Notification Tenant MS16",
                is_active=True,
            )
            session.add(real_tenant)
            await session.commit()
            await session.refresh(real_tenant)
            created_tenant["id"] = real_tenant.id
            break

    anyio.run(seed)
    tenant_id = created_tenant["id"]

    # 1. Global notification should succeed and have tenant_id == None
    res_global = client.post(
        "/api/v1/notifications/broadcast",
        headers=super_admin_headers,
        json={
            "title": "Global Maintenance Notice",
            "content": "System update scheduled for midnight.",
            "type": "info",
            "is_global": True,
            "tenant_id": 9999,  # Should be normalized to None
        },
    )
    assert res_global.status_code == 200, res_global.text
    data_global = res_global.json()["data"]
    assert data_global["is_global"] is True
    assert data_global["tenant_id"] is None

    # 2. Targeted notification with real tenant should succeed
    res_targeted = client.post(
        "/api/v1/notifications/broadcast",
        headers=super_admin_headers,
        json={
            "title": "Clinic Specific Alert",
            "content": "Your subscription will expire soon.",
            "type": "warning",
            "is_global": False,
            "tenant_id": tenant_id,
        },
    )
    assert res_targeted.status_code == 200, res_targeted.text
    data_targeted = res_targeted.json()["data"]
    assert data_targeted["is_global"] is False
    assert data_targeted["tenant_id"] == tenant_id

    # 3. Targeted notification without tenant_id should be rejected with 422
    res_missing_tenant = client.post(
        "/api/v1/notifications/broadcast",
        headers=super_admin_headers,
        json={
            "title": "Invalid Targeted Alert",
            "content": "Missing tenant",
            "type": "error",
            "is_global": False,
            "tenant_id": None,
        },
    )
    assert res_missing_tenant.status_code == 422

    # 4. Targeted notification with non-existent tenant_id should be rejected with 404
    res_nonexistent_tenant = client.post(
        "/api/v1/notifications/broadcast",
        headers=super_admin_headers,
        json={
            "title": "Invalid Targeted Alert Nonexistent",
            "content": "Nonexistent tenant",
            "type": "error",
            "is_global": False,
            "tenant_id": 987654321,
        },
    )
    assert res_nonexistent_tenant.status_code == 404
    assert "not found" in res_nonexistent_tenant.json()["detail"].lower()
