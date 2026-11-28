"""Regression tests for demo clinic hotfix bugs (appointment In-Chair status & linked lab orders)."""

from decimal import Decimal
import pytest

from backend import models
from backend.clinical.lab_links import matching_procedure


@pytest.mark.parametrize("raw_status", ["In-Chair", "in-chair", "in chair", "in_chair"])
def test_appointment_accepts_in_chair_status_across_endpoints(
    client, test_patient, admin_headers, raw_status
):
    """Bug 2: Changing or creating appointments with In-Chair status must not 422 and normalizes to 'In-Chair'."""
    create_res = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": test_patient.id,
            "date_time": "2026-12-02T10:00:00",
            "status": raw_status,
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201, create_res.text
    appt_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["status"] == "In-Chair"

    put_res = client.put(
        f"/api/v1/appointments/{appt_id}",
        json={"status": raw_status},
        headers=admin_headers,
    )
    assert put_res.status_code == 200, put_res.text
    assert put_res.json()["data"]["status"] == "In-Chair"

    status_res = client.put(
        f"/api/v1/appointments/{appt_id}/status",
        params={"status": raw_status},
        headers=admin_headers,
    )
    assert status_res.status_code == 200, status_res.text
    assert status_res.json()["data"]["status"] == "In-Chair"


def test_matching_procedure_supports_bridge_and_denture_aliases():
    assert matching_procedure("جسر ثابت – Fixed Bridge", "Bridge")
    assert matching_procedure("جسر ثابت – Fixed Bridge", "جسر ثابت – Fixed Bridge")
    assert matching_procedure("تاج زيركون – Zirconia Crown", "Crown")
    assert matching_procedure("طقم جزئي أكريليك – Partial Acrylic Denture", "Partial Denture")
    assert not matching_procedure("Composite Filling", "Bridge")


@pytest.mark.parametrize(
    "treatment_proc,work_type",
    [
        ("جسر ثابت – Fixed Bridge", "Bridge"),
        ("تاج زيركون – Zirconia Crown", "تاج زيركون – Zirconia Crown"),
        ("تاج زيركون – Zirconia Crown", "Crown"),
        ("طقم جزئي أكريليك – Partial Acrylic Denture", "Partial Denture"),
    ],
)
def test_create_lab_order_linked_to_treatment_accepts_matching_work_type(
    client, db_session, test_user, test_patient, admin_headers, treatment_proc, work_type
):
    """Bug 3: Linked lab orders accept bilingual treatment names and UI dropdown work_type values."""
    lab = models.Laboratory(name="Demo Ceramics Lab", tenant_id=test_user.tenant_id)
    treatment = models.Treatment(
        patient_id=test_patient.id,
        tooth_number=16,
        procedure=treatment_proc,
        diagnosis="Caries",
        cost=Decimal("2500.00"),
        discount=Decimal("0.00"),
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    db_session.add_all([lab, treatment])
    db_session.commit()
    db_session.refresh(lab)
    db_session.refresh(treatment)

    res = client.post(
        "/api/v1/lab-orders",
        json={
            "patient_id": test_patient.id,
            "laboratory_id": lab.id,
            "treatment_id": treatment.id,
            "work_type": work_type,
            "tooth_number": "16",
            "cost": 600,
            "paid_now": 0,
            "price_to_patient": 0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["treatment_id"] == treatment.id
    assert body["work_type"] == work_type


def test_create_lab_order_linked_to_treatment_still_rejects_mismatched_work_type(
    client, db_session, test_user, test_patient, admin_headers
):
    lab = models.Laboratory(name="Demo Lab", tenant_id=test_user.tenant_id)
    treatment = models.Treatment(
        patient_id=test_patient.id,
        tooth_number=14,
        procedure="Composite Filling",
        diagnosis="Caries",
        cost=Decimal("500.00"),
        discount=Decimal("0.00"),
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    db_session.add_all([lab, treatment])
    db_session.commit()
    db_session.refresh(lab)
    db_session.refresh(treatment)

    res = client.post(
        "/api/v1/lab-orders",
        json={
            "patient_id": test_patient.id,
            "laboratory_id": lab.id,
            "treatment_id": treatment.id,
            "work_type": "Bridge",
            "tooth_number": "14",
        },
        headers=admin_headers,
    )
    assert res.status_code == 422
    assert "لا يطابق العلاج" in res.json()["detail"]
