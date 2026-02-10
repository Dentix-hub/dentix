import pytest
from datetime import datetime
from backend.services.patient_service import PatientService
from backend import models

def test_service_fixes(db_session):
    # DEBUG: Check tables
    from sqlalchemy import inspect
    inspector = inspect(db_session.bind)
    print(f"DEBUG: Tables in DB: {inspector.get_table_names()}")
    
    # Setup Tenant and Doctor and Patient
    tenant_id = 1
    
    # Doctor needed for treatment
    doctor = db_session.query(models.User).filter_by(role="doctor").first()
    if not doctor:
        doctor = models.User(username="test_svc_doc", role="doctor", tenant_id=tenant_id, hashed_password="pw")
        db_session.add(doctor)
        db_session.commit()
    
    # Patient
    p = db_session.query(models.Patient).filter(models.Patient.name == "ServiceTest Patient").first()
    if not p:
        p = models.Patient(
            tenant_id=tenant_id, name="ServiceTest Patient", phone="0123456789", age=30
        )
        db_session.add(p)
        db_session.commit()
        
        # Treatment for balance
        t = models.Treatment(
            patient_id=p.id,
            procedure="Test Procedure",
            cost=500.0,
            date=datetime.utcnow(),
            tenant_id=tenant_id,
            doctor_id=doctor.id
        )
        db_session.add(t)
        db_session.commit()
    
    service = PatientService(db_session, tenant_id=tenant_id)
    
    # 1. File Details
    details = service.get_patient_file_details("ServiceTest Patient")
    assert details["found"] is True
    assert details["patient"].name == "ServiceTest Patient"
    
    # 2. Search
    results = service.search_patients_by_name("ServiceTest")
    assert len(results) >= 1
    
    # 3. Balance
    debtors = service.get_patients_with_balance()
    names = [d["name"] for d in debtors]
    assert "ServiceTest Patient" in names
    
    # 4. Summary
    summary = service.get_patient_summary_data("ServiceTest Patient")
    assert summary["found"] is True
    assert "summary_data" in summary
