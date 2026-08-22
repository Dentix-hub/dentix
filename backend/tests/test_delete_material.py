"""
Test: Material Deletion Flow
Verifies that materials can be deleted when empty and blocked when in use.
"""

from datetime import date

import pytest
from sqlalchemy import select

from backend.models.inventory import Batch, Material, StockItem, StockMovement, Warehouse
from backend.services.inventory_service import InventoryService


def test_delete_empty_material(client, admin_headers):
    """Test that a material with no stock can be deleted."""
    # 1. Create Material
    mat_data = {
        "name": "Temp Material",
        "type": "NON_DIVISIBLE",
        "base_unit": "box",
        "alert_threshold": 5,
    }
    resp = client.post("/api/v1/inventory/materials", json=mat_data, headers=admin_headers)
    assert resp.status_code == 200 or resp.status_code == 201
    res = resp.json()
    assert res["success"] is True
    mat = res["data"]

    # 2. Delete it (Should succeed)
    del_resp = client.delete(f"/api/v1/inventory/materials/{mat['id']}", headers=admin_headers)
    assert del_resp.status_code == 204

    stock_resp = client.get("/api/v1/inventory/stock", headers=admin_headers)
    assert stock_resp.status_code == 200
    assert all(item["material_id"] != mat["id"] for item in stock_resp.json()["data"])


def test_delete_material_with_stock_blocked(client, admin_headers, admin_user, db_session):
    """Test that a material with active stock cannot be deleted."""
    # 1. Create Material
    mat_data = {
        "name": "Stock Material",
        "type": "NON_DIVISIBLE",
        "base_unit": "box",
    }
    resp = client.post("/api/v1/inventory/materials", json=mat_data, headers=admin_headers)
    assert resp.status_code == 200 or resp.status_code == 201
    res = resp.json()
    assert res["success"] is True
    mat = res["data"]

    # 2. Seed active stock directly; the receive endpoint has separate response-loading
    # behavior that is not part of this deletion regression.
    warehouse = Warehouse(
        tenant_id=admin_user.tenant_id,
        name="Delete Test Warehouse",
        type="MAIN",
    )
    db_session.add(warehouse)
    db_session.flush()
    batch = Batch(
        tenant_id=admin_user.tenant_id,
        material_id=mat["id"],
        batch_number="DELETE-BLOCK-1",
        expiry_date=date(2030, 12, 31),
    )
    db_session.add(batch)
    db_session.flush()
    db_session.add(
        StockItem(
            tenant_id=admin_user.tenant_id,
            warehouse_id=warehouse.id,
            batch_id=batch.id,
            quantity=10.0,
        )
    )
    db_session.commit()

    # 3. Try Delete (conflict: active stock must not disappear)
    del_resp = client.delete(f"/api/v1/inventory/materials/{mat['id']}", headers=admin_headers)
    assert del_resp.status_code == 409
    assert "active stock" in del_resp.json()["detail"]


def test_create_material_category_is_idempotent(client, admin_headers):
    """Repeated category submission returns the existing global category."""
    payload = {
        "name_en": "Regression Category 188",
        "name_ar": "تصنيف اختبار 188",
        "default_type": "DIVISIBLE",
        "default_unit": "g",
    }
    first = client.post("/api/v1/inventory/categories", json=payload, headers=admin_headers)
    second = client.post(
        "/api/v1/inventory/categories",
        json={**payload, "name_en": payload["name_en"].upper()},
        headers=admin_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first.json()["data"]["id"]


@pytest.mark.asyncio
async def test_delete_zero_balance_material_preserves_audit_history(async_db_session):
    """A zero-balance material is hidden without deleting its stock ledger."""
    tenant_id = 188
    material = Material(
        id=1881,
        tenant_id=tenant_id,
        name="Historical Material",
        type="NON_DIVISIBLE",
        base_unit="box",
    )
    warehouse = Warehouse(id=1882, tenant_id=tenant_id, name="Main", type="MAIN")
    batch = Batch(
        id=1883,
        tenant_id=tenant_id,
        material_id=material.id,
        batch_number="HIST-1",
        expiry_date=date(2030, 1, 1),
    )
    stock_item = StockItem(
        id=1884,
        tenant_id=tenant_id,
        warehouse_id=warehouse.id,
        batch_id=batch.id,
        quantity=0.0,
    )
    movement = StockMovement(
        id=1885,
        stock_item_id=stock_item.id,
        change_amount=-1.0,
        reason="USAGE",
    )
    async_db_session.add_all([material, warehouse, batch, stock_item, movement])
    await async_db_session.commit()

    await InventoryService().delete_material(material.id, tenant_id, async_db_session)

    await async_db_session.refresh(material)
    assert material.is_deleted is True
    assert material.deleted_at is not None
    assert await async_db_session.scalar(
        select(StockMovement).where(StockMovement.id == movement.id)
    ) is not None
    assert await async_db_session.scalar(
        select(Batch).where(Batch.id == batch.id)
    ) is not None
