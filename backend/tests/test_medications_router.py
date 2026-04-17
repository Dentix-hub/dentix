import pytest
from backend.models import SavedMedication

def test_get_saved_medications(client, super_admin_headers, db_session):
    # Seed a medication
    med = SavedMedication(name="Panadol", dosage="500mg", frequency="3 times daily", tenant_id=1)
    db_session.add(med)
    db_session.commit()
    
    response = client.get("/api/v1/medications/saved", headers=super_admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert any(m["name"] == "Panadol" for m in data)

def test_create_saved_medication(client, super_admin_headers, db_session):
    payload = {
        "name": "Amoxicillin",
        "dosage": "250mg",
        "frequency": "Every 8 hours"
    }
    response = client.post("/api/v1/medications/saved", json=payload, headers=super_admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Amoxicillin"
    
    # Verify DB
    db_med = db_session.query(SavedMedication).filter(SavedMedication.id == data["id"]).first()
    assert db_med is not None
    assert db_med.dosage == "250mg"

def test_delete_saved_medication(client, super_admin_headers, db_session):
    med = SavedMedication(name="To Delete", tenant_id=1)
    db_session.add(med)
    db_session.commit()
    
    response = client.delete(f"/api/v1/medications/saved/{med.id}", headers=super_admin_headers)
    assert response.status_code == 200
    
    # Verify DB (hard delete in router line 68)
    db_med = db_session.query(SavedMedication).filter(SavedMedication.id == med.id).first()
    assert db_med is None
