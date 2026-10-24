import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from backend import models
from backend.main import app
from backend.auth import create_access_token


@pytest.mark.asyncio
async def test_get_material_stock_loads_relationships_without_500(async_db_session):
    """
    Reproduces staging issue:
    GET /api/v1/inventory/materials/{id}/stock returned 500 due to lazy-loading
    relationships (batch, warehouse) in StockItemRead schema under async session.
    """
    tenant = models.Tenant(name="Inventory Stock Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="inv_doctor",
        email="inv_doctor@example.com",
        role="doctor",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.flush()

    warehouse = models.Warehouse(name="Dental Supply WH", tenant_id=tenant.id)
    async_db_session.add(warehouse)
    await async_db_session.flush()

    material = models.Material(
        name="Articaine 4%",
        type="DIVISIBLE",
        base_unit="carpule",
        tenant_id=tenant.id,
    )
    async_db_session.add(material)
    await async_db_session.flush()

    batch = models.Batch(
        material_id=material.id,
        tenant_id=tenant.id,
        batch_number="B-ART-99",
        expiry_date=datetime.now(timezone.utc),
    )
    async_db_session.add(batch)
    await async_db_session.flush()

    stock_item = models.StockItem(
        warehouse_id=warehouse.id,
        batch_id=batch.id,
        tenant_id=tenant.id,
        quantity=50.0,
    )
    async_db_session.add(stock_item)
    await async_db_session.commit()

    token = create_access_token(data={"sub": user.username, "tenant_id": tenant.id, "role": user.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/inventory/materials/{material.id}/stock",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    items = res_data["data"]
    assert len(items) == 1
    assert items[0]["id"] == stock_item.id
    assert items[0]["quantity"] == 50.0
    assert items[0]["batch"]["batch_number"] == "B-ART-99"
    assert items[0]["warehouse"]["name"] == "Dental Supply WH"


@pytest.mark.asyncio
async def test_get_material_stock_nonexistent_returns_404(async_db_session):
    tenant = models.Tenant(name="404 Stock Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="inv_doctor_404",
        email="inv_doctor_404@example.com",
        role="doctor",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.commit()

    token = create_access_token(data={"sub": user.username, "tenant_id": tenant.id, "role": user.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/inventory/materials/999999/stock",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert "Material not found" in response.json()["detail"]
