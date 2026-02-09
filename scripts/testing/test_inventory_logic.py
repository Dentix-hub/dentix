import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import requests
import sys

API_URL = "http://127.0.0.1:8000/api/v1"
TENANT_ID = 1

def login():
    print("Logging in...")
    # Try Super Admin credentials (from seeding.py)
    creds = {"username": "eslamemara1312@gmail.com", "password": "ESLAMomara11##"}
    try:
        r = requests.post(f"{API_URL}/token", data=creds)
        if r.status_code == 200:
            return r.json()["access_token"]
        else:
             print(f"Login Failed: {r.status_code} {r.text}")
             # Backup: Legacy Admin (if enabled in other seeds)
             creds = {"username": "admin", "password": "password"}
             r = requests.post(f"{API_URL}/token", data=creds)
             if r.status_code == 200:
                print("Logged in with 'admin'")
                return r.json()["access_token"]
    except Exception as e:
        print(f"Login Error: {e}")
    return None

def test_inventory_logic():
    print("--- Testing Inventory Logic ---")
    
    token = login()
    if not token:
        print("Creating Admin if missing...")
        # Try manual seed if needed, but assuming admin exists from startup
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        # 1. Create Materials
        print("\n1. Creating Materials...")
        
        # Non-Divisible (e.g. Bur)
        mat_nd_data = {
            "name": "Test Bur (ND)",
            "type": "NON_DIVISIBLE",
            "base_unit": "pcs",
            "packaging_ratio": 1.0,
            "alert_threshold": 5
        }
        r = requests.post(f"{API_URL}/inventory/materials?tenant_id={TENANT_ID}", json=mat_nd_data, headers=headers, timeout=5)
        print(f"Create ND Material: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
            return
        mat_nd = r.json()
        
        # Divisible (e.g. Bond)
        mat_d_data = {
            "name": "Test Bond (D)",
            "type": "DIVISIBLE",
            "base_unit": "ml",
            "packaging_ratio": 5.0, # 5ml bottle
            "alert_threshold": 2
        }
        r = requests.post(f"{API_URL}/inventory/materials?tenant_id={TENANT_ID}", json=mat_d_data, headers=headers, timeout=5)
        print(f"Create Div Material: {r.status_code}")
        mat_d = r.json()

        # 2. Add Stock (Main Warehouse)
        print("\n2. Adding Stock...")
        
        # Determine Warehouses
        r = requests.get(f"{API_URL}/inventory/warehouses?tenant_id={TENANT_ID}", headers=headers, timeout=5)
        warehouses = r.json()
        clinic_wh = next((w for w in warehouses if w['type'] == 'CLINIC'), None)
        if not clinic_wh:
            print("Creating Clinic Warehouse...")
            r = requests.post(f"{API_URL}/inventory/warehouses?tenant_id={TENANT_ID}", json={"name": "Clinic", "type": "CLINIC"}, headers=headers, timeout=5)
            clinic_wh = r.json()
        wh_clinic_id = clinic_wh['id']
        
        main_wh = next((w for w in warehouses if w['type'] == 'MAIN'), None)
        if not main_wh:
             wh_main_id = warehouses[0]['id'] if warehouses else 1
        else:
             wh_main_id = main_wh['id']

        print(f"Main WH: {wh_main_id}, Clinic WH: {wh_clinic_id}")
        
        # Add Stock to MAIN
        batch_nd = {
            "batch_number": "B-ND-TRANS-01",
            "expiry_date": "2026-12-31",
            "cost_per_unit": 10.0,
            "supplier": "Test Supplier"
        }
        r = requests.post(f"{API_URL}/inventory/receive", json={
            "material_id": mat_nd['id'],
            "warehouse_id": wh_main_id,
            "quantity": 10,
            "batch": batch_nd
        }, headers=headers, timeout=5)
        print(f"Add Stock ND to MAIN: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
            return
        stock_item = r.json()
        
        # 3. Test Transfer (Main -> Clinic)
        print("\n3. Testing Transfer (Main -> Clinic)...")
        transfer_qty = 5.0
        r = requests.post(f"{API_URL}/inventory/transfer", json={
            "stock_item_id": stock_item['id'],
            "target_warehouse_id": wh_clinic_id,
            "quantity": transfer_qty
        }, headers=headers, timeout=5)
        print(f"Transfer Stock: {r.status_code}")
        if r.status_code != 200:
             print(r.text)
        else:
             print("Transfer Success")

        # 4. Verify Material Update
        print("\n4. Verifying Material Update...")
        update_data = {"packaging_ratio": 2.5}
        r = requests.put(f"{API_URL}/inventory/materials/{mat_d['id']}?tenant_id={TENANT_ID}", json=update_data, headers=headers, timeout=5)
        print(f"Update Material Ratio: {r.status_code}")
        updated_mat = r.json()
        print(f"New Ratio: {updated_mat['packaging_ratio']}")
        assert updated_mat['packaging_ratio'] == 2.5

        print("\n--- Test Complete ---")

    except requests.exceptions.RequestException as e:
        print(f"\nRequest Failed: {e}")
        # If API is down, maybe port or path is wrong.
        print("Tip: Check if backend is running on 8000 and URL prefix is correct.")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")

if __name__ == "__main__":
    test_inventory_logic()
