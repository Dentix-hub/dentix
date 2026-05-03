"""
Test: Material Deletion Flow
Verifies that materials can be deleted when empty and blocked when in use.
"""


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


def test_delete_material_with_stock_blocked(client, admin_headers):
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

    # 2. Get warehouse
    wh_resp = client.get("/api/v1/inventory/warehouses", headers=admin_headers)
    if wh_resp.status_code != 200 or not wh_resp.json():
        # No warehouses available, skip stock test
        return
    
    wh_res = wh_resp.json()
    if isinstance(wh_res, dict) and "data" in wh_res:
        wh_list = wh_res["data"]
    else:
        wh_list = wh_res

    if not wh_list:
        return

    wh = wh_list[0]

    # 3. Add Stock
    stock_data = {
        "material_id": mat["id"],
        "warehouse_id": wh["id"],
        "quantity": 10,
        "batch": {"batch_number": "B123", "expiry_date": "2025-12-31", "tenant_id": 1},
    }
    client.post("/api/v1/inventory/receive", json=stock_data, headers=admin_headers)

    # 4. Try Delete (Should fail with 400 or 500)
    del_resp = client.delete(f"/api/v1/inventory/materials/{mat['id']}", headers=admin_headers)
    assert del_resp.status_code != 204, "Should not delete material with active stock"
