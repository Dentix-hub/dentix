"""Regression coverage for AI/automation finance paths sharing Finance V2 truth."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.ai.handlers.finance import FinanceHandler
from backend.services.billing_service import BillingService
from backend.services.finance_service import FinanceService


def make_patient(patient_id: int, tenant_id: int, name: str):
    return models.Patient(
        id=patient_id,
        name=name,
        age=35,
        phone=f"010{patient_id:08d}"[-11:],
        medical_history="None",
        notes="Finance AI regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_missing_payment_date_is_materialized_as_utc_naive(async_db_session):
    tenant_id = 152
    doctor = models.User(
        id=1521,
        username="timestamp_doctor",
        email="timestamp-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
    )
    patient = make_patient(1522, tenant_id, "Timestamp Patient")
    treatment = models.Treatment(
        id=1523,
        patient_id=patient.id,
        doctor_id=doctor.id,
        procedure="Filling",
        diagnosis="Caries",
        cost=1000.0,
        discount=0.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all([doctor, patient, treatment])
    await async_db_session.commit()

    payment = await BillingService(async_db_session, tenant_id).create_payment(
        schemas.PaymentCreate(patient_id=patient.id, amount=250.0),
        doctor_id=None,
        commit=False,
    )
    assert payment.date is not None
    assert payment.date.tzinfo is None
    assert payment.doctor_id == doctor.id


@pytest.mark.asyncio
async def test_finance_service_does_not_attribute_admin_as_provider(async_db_session):
    tenant_id = 153
    admin = models.User(
        id=1531,
        username="finance_service_admin",
        email="finance-service-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    doctor = models.User(
        id=1532,
        username="finance_service_doctor",
        email="finance-service-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
    )
    patient = make_patient(1533, tenant_id, "Finance Service Patient")
    treatment = models.Treatment(
        id=1534,
        patient_id=patient.id,
        doctor_id=doctor.id,
        procedure="Crown",
        diagnosis="Missing tooth",
        cost=2000.0,
        discount=0.0,
        date=datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all([admin, doctor, patient, treatment])
    await async_db_session.commit()

    result = await FinanceService(async_db_session, tenant_id).create_payment(
        patient.name,
        500.0,
        user_id=admin.id,
    )
    payment = (
        await async_db_session.execute(
            select(models.Payment).where(models.Payment.id == result["payment_id"])
        )
    ).scalar_one()
    assert payment.doctor_id == doctor.id
    assert payment.date is not None


@pytest.mark.asyncio
async def test_active_ai_financial_record_uses_net_active_treatments(async_db_session):
    tenant_id = 154
    admin = models.User(
        id=1541,
        username="ai_finance_admin",
        email="ai-finance-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    patient = make_patient(1542, tenant_id, "AI Financial Record Patient")
    active = models.Treatment(
        id=1543,
        patient_id=patient.id,
        procedure="Active",
        diagnosis="A",
        cost=1000.0,
        discount=100.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    deleted = models.Treatment(
        id=1544,
        patient_id=patient.id,
        procedure="Deleted",
        diagnosis="D",
        cost=5000.0,
        discount=0.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=True,
    )
    payment = models.Payment(
        id=1545,
        patient_id=patient.id,
        amount=400.0,
        date=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([admin, patient, active, deleted, payment])
    await async_db_session.commit()

    record = await FinanceHandler(async_db_session, admin).get_financial_record({
        "patient_name": patient.name,
    })
    assert record["total_cost"] == 900.0
    assert record["total_invoiced"] == 900.0
    assert record["total_paid"] == 400.0
    assert record["remaining"] == 500.0
