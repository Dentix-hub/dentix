
def test_bom_flow(client, admin_headers):
    """
    Test Bill of Materials (BOM) flow:
    1. Create Material
    2. Create Procedure
    3. Link Material to Procedure (Set Weight)
    4. Verify Link
    """
    # 1. Create Material (if not exists)
    mat_data = {
        "name": "Test Composite",
        "type": "NON_DIVISIBLE",
        "base_unit": "carpule",
        "alert_threshold": 5,
    }
    
    # Check if exists first
    resp = client.get("/api/v1/inventory/materials", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    mats = body.get("data", body) if isinstance(body, dict) else body
    mat = next((m for m in mats if m["name"] == "Test Composite"), None)

    if not mat:
        resp = client.post("/api/v1/inventory/materials", json=mat_data, headers=admin_headers)
        assert resp.status_code in [200, 201]
        body = resp.json()
        mat = body.get("data", body) if isinstance(body, dict) and "data" in body else body

    # 2. Create Procedure (if not exists)
    resp = client.get("/api/v1/procedures", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    procs = body.get("data", body) if isinstance(body, dict) and "data" in body else body
    proc = next((p for p in procs if p["name"] == "Test Filling"), None)

    if not proc:
        resp = client.post(
            "/api/v1/procedures",
            json={"name": "Test Filling", "price": 500},
            headers=admin_headers,
        )
        assert resp.status_code in [200, 201]
        body = resp.json()
        proc = body.get("data", body) if isinstance(body, dict) and "data" in body else body

    # 3. Link them (Set Weight)
    weight_data = {
        "procedure_name": "Test Filling",
        "material_id": mat["id"],
        "weight": 2.5,
    }
    w_resp = client.post(
        "/api/v1/inventory/weights", json=weight_data, headers=admin_headers
    )
    assert w_resp.status_code == 200

    # 4. Fetch by Procedure ID
    resp = client.get(
        "/api/v1/inventory/weights",
        params={"procedure_id": proc["id"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    weights = body.get("data", body) if isinstance(body, dict) and "data" in body else body

    found = any(w["material_id"] == mat["id"] and w["weight"] == 2.5 for w in weights)
    assert found, "BOM link not found in response"

