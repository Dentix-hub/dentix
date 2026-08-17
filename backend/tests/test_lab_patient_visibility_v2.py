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


def _setup_lab_orders(db_session, test_tenant, test_user, admin_user):
    test_user.patient_visibility_mode = "all_assigned"
    visible = _patient(
        tenant_id=test_tenant.id,
        name="Visible Lab Patient",
        phone="01096666666",
        assigned_doctor_id=test_user.id,
    )
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Lab Patient",
        phone="01097777777",
        assigned_doctor_id=admin_user.id,
    )
    laboratory = models.Laboratory(
        tenant_id=test_tenant.id,
        name="Visibility Test Lab",
        is_active=True,
    )
    db_session.add_all([visible, hidden, laboratory])
    db_session.flush()
    visible_order = models.LabOrder(
        tenant_id=test_tenant.id,
        patient_id=visible.id,
        laboratory_id=laboratory.id,
        doctor_id=test_user.id,
        work_type="Crown",
        status="pending",
    )
    hidden_order = models.LabOrder(
        tenant_id=test_tenant.id,
        patient_id=hidden.id,
        laboratory_id=laboratory.id,
        doctor_id=admin_user.id,
        work_type="Bridge",
        status="pending",
    )
    db_session.add_all([visible_order, hidden_order])
    db_session.commit()
    return visible, hidden, laboratory, visible_order, hidden_order


def test_doctor_lab_order_list_excludes_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    visible, hidden, _, visible_order, hidden_order = _setup_lab_orders(
        db_session, test_tenant, test_user, admin_user
    )
    response = client.get("/api/v1/lab-orders", headers=auth_headers)
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert visible_order.id in ids
    assert hidden_order.id not in ids
    names = [item.get("patient_name") for item in response.json()["data"]]
    assert visible.name in names
    assert hidden.name not in names


def test_doctor_cannot_read_hidden_patient_lab_order_by_id(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    _, _, _, _, hidden_order = _setup_lab_orders(
        db_session, test_tenant, test_user, admin_user
    )
    response = client.get(f"/api/v1/lab-orders/{hidden_order.id}", headers=auth_headers)
    assert response.status_code == 404


def test_doctor_cannot_create_lab_order_for_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    _, hidden, laboratory, _, _ = _setup_lab_orders(
        db_session, test_tenant, test_user, admin_user
    )
    response = client.post(
        "/api/v1/lab-orders",
        json={
            "patient_id": hidden.id,
            "laboratory_id": laboratory.id,
            "work_type": "New hidden order",
            "cost": 0,
            "price_to_patient": 0,
            "status": "pending",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_doctor_patient_lab_orders_endpoint_hides_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    _, hidden, _, _, _ = _setup_lab_orders(
        db_session, test_tenant, test_user, admin_user
    )
    response = client.get(
        f"/api/v1/patients/{hidden.id}/lab_orders",
        headers=auth_headers,
    )
    assert response.status_code == 404
