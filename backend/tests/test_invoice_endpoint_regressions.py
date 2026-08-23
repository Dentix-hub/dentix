"""Regression tests for the server-authoritative patient invoice (CRITICAL-02).

Guarantees:
- Totals are computed server-side with net = cost - discount (never gross).
- Invoice number is deterministic across reprints.
- Clinic identity comes from the requesting tenant, not hardcoded values.
- Cross-tenant invoice access returns 404.
"""

from decimal import Decimal

import pytest

from backend import models


@pytest.fixture
def invoice_patient(db_session, test_tenant, test_user):
    patient = models.Patient(
        name="Invoice Patient",
        phone="01000011122",
        age=40,
        medical_history="",
        notes="",
        tenant_id=test_tenant.id,
        assigned_doctor_id=test_user.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def _add_treatment(db_session, patient, tenant_id, cost, discount, procedure="حشو"):
    treatment = models.Treatment(
        patient_id=patient.id,
        diagnosis="تسوس",
        procedure=procedure,
        cost=Decimal(str(cost)),
        discount=Decimal(str(discount)),
        tenant_id=tenant_id,
    )
    db_session.add(treatment)
    db_session.commit()
    db_session.refresh(treatment)
    return treatment


def _add_payment(db_session, patient, tenant_id, amount):
    payment = models.Payment(
        patient_id=patient.id,
        amount=Decimal(str(amount)),
        tenant_id=tenant_id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment


def test_invoice_totals_use_net_after_discount(
    client, admin_headers, db_session, test_tenant, invoice_patient
):
    _add_treatment(db_session, invoice_patient, test_tenant.id, cost=500, discount=100)
    _add_treatment(db_session, invoice_patient, test_tenant.id, cost=300, discount=0)
    _add_payment(db_session, invoice_patient, test_tenant.id, amount=200)

    response = client.get(
        f"/api/v1/patients/{invoice_patient.id}/invoice", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    totals = data["totals"]

    assert totals["gross_total"] == pytest.approx(800.0)
    assert totals["discount_total"] == pytest.approx(100.0)
    # The printed total must match the patient account rule: cost - discount.
    assert totals["net_total"] == pytest.approx(700.0)
    assert totals["paid_total"] == pytest.approx(200.0)
    assert totals["remaining_total"] == pytest.approx(500.0)


def test_invoice_number_is_stable_and_clinic_identity_from_tenant(
    client, admin_headers, db_session, test_tenant, invoice_patient
):
    response_one = client.get(
        f"/api/v1/patients/{invoice_patient.id}/invoice", headers=admin_headers
    )
    response_two = client.get(
        f"/api/v1/patients/{invoice_patient.id}/invoice", headers=admin_headers
    )

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    first = response_one.json()["data"]
    second = response_two.json()["data"]

    assert first["invoice_number"] == second["invoice_number"]
    assert first["invoice_number"].startswith("INV-")
    assert first["clinic_name"] == test_tenant.name
    assert first["currency"] == "EGP"


def test_invoice_rejects_cross_tenant_patient(
    client, admin_headers, db_session, test_tenant, test_user
):
    other_tenant = models.Tenant(name="Other Clinic", is_active=True)
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    foreign_patient = models.Patient(
        name="Foreign Patient",
        phone="01111111111",
        age=25,
        medical_history="",
        notes="",
        tenant_id=other_tenant.id,
    )
    db_session.add(foreign_patient)
    db_session.commit()
    db_session.refresh(foreign_patient)

    _add_treatment(db_session, foreign_patient, other_tenant.id, cost=999, discount=0)

    response = client.get(
        f"/api/v1/patients/{foreign_patient.id}/invoice", headers=admin_headers
    )

    assert response.status_code == 404


def test_invoice_requires_receivable_read_permission(client, auth_headers, invoice_patient):
    """Doctors hold CLINICAL_READ but not RECEIVABLE_READ; payment data stays protected."""
    response = client.get(
        f"/api/v1/patients/{invoice_patient.id}/invoice", headers=auth_headers
    )
    assert response.status_code == 403
