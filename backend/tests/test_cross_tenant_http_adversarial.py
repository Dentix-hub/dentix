"""Phase 6 BOLA/IDOR adversarial HTTP matrix.

Creates real Tenant-A and Tenant-B records, authenticates only as Tenant A, then
substitutes Tenant-B object IDs into sensitive HTTP routes. Cross-tenant objects
must be indistinguishable from missing objects and must never appear in A lists.
"""

import uuid
from datetime import datetime, timedelta

from backend import models
from backend.auth import get_password_hash


def _response_ids(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("success") is True
    return {item["id"] for item in body.get("data", [])}


def _create_tenant_b_graph(db_session):
    suffix = uuid.uuid4().hex[:8]
    tenant_b = models.Tenant(name=f"Adversarial Tenant B {suffix}", is_active=True)
    db_session.add(tenant_b)
    db_session.flush()

    doctor_b = models.User(
        username=f"tenant_b_doctor_{suffix}",
        email=f"tenant-b-{suffix}@example.com",
        full_name="Tenant B Doctor",
        role="doctor",
        tenant_id=tenant_b.id,
        is_active=True,
        hashed_password=get_password_hash("ValidPass9!TenantB"),
    )
    db_session.add(doctor_b)
    db_session.flush()

    patient_b = models.Patient(
        name="Tenant B Patient",
        age=41,
        phone=f"0108{suffix[:7]}",
        email=None,
        medical_history="",
        notes="tenant-b-private",
        tenant_id=tenant_b.id,
        assigned_doctor_id=doctor_b.id,
        is_deleted=False,
    )
    db_session.add(patient_b)
    db_session.flush()

    appointment_b = models.Appointment(
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        date_time=datetime.utcnow() + timedelta(days=7),
        status="Scheduled",
        notes="tenant-b-private",
        tenant_id=tenant_b.id,
        is_deleted=False,
    )
    treatment_b = models.Treatment(
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        tooth_number=11,
        diagnosis="Private",
        procedure="Tenant B Procedure",
        cost=500,
        discount=0,
        status="Done",
        tenant_id=tenant_b.id,
        is_deleted=False,
    )
    payment_b = models.Payment(
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        amount=250,
        notes="tenant-b-private",
        tenant_id=tenant_b.id,
    )
    attachment_b = models.Attachment(
        tenant_id=tenant_b.id,
        patient_id=patient_b.id,
        file_path=f"tenant_{tenant_b.id}/private-{suffix}.txt",
        filename=f"private-{suffix}.txt",
        file_type="text/plain",
    )
    db_session.add_all([appointment_b, treatment_b, payment_b, attachment_b])
    db_session.commit()

    for obj in [tenant_b, doctor_b, patient_b, appointment_b, treatment_b, payment_b, attachment_b]:
        db_session.refresh(obj)

    return {
        "tenant": tenant_b,
        "doctor": doctor_b,
        "patient": patient_b,
        "appointment": appointment_b,
        "treatment": treatment_b,
        "payment": payment_b,
        "attachment": attachment_b,
    }


def _create_tenant_a_patient(db_session, test_tenant, test_user):
    suffix = uuid.uuid4().hex[:8]
    patient = models.Patient(
        name="Tenant A Control Patient",
        age=30,
        phone=f"0107{suffix[:7]}",
        email=None,
        medical_history="",
        notes="tenant-a-control",
        tenant_id=test_tenant.id,
        assigned_doctor_id=test_user.id,
        is_deleted=False,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def _create_tenant_a_controls(db_session, test_tenant, test_user, patient_a):
    appointment_a = models.Appointment(
        patient_id=patient_a.id,
        doctor_id=test_user.id,
        date_time=datetime.utcnow() + timedelta(days=3),
        status="Scheduled",
        notes="tenant-a-control",
        tenant_id=test_tenant.id,
        is_deleted=False,
    )
    payment_a = models.Payment(
        patient_id=patient_a.id,
        doctor_id=test_user.id,
        amount=100,
        notes="tenant-a-control",
        tenant_id=test_tenant.id,
    )
    db_session.add_all([appointment_a, payment_a])
    db_session.commit()
    db_session.refresh(appointment_a)
    db_session.refresh(payment_a)
    return appointment_a, payment_a


def test_tenant_a_cannot_read_or_mutate_tenant_b_patient_resources(
    client,
    db_session,
    test_tenant,
    test_user,
    admin_headers,
):
    graph_b = _create_tenant_b_graph(db_session)
    patient_a = _create_tenant_a_patient(db_session, test_tenant, test_user)
    appointment_a, payment_a = _create_tenant_a_controls(
        db_session, test_tenant, test_user, patient_a
    )
    patient_b = graph_b["patient"]

    patient_list = client.get("/api/v1/patients", headers=admin_headers)
    patient_ids = _response_ids(patient_list)
    assert patient_a.id in patient_ids
    assert patient_b.id not in patient_ids

    assert client.get(
        f"/api/v1/patients/{patient_b.id}", headers=admin_headers
    ).status_code == 404
    assert client.put(
        f"/api/v1/patients/{patient_b.id}",
        json={"notes": "tenant-a-tamper"},
        headers=admin_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/patients/{patient_b.id}", headers=admin_headers
    ).status_code == 404

    for suffix in ["treatments", "payments", "attachments", "prescriptions", "tooth_status"]:
        response = client.get(
            f"/api/v1/patients/{patient_b.id}/{suffix}", headers=admin_headers
        )
        assert response.status_code == 404, (suffix, response.status_code, response.text)

    appointment_list = client.get("/api/v1/appointments", headers=admin_headers)
    appointment_ids = _response_ids(appointment_list)
    assert appointment_a.id in appointment_ids
    assert graph_b["appointment"].id not in appointment_ids

    assert client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_b.id,
            "doctor_id": test_user.id,
            "date_time": (datetime.utcnow() + timedelta(days=10)).isoformat(),
            "status": "Scheduled",
        },
        headers=admin_headers,
    ).status_code == 404
    assert client.put(
        f"/api/v1/appointments/{graph_b['appointment'].id}",
        json={"notes": "tenant-a-tamper"},
        headers=admin_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/appointments/{graph_b['appointment'].id}", headers=admin_headers
    ).status_code == 404

    assert client.post(
        "/api/v1/treatments",
        json={
            "patient_id": patient_b.id,
            "tooth_number": 12,
            "procedure": "Cross Tenant Attempt",
            "cost": 100,
            "discount": 0,
            "skip_stock_check": True,
        },
        headers=admin_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/treatments/{graph_b['treatment'].id}", headers=admin_headers
    ).status_code == 404

    payment_list = client.get("/api/v1/payments", headers=admin_headers)
    payment_ids = _response_ids(payment_list)
    assert payment_a.id in payment_ids
    assert graph_b["payment"].id not in payment_ids

    assert client.post(
        "/api/v1/payments",
        json={"patient_id": patient_b.id, "amount": 75},
        headers=admin_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/payments/{graph_b['payment'].id}", headers=admin_headers
    ).status_code == 404

    file_response = client.get(
        f"/api/v1/upload/file/{graph_b['attachment'].file_path}",
        headers=admin_headers,
    )
    assert file_response.status_code == 404


def test_tenant_a_cannot_manage_or_discover_tenant_b_doctor(
    client,
    db_session,
    test_user,
    admin_headers,
):
    graph_b = _create_tenant_b_graph(db_session)
    doctor_b = graph_b["doctor"]

    doctors = client.get("/api/v1/users/doctors", headers=admin_headers)
    doctor_ids = _response_ids(doctors)
    assert test_user.id in doctor_ids
    assert doctor_b.id not in doctor_ids

    users = client.get("/api/v1/users", headers=admin_headers)
    user_ids = _response_ids(users)
    assert doctor_b.id not in user_ids

    update = client.put(
        f"/api/v1/users/{doctor_b.id}",
        json={"full_name": "Tenant A Tamper"},
        headers=admin_headers,
    )
    assert update.status_code == 404

    delete = client.delete(
        f"/api/v1/users/{doctor_b.id}", headers=admin_headers
    )
    assert delete.status_code == 404
