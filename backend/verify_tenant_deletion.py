import sys
import os

# Ensure backend can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Handle potential import errors if dependencies are missing in env
# Handle potential import errors if dependencies are missing in env
# STRICT PRODUCTION CHECK
if "DATABASE_URL" not in os.environ:
    print("CRITICAL: DATABASE_URL not set. Cannot run verification.")
    sys.exit(1)

try:
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.database import SessionLocal
    from backend import models
    from backend.routers.admin import require_super_admin
    from datetime import datetime
except ImportError as e:
    print(f"Import Error: {e}")
    print("Ensure all requirements are installed.")
    sys.exit(1)

# Setup
client = TestClient(app)
db = SessionLocal()

def verify():
    # 1. Create Data
    print("Creating test tenant...")
    tenant = models.Tenant(name=f"DelTest_{int(datetime.now().timestamp())}", subscription_status="active", plan="trial")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    print(f"Created Tenant: {tenant.id}")

    print("Creating dependencies...")
    try:
        # Patient
        patient = models.Patient(name="Test Patient", tenant_id=tenant.id, age=30, phone="123", medical_history="None", notes="None")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        # Appointment
        appt = models.Appointment(patient_id=patient.id, date_time=datetime.now(), status="Scheduled")
        db.add(appt)
        
        # Log
        log = models.AuditLog(action="test_creation", entity_type="tenant", tenant_id=tenant.id, performed_by_username="tester")
        db.add(log)
        
        # Expense (Financial)
        expense = models.Expense(item_name="Test Expense", cost=100.0, category="Test", date=datetime.now(), tenant_id=tenant.id)
        db.add(expense)

        db.commit()
        print("Dependencies created.")
    except Exception as e:
        print(f"Error creating dependencies: {e}")
        db.rollback()
        return

    # 2. Mock Auth
    superuser = models.User(username="superuser", role="super_admin", id=99999, is_active=True)
    app.dependency_overrides[require_super_admin] = lambda: superuser

    # 3. Execute Delete
    print(f"Deleting Tenant {tenant.id} permanently...")
    try:
        response = client.delete(f"/admin/tenants/{tenant.id}/permanent")
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        # 4. Verification
        if response.status_code == 200:
            # Re-query
            db.expire_all() 
            t_check = db.query(models.Tenant).filter(models.Tenant.id == tenant.id).first()
            p_check = db.query(models.Patient).filter(models.Patient.id == patient.id).first()
            e_check = db.query(models.Expense).filter(models.Expense.id == expense.id).first()
            
            if not t_check and not p_check and not e_check:
                print("SUCCESS: Tenant and all dependencies deleted.")
            else:
                print("FAILURE: Some data remains.")
                if t_check: print("  - Tenant still exists")
                if p_check: print("  - Patient still exists")
                if e_check: print("  - Expense still exists")
        else:
            print("FAILURE: API returned error.")
    except Exception as e:
        print(f"Execution Error: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    verify()
