"""Regression coverage for finance totals, date filters, and payment attribution."""

from datetime import datetime, timezone

import pytest

from backend import models, schemas
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService


def _patient(patient_id: int, tenant_id: int, name: str, phone: str):
    return models.Patient(
        id=patient_id,
        name=name,
        age=35,
        phone=phone,
        medical_history="None",
        notes="Finance regression fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_accounting_day_filter_uses_cairo_business_day(async_db_session):
    tenant_id = 140
    patient = _patient(1401, tenant_id, "Timezone Patient", "01014001400")
    included = models.Payment(
        id=1402, patient_id=patient.id, amount=700.0,
        date=datetime(2026, 8, 17, 21, 30, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    excluded = models.Payment(
        id=1403, patient_id=patient.id, amount=900.0,
        date=datetime(2026, 8, 18, 21, 30, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    async_db_session.add_all([patient, included, excluded])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-18", "2026-08-18")
    assert await service.get_total_collected(start, end) == 700.0


@pytest.mark.asyncio
async def test_patient_report_does_not_fallback_outside_requested_period(async_db_session):
    tenant_id = 141
    patient = _patient(1411, tenant_id, "Historical Only", "01014101410")
    treatment = models.Treatment(
        id=1412, patient_id=patient.id, procedure="Old Filling", diagnosis="Caries",
        cost=1000.0, discount=0.0,
        date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=False,
    )
    async_db_session.add_all([patient, treatment])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-18", "2026-08-18")
    report = await service.get_patients_report(start=start, end=end)
    assert report["total"] == 0
    assert report["patients"] == []
    assert report["summary"]["total_invoiced"] == 0.0
    assert report["summary"]["total_paid"] == 0.0


@pytest.mark.asyncio
async def test_soft_deleted_treatments_never_affect_finance_totals(async_db_session):
    tenant_id = 142
    patient = _patient(1421, tenant_id, "Soft Delete Patient", "01014201420")
    active = models.Treatment(
        id=1422, patient_id=patient.id, procedure="Active", diagnosis="A",
        cost=1000.0, discount=100.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=False,
    )
    deleted = models.Treatment(
        id=1423, patient_id=patient.id, procedure="Deleted", diagnosis="D",
        cost=9000.0, discount=0.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=True,
    )
    async_db_session.add_all([patient, active, deleted])
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)
    start, end = accounting.parse_date_range("2026-08-18", "2026-08-18")
    assert await accounting.get_total_income(start, end) == 900.0
    assert await BillingService(async_db_session, tenant_id).get_outstanding_balance(patient.id) == 900.0


@pytest.mark.asyncio
async def test_mixed_tagged_and_untagged_payments_are_all_attributed(async_db_session):
    tenant_id = 143
    doctor_a = models.User(
        id=1431, username="doctor_a", email="doctor-a@example.com",
        hashed_password="h", role="doctor", tenant_id=tenant_id,
        commission_percent=0.0, fixed_salary=0.0,
    )
    doctor_b = models.User(
        id=1432, username="doctor_b", email="doctor-b@example.com",
        hashed_password="h", role="doctor", tenant_id=tenant_id,
        commission_percent=0.0, fixed_salary=0.0,
    )
    patient = _patient(1433, tenant_id, "Shared Patient", "01014301430")
    treatment_a = models.Treatment(
        id=1434, patient_id=patient.id, doctor_id=doctor_a.id,
        procedure="A", diagnosis="A", cost=1000.0, discount=0.0,
        date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=False,
    )
    treatment_b = models.Treatment(
        id=1435, patient_id=patient.id, doctor_id=doctor_b.id,
        procedure="B", diagnosis="B", cost=3000.0, discount=0.0,
        date=datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=False,
    )
    direct = models.Payment(
        id=1436, patient_id=patient.id, doctor_id=doctor_a.id, amount=400.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    untagged = models.Payment(
        id=1437, patient_id=patient.id, doctor_id=None, amount=800.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    async_db_session.add_all([doctor_a, doctor_b, patient, treatment_a, treatment_b, direct, untagged])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-18", "2026-08-18")
    rows = await service.get_doctor_revenue_analytics(start, end)
    by_id = {row["doctor_id"]: row for row in rows}
    assert by_id[doctor_a.id]["collected"] == 600.0
    assert by_id[doctor_b.id]["collected"] == 600.0
    assert sum(row["collected"] for row in rows) == 1200.0


@pytest.mark.asyncio
async def test_daily_filter_prorates_monthly_fixed_compensation(async_db_session):
    tenant_id = 144
    doctor = models.User(
        id=1441, username="salary_doctor", email="salary-doctor@example.com",
        hashed_password="h", role="doctor", tenant_id=tenant_id,
        commission_percent=0.0, fixed_salary=3100.0,
    )
    assistant = models.User(
        id=1442, username="salary_assistant", email="salary-assistant@example.com",
        hashed_password="h", role="assistant", tenant_id=tenant_id,
        fixed_salary=3100.0, per_appointment_fee=0.0,
    )
    async_db_session.add_all([doctor, assistant])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-18", "2026-08-18")
    doctor_row = next(row for row in await service.get_doctor_revenue_analytics(start, end) if row["doctor_id"] == doctor.id)
    assert doctor_row["fixed_salary"] == 3100.0
    assert doctor_row["fixed_salary_period"] == 100.0
    assert doctor_row["total_due"] == 100.0

    staff_rows, staff_total = await service.calculate_staff_dues(start, end, 0)
    staff_row = next(row for row in staff_rows if row["id"] == assistant.id)
    assert staff_row["fixed_salary_period"] == 100.0
    assert staff_total == 100.0


@pytest.mark.asyncio
async def test_payment_without_doctor_uses_latest_active_treatment_provider(async_db_session):
    tenant_id = 145
    doctor = models.User(
        id=1451, username="payment_doctor", email="payment-doctor@example.com",
        hashed_password="h", role="doctor", tenant_id=tenant_id,
    )
    patient = _patient(1452, tenant_id, "Payment Attribution", "01014501450")
    treatment = models.Treatment(
        id=1453, patient_id=patient.id, doctor_id=doctor.id,
        procedure="Crown", diagnosis="Missing tooth", cost=2000.0, discount=0.0,
        date=datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=False,
    )
    async_db_session.add_all([doctor, patient, treatment])
    await async_db_session.commit()

    payment = await BillingService(async_db_session, tenant_id).create_payment(
        schemas.PaymentCreate(patient_id=patient.id, amount=500.0), doctor_id=None, commit=False,
    )
    assert payment.doctor_id == doctor.id


@pytest.mark.asyncio
async def test_comprehensive_stats_excludes_deleted_rows_and_prorates_staff(async_db_session):
    from backend.routers.accounting import get_comprehensive_stats

    tenant_id = 146
    admin = models.User(
        id=1461, username="finance_admin", email="finance-admin-146@example.com",
        hashed_password="h", role="admin", tenant_id=tenant_id,
    )
    assistant = models.User(
        id=1462, username="finance_assistant", email="finance-assistant-146@example.com",
        hashed_password="h", role="assistant", tenant_id=tenant_id,
        fixed_salary=3100.0, per_appointment_fee=0.0,
    )
    patient = _patient(1463, tenant_id, "Comprehensive Patient", "01014601460")
    appointment = models.Appointment(
        id=1467, patient_id=patient.id,
        date_time=datetime(2026, 8, 18, 10, 0),
        status="Scheduled", tenant_id=tenant_id, is_deleted=False,
    )
    active = models.Treatment(
        id=1464, patient_id=patient.id, procedure="Active", diagnosis="A",
        cost=1000.0, discount=0.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=False,
    )
    deleted = models.Treatment(
        id=1465, patient_id=patient.id, procedure="Deleted", diagnosis="D",
        cost=9000.0, discount=0.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id, is_deleted=True,
    )
    payment = models.Payment(
        id=1466, patient_id=patient.id, amount=500.0,
        date=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    async_db_session.add_all(
        [admin, assistant, patient, appointment, active, deleted, payment]
    )
    await async_db_session.commit()

    response = await get_comprehensive_stats(
        start_date="2026-08-18", end_date="2026-08-18", patient_id=None,
        db=async_db_session, current_user=admin,
    )
    data = response["data"]
    assert data["income"]["gross_revenue"] == 1000.0
    assert data["income"]["total_revenue"] == 1000.0
    assert data["income"]["total_collected"] == 500.0
    assert data["income"]["total_appointments"] == 1
    assert data["income"]["unique_patients"] == 1
    assert data["deductions"]["staff_dues"]["total"] == 100.0
    assert data["income"]["all_time_outstanding"] == 500.0


@pytest.mark.asyncio
async def test_payments_list_date_filter_uses_tenant_business_day(async_db_session):
    from backend.routers.payments import read_payments

    tenant_id = 147
    admin = models.User(
        id=1471, username="payments_admin", email="payments-admin-147@example.com",
        hashed_password="h", role="admin", tenant_id=tenant_id,
    )
    patient = _patient(1472, tenant_id, "Payments Date Patient", "01014701470")
    included = models.Payment(
        id=1473, patient_id=patient.id, amount=111.0,
        date=datetime(2026, 8, 17, 21, 30, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    excluded = models.Payment(
        id=1474, patient_id=patient.id, amount=222.0,
        date=datetime(2026, 8, 18, 21, 30, tzinfo=timezone.utc), tenant_id=tenant_id,
    )
    async_db_session.add_all([admin, patient, included, excluded])
    await async_db_session.commit()

    response = await read_payments(
        skip=0, limit=100, search=None,
        start_date="2026-08-18", end_date="2026-08-18",
        patient_id=None, doctor_id=None,
        db=async_db_session, current_user=admin,
    )
    assert [row.id for row in response["data"]] == [included.id]
