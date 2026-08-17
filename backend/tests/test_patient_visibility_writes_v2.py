from backend import models
from backend.utils.patient_search_normalization import (
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)


def _patient(*, tenant_id, name, phone, assigned_doctor_id):
    return models.Patient(
        tenant_id=tenant_id,
        name=name,
        name_search_normalized=normalize_patient_name_for_search(name),
        phone=phone,
        phone_search_hash=patient_phone_search_hash(phone),
        age=30,
        medical_history="",
        notes="",
        assigned_doctor_id=assigned_doctor_id,
    )


def test_doctor_cannot_create_treatment_for_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Treatment Patient",
        phone="01091111111",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)

    response = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": hidden.id,
            "tooth_number": 11,
            "procedure": "Visibility Test",
            "cost": 100,
            "discount": 0,
            "skip_stock_check": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert (
        db_session.query(models.Treatment)
        .filter(models.Treatment.patient_id == hidden.id)
        .count()
        == 0
    )


def test_doctor_can_create_treatment_for_visible_patient(
    client, db_session, test_tenant, test_user, auth_headers,
):
    test_user.patient_visibility_mode = "all_assigned"
    visible = _patient(
        tenant_id=test_tenant.id,
        name="Visible Treatment Patient",
        phone="01092222222",
        assigned_doctor_id=test_user.id,
    )
    db_session.add(visible)
    db_session.commit()
    db_session.refresh(visible)

    response = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": visible.id,
            "tooth_number": 12,
            "procedure": "Visibility Test",
            "cost": 100,
            "discount": 0,
            "skip_stock_check": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["patient_id"] == visible.id


def test_doctor_cannot_update_hidden_patient_tooth_status(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Tooth Patient",
        phone="01093333333",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)

    response = client.post(
        "/api/v1/treatments/tooth_status",
        json={
            "patient_id": hidden.id,
            "tooth_number": 21,
            "condition": "Caries",
            "notes": "Must not be written",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_doctor_cannot_create_prescription_for_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Prescription Patient",
        phone="01094444444",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)

    response = client.post(
        "/api/v1/prescriptions",
        json={
            "patient_id": hidden.id,
            "medications": "Do not create",
            "notes": "visibility test",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_doctor_cannot_delete_hidden_patient_treatment(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Delete Treatment Patient",
        phone="01095555555",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(hidden)
    db_session.flush()
    treatment = models.Treatment(
        tenant_id=test_tenant.id,
        patient_id=hidden.id,
        doctor_id=admin_user.id,
        procedure="Existing Hidden Treatment",
        cost=100,
        discount=0,
        status="Done",
    )
    db_session.add(treatment)
    db_session.commit()
    db_session.refresh(treatment)

    response = client.delete(
        f"/api/v1/treatments/{treatment.id}",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert db_session.get(models.Treatment, treatment.id) is not None
