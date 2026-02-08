import requests
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SQLALCHEMY_DATABASE_URL
from backend.models import clinical as clinical_models
from backend.models import inventory as inv_models
from backend.models import tenant as tenant_models

# Setup DB
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

BASE_URL = "http://127.0.0.1:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/token"

def get_token():
    payload = {
        "username": "eslamemara1312@gmail.com",
        "password": "ESLAMomara11##"
    }
    resp = requests.post(LOGIN_URL, data=payload)
    if resp.status_code != 200:
        print("Login Failed:", resp.text)
        sys.exit(1)
    return resp.json()["access_token"]

def run_test():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("1. Authenticated.")
    
    # 2. Create Material
    mat_payload = {
        "name": "Smart Composite X",
        "type": "DIVISIBLE",
        "base_unit": "g"
    }
    resp = requests.post(f"{BASE_URL}/inventory/materials", json=mat_payload, headers=headers)
    if resp.status_code != 200:
        # Maybe exists
        print("Material creation/check:", resp.status_code)
    material_data = resp.json() if resp.status_code==200 else \
        requests.get(f"{BASE_URL}/inventory/materials", headers=headers).json()[-1]
    material_id = material_data["id"]
    print(f"2. Material ID: {material_id}")

    # 3. Create Procedure (Simulate via DB)
    proc = db.query(clinical_models.Procedure).filter_by(name="Test Class I").first()
    if not proc:
        proc = clinical_models.Procedure(name="Test Class I", price=100.0, tenant_id=1)
        db.add(proc)
        db.commit()
    print(f"3. Procedure ID: {proc.id}")
    
    # 4. Set Weight
    weight_payload = {
        "procedure_name": "Test Class I",
        "material_id": material_id,
        "weight": 1.5
    }
    resp = requests.post(f"{BASE_URL}/inventory/weights", json=weight_payload, headers=headers)
    print(f"4. Set Weight: {resp.status_code} -> {resp.json()}")

    # 5. Create Batch & StockItem (Need this for Session)
    # Using 'receive' endpoint
    wh_resp = requests.get(f"{BASE_URL}/inventory/warehouses", headers=headers)
    warehouses = wh_resp.json()
    if not warehouses:
        print("Creating Missing Warehouse...")
        wh_payload = {"name": "Main Supply", "type": "MAIN"}
        create_wh_resp = requests.post(f"{BASE_URL}/inventory/warehouses", json=wh_payload, headers=headers)
        if create_wh_resp.status_code != 200:
            print("Failed to create warehouse:", create_wh_resp.text)
            sys.exit(1)
        wh_id = create_wh_resp.json()["id"]
    else:
        wh_id = warehouses[0]["id"]
    
    rec_payload = {
        "material_id": material_id,
        "warehouse_id": wh_id,
        "quantity": 10,
        "batch": {
            "batch_number": "B100",
            "expiry_date": "2026-12-31"
        }
    }
    requests.post(f"{BASE_URL}/inventory/receive", json=rec_payload, headers=headers)
    
    # Get Stock Item ID
    stock_resp = requests.get(f"{BASE_URL}/inventory/stock", headers=headers)
    # This gives summary. Need raw stock item?
    # Actually, receiving creates stock item.
    # Let's direct query DB for stock item
    stock_item = db.query(inv_models.StockItem).filter_by(warehouse_id=wh_id).order_by(inv_models.StockItem.id.desc()).first()
    print(f"5. Stock Item ID: {stock_item.id}")

    # 6. Open Session
    sess_payload = {
        "stock_item_id": stock_item.id
    }
    resp = requests.post(f"{BASE_URL}/inventory/sessions", json=sess_payload, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to open session: {resp.status_code} -> {resp.text}")
        sys.exit(1)
    session_id = resp.json()["id"]
    print(f"6. Open Session ID: {session_id}")
    
    # 7. Simulate Treatments (DB)
    # Create 2 treatments used "Test Class I"
    t1 = clinical_models.Treatment(
        patient_id=1, doctor_id=1, tenant_id=1,
        procedure="Test Class I",
        date=datetime.utcnow()
    )
    t2 = clinical_models.Treatment(
        patient_id=1, doctor_id=1, tenant_id=1,
        procedure="Test Class I",
        date=datetime.utcnow()
    )
    db.add(t1); db.add(t2)
    db.commit()
    print("7. Simulated Treatments")

    # 8. Close Session
    close_payload = {
        "total_consumed": 3.0 # 2 treatments, total 3.0g. Expect 1.5g per treatment (matches weight 1.5)
    }
    resp = requests.post(f"{BASE_URL}/inventory/sessions/{session_id}/close", json=close_payload, headers=headers)
    print(f"8. Close Session: {resp.status_code} -> {resp.json()}")
    
    # 9. Verify Learning
    weight_check = requests.post(f"{BASE_URL}/inventory/weights", json=weight_payload, headers=headers).json()
    print(f"9. Updated Average Usage: {weight_check.get('current_average_usage')}")
    
    if weight_check.get('current_average_usage') > 0:
        print("SUCCESS: System learned usage!")
    else:
        print("FAILURE: System did not learn.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Error: {e}")
