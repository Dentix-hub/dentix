"""Regression coverage for Finance V2 payment identifier/deep-link filters."""

from datetime import datetime, timezone

import pytest

from backend import models
from backend.routers.payments import read_payments


@pytest.mark.asyncio
async def test_payment_list_filters_by_file_receipt_and_numeric_search(async_db_session):
    tenant_id = 310
    tenant = models.Tenant(id=tenant_id, name="Finance Filter Clinic", timezone="Africa/Cairo")
    admin = models.User(
        id=3101,
        username="finance_filter_admin",
        email="finance-filter-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    patient = models.Patient(
        id=3102,
        name="Identifier Patient",
        age=30,
        phone="01031003102",
        medical_history="None",
        notes="Identifier filter regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    other_patient = models.Patient(
        id=3103,
        name="Other Patient",
        age=31,
        phone="01031003103",
        medical_history="None",
        notes="Other payment",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    target = models.Payment(
        id=3104,
        patient_id=patient.id,
        amount=500.0,
        date=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        notes="Target receipt",
        tenant_id=tenant_id,
    )
    other = models.Payment(
        id=3105,
        patient_id=other_patient.id,
        amount=700.0,
        date=datetime(2026, 8, 20, 11, 0, tzinfo=timezone.utc),
        notes="Other receipt",
        tenant_id=tenant_id,
    )
    async_db_session.add_all([tenant, admin, patient, other_patient, target, other])
    await async_db_session.commit()

    common = {
        "skip": 0,
        "limit": 20,
        "start_date": None,
        "end_date": None,
        "doctor_id": None,
        "db": async_db_session,
        "current_user": admin,
    }

    by_file = await read_payments(
        search=None,
        patient_id=None,
        file_number=patient.id,
        payment_id=None,
        **common,
    )
    assert [row.id for row in by_file["data"]] == [target.id]

    # Exact receipt deep links must remain reproducible even when an old page=N
    # query parameter survives in a copied URL.
    by_receipt = await read_payments(
        skip=999,
        limit=20,
        search=None,
        start_date=None,
        end_date=None,
        patient_id=None,
        file_number=None,
        payment_id=target.id,
        doctor_id=None,
        db=async_db_session,
        current_user=admin,
    )
    assert [row.id for row in by_receipt["data"]] == [target.id]

    by_numeric_search = await read_payments(
        search=f"#{target.id}",
        patient_id=None,
        file_number=None,
        payment_id=None,
        **common,
    )
    assert [row.id for row in by_numeric_search["data"]] == [target.id]


@pytest.mark.asyncio
async def test_payment_identifier_filters_remain_tenant_scoped(async_db_session):
    tenant_a = models.Tenant(id=311, name="Tenant A", timezone="Africa/Cairo")
    tenant_b = models.Tenant(id=312, name="Tenant B", timezone="Africa/Cairo")
    admin = models.User(
        id=3111,
        username="tenant_a_admin",
        email="tenant-a-filter-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_a.id,
    )
    patient_b = models.Patient(
        id=3112,
        name="Tenant B Patient",
        age=32,
        phone="01031103112",
        medical_history="None",
        notes="Cross tenant",
        tenant_id=tenant_b.id,
        is_deleted=False,
    )
    payment_b = models.Payment(
        id=3113,
        patient_id=patient_b.id,
        amount=900.0,
        date=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
        tenant_id=tenant_b.id,
    )
    async_db_session.add_all([tenant_a, tenant_b, admin, patient_b, payment_b])
    await async_db_session.commit()

    response = await read_payments(
        skip=0,
        limit=20,
        search=None,
        start_date=None,
        end_date=None,
        patient_id=None,
        file_number=patient_b.id,
        payment_id=payment_b.id,
        doctor_id=None,
        db=async_db_session,
        current_user=admin,
    )
    assert response["data"] == []
