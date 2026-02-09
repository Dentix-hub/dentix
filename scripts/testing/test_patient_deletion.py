import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import requests
import json
import sys
import random

API_URL = "http://127.0.0.1:8000/api/v1"

def register_clinic():
    # Create unique clinic info
    suffix = random.randint(1000, 9999)
    admin_data = {
        "clinic_name": f"Test Clinic {suffix}",
        "admin_username": f"admin{suffix}",
        "admin_email": f"admin{suffix}@test.com",
        "admin_password": "password123"
    }
    print(f"Registering Clinic: {admin_data['clinic_name']}...")
    try:
        r = requests.post(f"{API_URL}/auth/register_clinic", data=admin_data)
        if r.status_code == 200:
            return r.json()["access_token"]
        print(f"Registration Failed: {r.text}")
    except Exception as e:
        print(f"Registration Error: {e}")
    return None

def test_deletion_cleanup():
    print("--- Testing Patient Deletion Financial Cleanup ---")
    
    # 1. Register & Login as Clinic Admin
    token = register_clinic()
    if not token: 
        print("Aborting: Could not obtain token.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        # 2. Create Patient
        p_data = {"name": "Test Delete Financial", "phone": "01000000000", "age": 30}
        r = requests.post(f"{API_URL}/patients/", json=p_data, headers=headers)
        if r.status_code != 200:
            print(f"Create Patient Failed: {r.text}")
            return
        patient = r.json()
        pid = patient['id']
        print(f"2. Created Patient: {patient['name']} (ID: {pid})")

        # 3. Add Treatment (Create Debt)
        # We need a valid procedure. Let's create one or find one.
        # Actually better to create one to be safe.
        proc_data = {
            "name": "Test Extraction",
            "cost": 100.0,
            "category": "Surgery",
            "duration_minutes": 30
        }
        # Assuming we have an endpoint for creating procedures, checking routes...
        # If not, we use existing logic to fetch.
        # Let's try fetching first.
        r = requests.get(f"{API_URL}/settings/procedures", headers=headers)
        if r.status_code == 200 and r.json():
            proc_id = r.json()[0]['id']
        else:
             # Fallback or create? 
             # Let's try to assume seeded data or create if possible. 
             # If new clinic, it might mean NO procedures?
             # Usually registration seeds default procedures? If not, we might fail here.
             # Let's hope for the best or add procedure creation if needed.
             print("Warning: No procedures found. Debt creation might fail.")
             proc_id = 1
        
        t_data = {
            "patient_id": pid,
            "procedure_id": proc_id,
            "cost": 100.0,
            "date": "2026-02-03" # Today
        }
        r = requests.post(f"{API_URL}/treatments/", json=t_data, headers=headers)
             
        if r.status_code != 200:
            print(f"Create Treatment Failed: {r.text}")
            return
        print(f"3. Added Treatment: Cost 100.0 (Debt Created)")

        # 4. Verify Debt Exists
        r = requests.get(f"{API_URL}/payments/today/debtors", headers=headers)
        if(r.status_code != 200):
             print(f"Get Debtors Failed: {r.text}")
             return
             
        debtors = r.json()
        in_debt = any(d['id'] == pid for d in debtors)
        print(f"4. Verify Debt Before Delete: {'FOUND' if in_debt else 'NOT FOUND'}")
        if not in_debt:
            print("Test Inconclusive: Debt not showing up initially.")
            # Debug: print debtors
            print(f"Debtors List: {json.dumps(debtors, indent=2)}")
            return

        # 5. Delete Patient
        r = requests.delete(f"{API_URL}/patients/{pid}", headers=headers)
        print(f"5. Deleted Patient: {r.status_code}")

        # 6. Verify Debt Gone
        r = requests.get(f"{API_URL}/payments/today/debtors", headers=headers)
        debtors = r.json()
        in_debt_after = any(d['id'] == pid for d in debtors)
        
        if in_debt_after:
             print("FAILURE: Patient still in debtors list.")
        else:
             print("SUCCESS: Patient removed from debtors list.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_deletion_cleanup()
