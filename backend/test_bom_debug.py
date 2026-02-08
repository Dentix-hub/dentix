import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
AUTH = None

def login():
    global AUTH
    resp = requests.post(f"{BASE_URL}/token", data={"username": "eslamemara1312@gmail.com", "password": "ESLAMomara11##"})
    if resp.status_code != 200:
        print("Login Failed:", resp.text)
        return
    token = resp.json()["access_token"]
    AUTH = {"Authorization": f"Bearer {token}"}

def test_bom_flow():
    login()
    if not AUTH: return
    
    # 1. Create/Find Procedure
    resp = requests.get(f"{BASE_URL}/procedures/", headers=AUTH)
    procs = resp.json()
    if isinstance(procs, dict):
        print("Error fetching procedures:", procs)
        return
    proc = next((p for p in procs if p["name"] == "BOM Test Proc"), None)
    if not proc:
        proc = requests.post(f"{BASE_URL}/procedures/", json={"name": "BOM Test Proc", "price": 100}, headers=AUTH).json()
    print(f"Procedure ID: {proc['id']}")

    # 2. Create/Find Material
    mats = requests.get(f"{BASE_URL}/inventory/materials", headers=AUTH).json()
    mat = mats[0] if mats else requests.post(f"{BASE_URL}/inventory/materials", json={"name": "BOM Mat", "type": "NON_DIVISIBLE", "base_unit": "pcs"}, headers=AUTH).json()
    print(f"Material ID: {mat['id']}")

    # 3. Set Weight
    requests.post(f"{BASE_URL}/inventory/weights", json={
        "procedure_name": proc["name"], # API expects name
        "material_id": mat["id"],
        "weight": 5.5
    }, headers=AUTH)
    
    # 4. Fetch Weights (What Frontend does)
    w_resp = requests.get(f"{BASE_URL}/inventory/weights", params={"procedure_id": proc["id"]}, headers=AUTH)
    weights = w_resp.json()
    print("Weights Response:", weights)
    
    found = next((w for w in weights if w["material_id"] == mat["id"]), None)
    if found and found["weight"] == 5.5:
        print("✅ SUCCESS: Backend returns correct weight.")
    else:
        print("❌ FAILURE: Backend did not return expected weight.")

if __name__ == "__main__":
    test_bom_flow()
