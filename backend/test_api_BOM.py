import requests

BASE_URL = "http://127.0.0.1:8000"

def test_bom_flow():
    # 1. Login
    resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "password"})
    if resp.status_code != 200:
        print("Login failed")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Material (if not exists)
    mat_data = {"name": "Test Composite", "type": "NON_DIVISIBLE", "base_unit": "carpule", "alert_threshold": 5}
    # Check if exists first ot avoid dup
    mats = requests.get(f"{BASE_URL}/inventory/materials", headers=headers).json()
    mat = next((m for m in mats if m["name"] == "Test Composite"), None)
    
    if not mat:
        mat = requests.post(f"{BASE_URL}/inventory/materials", json=mat_data, headers=headers).json()
        print(f"Created Material: {mat['id']}")
    else:
        print(f"Using Material: {mat['id']}")

    # 3. Create Procedure (if not exists)
    procs = requests.get(f"{BASE_URL}/procedures/", headers=headers).json()
    proc = next((p for p in procs if p["name"] == "Test Filling"), None)
    
    if not proc:
        proc = requests.post(f"{BASE_URL}/procedures/", json={"name": "Test Filling", "price": 500}, headers=headers).json()
        print(f"Created Procedure: {proc['id']}")
    else:
        print(f"Using Procedure: {proc['id']}")

    # 4. Link them (Set Weight)
    weight_data = {
        "procedure_name": "Test Filling",
        "material_id": mat["id"],
        "weight": 2.5
    }
    w_resp = requests.post(f"{BASE_URL}/inventory/weights", json=weight_data, headers=headers)
    print("Set Weight Resp:", w_resp.status_code)
    assert w_resp.status_code == 200

    # 5. Fetch by Procedure ID
    weights = requests.get(f"{BASE_URL}/inventory/weights", params={"procedure_id": proc["id"]}, headers=headers).json()
    print("Fetched Weights:", weights)
    
    found = any(w["material_id"] == mat["id"] and w["weight"] == 2.5 for w in weights)
    if found:
        print("✅ SUCCESS: Procedure BOM found correctly.")
    else:
        print("❌ FAILURE: BOM not found.")

if __name__ == "__main__":
    test_bom_flow()
