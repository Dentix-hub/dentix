from datetime import datetime, time

from backend import models
from backend.utils.patient_search_normalization import (
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)
from backend.utils.tenant_time import tenant_local_date


def _patient(*, tenant_id, name, phone, age=30, assigned_doctor_id=None):
    return models.Patient(
        tenant_id=tenant_id,
        name=name,
        name_search_normalized=normalize_patient_name_for_search(name),
        phone=phone,
        phone_search_hash=patient_phone_search_hash(phone),
        age=age,
        medical_history="",
        notes="",
        assigned_doctor_id=assigned_doctor_id,
    )


def test_directory_search_finds_patient_beyond_legacy_first_100(
    client, db_session, test_tenant, admin_user, admin_headers,
):
    patients = [
        _patient(
            tenant_id=test_tenant.id,
            name=f"مريض تجريبي {index}",
            phone=f"01012{index:06d}",
            assigned_doctor_id=admin_user.id,
        )
        for index in range(125)
    ]
    target = _patient(
        tenant_id=test_tenant.id,
        name="أحمد خارج أول مائة",
        phone="01198765432",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add_all(patients + [target])
    db_session.commit()
    response = client.get(
        "/api/v1/patients/directory",
        params={"q": "احمد خارج اول مائة", "limit": 30},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [target.id]


def test_directory_file_number_search_is_exact(
    client, db_session, test_tenant, admin_user, admin_headers,
):
    patient = _patient(
        tenant_id=test_tenant.id,
        name="File Number Patient",
        phone="01212345678",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    response = client.get(
        "/api/v1/patients/directory",
        params={"q": f"#{patient.id}"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == patient.id
    assert response.json()["data"][0]["file_number"] == patient.id


def test_directory_phone_search_normalizes_egypt_formats(
    client, db_session, test_tenant, admin_user, admin_headers,
):
    patient = _patient(
        tenant_id=test_tenant.id,
        name="Phone Patient",
        phone="01012345678",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    for query in ("01012345678", "+201012345678", "٠١٠١٢٣٤٥٦٧٨"):
        response = client.get(
            "/api/v1/patients/directory",
            params={"q": query},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["data"]] == [patient.id]


def test_today_scope_uses_tenant_local_appointment_day(
    client, db_session, test_tenant, admin_user, admin_headers,
):
    today_patient = _patient(
        tenant_id=test_tenant.id,
        name="Today Patient",
        phone="01066666666",
        assigned_doctor_id=admin_user.id,
    )
    other_patient = _patient(
        tenant_id=test_tenant.id,
        name="Not Today Patient",
        phone="01077777777",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add_all([today_patient, other_patient])
    db_session.flush()
    local_today = tenant_local_date(test_tenant.timezone)
    db_session.add(
        models.Appointment(
            tenant_id=test_tenant.id,
            patient_id=today_patient.id,
            doctor_id=admin_user.id,
            date_time=datetime.combine(local_today, time(hour=12)),
            status="Scheduled",
            is_deleted=False,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/patients/directory",
        params={"scope": "today"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert today_patient.id in ids
    assert other_patient.id not in ids


def test_recent_directory_preserves_order_and_revalidates_visibility(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    first = _patient(
        tenant_id=test_tenant.id,
        name="Recent First",
        phone="01081111111",
        assigned_doctor_id=test_user.id,
    )
    second = _patient(
        tenant_id=test_tenant.id,
        name="Recent Second",
        phone="01082222222",
        assigned_doctor_id=test_user.id,
    )
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Recent Hidden",
        phone="01083333333",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add_all([first, second, hidden])
    db_session.commit()

    response = client.get(
        "/api/v1/patients/directory/recent",
        params={"ids": f"{second.id},{hidden.id},{first.id}"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [second.id, first.id]


def test_doctor_mine_scope_is_assignment_based(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "mixed"
    mine = _patient(
        tenant_id=test_tenant.id,
        name="Mine Patient",
        phone="01084444444",
        assigned_doctor_id=test_user.id,
    )
    not_mine = _patient(
        tenant_id=test_tenant.id,
        name="Appointment Only Patient",
        phone="01085555555",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add_all([mine, not_mine])
    db_session.flush()
    local_today = tenant_local_date(test_tenant.timezone)
    db_session.add(
        models.Appointment(
            tenant_id=test_tenant.id,
            patient_id=not_mine.id,
            doctor_id=test_user.id,
            date_time=datetime.combine(local_today, time(hour=14)),
            status="Scheduled",
            is_deleted=False,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/patients/directory",
        params={"scope": "mine"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [mine.id]


def test_doctor_directory_does_not_leak_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    visible = _patient(
        tenant_id=test_tenant.id,
        name="Visible Doctor Patient",
        phone="01033333333",
        assigned_doctor_id=test_user.id,
    )
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Doctor Patient",
        phone="01044444444",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add_all([visible, hidden])
    db_session.commit()
    visible_response = client.get(
        "/api/v1/patients/directory",
        params={"q": "Visible Doctor Patient"},
        headers=auth_headers,
    )
    hidden_response = client.get(
        "/api/v1/patients/directory",
        params={"q": "Hidden Doctor Patient"},
        headers=auth_headers,
    )
    assert visible_response.status_code == 200
    assert [item["id"] for item in visible_response.json()["data"]] == [visible.id]
    assert hidden_response.status_code == 200
    assert hidden_response.json()["data"] == []


def test_doctor_cannot_update_hidden_patient(
    client, db_session, test_tenant, test_user, auth_headers, admin_user,
):
    test_user.patient_visibility_mode = "all_assigned"
    hidden = _patient(
        tenant_id=test_tenant.id,
        name="Hidden Update Patient",
        phone="01055555555",
        assigned_doctor_id=admin_user.id,
    )
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)
    response = client.put(
        f"/api/v1/patients/{hidden.id}",
        json={"name": "Should Not Change"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    db_session.refresh(hidden)
    assert hidden.name == "Hidden Update Patient"
