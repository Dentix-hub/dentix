"""Regression tests for tenant-scoped prescription print DTO (HIGH-06)."""

import json

import pytest

from backend import models


@pytest.fixture
def rx_patient(db_session, test_tenant, test_user):
    patient = models.Patient(
        name="Rx Patient",
        phone="01234567890",
        age=30,
        medical_history="",
        notes="",
        tenant_id=test_tenant.id,
        assigned_doctor_id=test_user.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def rx_prescription(db_session, rx_patient):
    prescription = models.Prescription(
        patient_id=rx_patient.id,
        medications=json.dumps([{"name": "Amoxicillin", "dose": "500mg"}]),
        notes="مرتين يومياً",
    )
    db_session.add(prescription)
    db_session.commit()
    db_session.refresh(prescription)
    return prescription


def test_prescription_print_returns_server_dto(
    client, admin_headers, db_session, test_tenant, rx_prescription, rx_patient
):
    response = client.get(
        f"/api/v1/prescriptions/{rx_prescription.id}/print", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["prescription"]["id"] == rx_prescription.id
    assert json.loads(data["prescription"]["medications"])[0]["name"] == "Amoxicillin"
    assert data["patient"]["id"] == rx_patient.id
    assert data["patient"]["name"] == "Rx Patient"
    # Clinic identity must come from the tenant, not hardcoded strings.
    assert data["clinic"]["doctor_name"] == test_tenant.doctor_name or data["clinic"]["doctor_name"] is None


def test_prescription_print_blocks_cross_tenant_access(
    client, admin_headers, db_session
):
    other_tenant = models.Tenant(name="Foreign Clinic", is_active=True)
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    foreign_patient = models.Patient(
        name="Foreign Rx Patient",
        phone="01111111111",
        age=28,
        medical_history="",
        notes="",
        tenant_id=other_tenant.id,
    )
    db_session.add(foreign_patient)
    db_session.commit()
    db_session.refresh(foreign_patient)

    foreign_rx = models.Prescription(
        patient_id=foreign_patient.id,
        medications=json.dumps([{"name": "Secret Med", "dose": "1mg"}]),
        notes="private",
    )
    db_session.add(foreign_rx)
    db_session.commit()
    db_session.refresh(foreign_rx)

    response = client.get(
        f"/api/v1/prescriptions/{foreign_rx.id}/print", headers=admin_headers
    )
    assert response.status_code == 404
