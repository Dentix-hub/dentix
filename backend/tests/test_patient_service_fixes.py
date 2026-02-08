
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.services.patient_service import PatientService
from backend import models

def test_service_fixes():
    db = SessionLocal()
    try:
        service = PatientService(db, tenant_id=1)
        
        print("🔍 Testing PatientService Repairs...")
        
        # 0. Ensure a dummy patient exists
        p = db.query(models.Patient).filter(models.Patient.name == "ServiceTest Patient").first()
        if not p:
            print("   Creating duplicate/dummy patient for testing...")
            p = models.Patient(
                tenant_id=1,
                name="ServiceTest Patient",
                phone="0123456789",
                age=30
            )
            db.add(p)
            db.flush() # Get ID
            
            # Create treatment to simulate balance
            t = models.Treatment(
                patient_id=p.id,
                procedure="Test Procedure",
                diagnosis="Test Diagnosis",
                cost=500.0,
                date=datetime.utcnow(),
                tenant_id=1
            )
            db.add(t)
            db.commit()
            db.refresh(p)

        # 1. Test get_patient_file_details
        print("\n🔹 Testing get_patient_file_details...")
        try:
            details = service.get_patient_file_details("ServiceTest Patient")
            print(f"   ✅ Success. Result keys: {list(details.keys())}")
            assert details["found"] is True
            assert details["patient"].name == "ServiceTest Patient"
        except AttributeError as e:
            print(f"   ❌ FAILED (AttributeError): {e}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")

        # 2. Test search_patients_by_name
        print("\n🔹 Testing search_patients_by_name...")
        try:
            results = service.search_patients_by_name("ServiceTest")
            print(f"   ✅ Success. Found {len(results)} patients.")
            assert len(results) >= 1
        except AttributeError as e:
            print(f"   ❌ FAILED (AttributeError): {e}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")

        # 3. Test get_patients_with_balance
        print("\n🔹 Testing get_patients_with_balance...")
        try:
            debtors = service.get_patients_with_balance()
            print(f"   ✅ Success. Found {len(debtors)} debtors.")
            # Verify structure
            if debtors:
                print(f"   Sample: {debtors[0]}")
                assert "balance" in debtors[0]
        except AttributeError as e:
            print(f"   ❌ FAILED (AttributeError): {e}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")\

        # 4. Test get_patient_summary_data
        print("\n🔹 Testing get_patient_summary_data...")
        try:
            summary = service.get_patient_summary_data("ServiceTest Patient")
            print(f"   ✅ Success. Result keys: {list(summary.keys())}")
            assert summary["found"] is True
            assert "summary_data" in summary
        except AttributeError as e:
            print(f"   ❌ FAILED (AttributeError): {e}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_service_fixes()
