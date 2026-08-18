"""Targeted regressions discovered during the post-fix Finance forensic audit."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService


@pytest.mark.asyncio
async def test_patient_financial_details_keep_patient_owned_legacy_null_tenant_events(
    async_db_session,
):
    tenant_id = 160
    patient = models.Patient(
        id=1601,
        name="Legacy Detail Patient",
        age=38,
        phone="01016001600",
        medical_history="None",
        notes="Finance audit legacy detail fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    treatment = models.Treatment(
        id=1602,
        patient_id=patient.id,
        procedure="Legacy crown",
        diagnosis="Missing tooth",
        cost=1000.0,
        discount=100.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
        tenant_id=None,
        is_deleted=False,
    )
    payment = models.Payment(
        id=1603,
        patient_id=patient.id,
        amount=400.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        tenant_id=None,
    )
    async_db_session.add_all([patient, treatment, payment])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    details = await service.get_patient_financial_details(patient.id)

    assert details is not None
    assert details["total_invoiced"] == 900.0
    assert details["total_paid"] == 400.0
    assert details["outstanding_balance"] == 500.0
    assert len(details["treatment_history"]) == 1
    assert len(details["payment_history"]) == 1


@pytest.mark.asyncio
async def test_explicit_payment_doctor_cannot_cross_tenant_boundary(async_db_session):
    tenant_id = 161
    other_tenant_id = 162
    patient = models.Patient(
        id=1611,
        name="Payment Tenant Patient",
        age=30,
        phone="01016101610",
        medical_history="None",
        notes="Cross-tenant payment provider fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    other_doctor = models.User(
        id=1621,
        username="other_tenant_doctor",
        email="other-tenant-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=other_tenant_id,
    )
    async_db_session.add_all([patient, other_doctor])
    await async_db_session.commit()

    payment = schemas.PaymentCreate(
        patient_id=patient.id,
        doctor_id=other_doctor.id,
        amount=250.0,
        date=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="Doctor not found"):
        await BillingService(async_db_session, tenant_id).create_payment(payment)

    persisted = (
        await async_db_session.execute(
            select(models.Payment).where(models.Payment.patient_id == patient.id)
        )
    ).scalars().all()
    assert persisted == []


@pytest.mark.asyncio
async def test_payroll_month_before_hire_date_has_zero_payable_salary(async_db_session):
    tenant_id = 163
    employee = models.User(
        id=1631,
        username="future_hire_assistant",
        email="future-hire-assistant@example.com",
        hashed_password="h",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=3100.0,
        hire_date=date(2026, 8, 16),
    )
    admin = models.User(
        id=1632,
        username="payroll_admin",
        email="payroll-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    async_db_session.add_all([employee, admin])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    status = await service.get_salary_status_for_month("2026-07")
    row = next(item for item in status["employees"] if item["id"] == employee.id)

    assert row["days_worked"] == 0
    assert row["prorated_salary"] == 0.0
    assert row["payable_amount"] == 0.0
    assert row["remaining_amount"] == 0.0

    result = await service.process_salary_payment(
        user_id=employee.id,
        current_user=admin,
        month="2026-07",
        amount=100.0,
        is_partial=False,
        days_worked=None,
        notes="Must not be payable before hire date",
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_staff_per_appointment_fee_starts_on_hire_date(async_db_session):
    tenant_id = 164
    staff = models.User(
        id=1641,
        username="mid_month_fee_assistant",
        email="mid-month-fee-assistant@example.com",
        hashed_password="h",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=0.0,
        per_appointment_fee=50.0,
        hire_date=date(2026, 8, 16),
    )
    patient = models.Patient(
        id=1642,
        name="Appointment Fee Patient",
        age=33,
        phone="01016401640",
        medical_history="None",
        notes="Hire-date appointment fee fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    before_hire = models.Appointment(
        id=1643,
        patient_id=patient.id,
        date_time=datetime(2026, 8, 10, 10, 0),
        status="Scheduled",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    after_hire = models.Appointment(
        id=1644,
        patient_id=patient.id,
        date_time=datetime(2026, 8, 20, 10, 0),
        status="Scheduled",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all([staff, patient, before_hire, after_hire])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-01", "2026-08-31")
    rows, total = await service.calculate_staff_dues(
        start,
        end,
        total_appointments=2,
    )
    row = next(item for item in rows if item["id"] == staff.id)

    assert row["appointments_in_period"] == 1
    assert row["appointment_earnings"] == 50.0
    assert row["total_due"] == 50.0
    assert total == 50.0


@pytest.mark.asyncio
async def test_lab_costs_keep_patient_owned_legacy_null_tenant_orders(async_db_session):
    tenant_id = 165
    doctor = models.User(
        id=1651,
        username="legacy_lab_doctor",
        email="legacy-lab-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
        commission_percent=20.0,
    )
    patient = models.Patient(
        id=1652,
        name="Legacy Lab Patient",
        age=39,
        phone="01016501650",
        medical_history="None",
        notes="Legacy NULL lab tenant fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    laboratory = models.Laboratory(
        id=1653,
        name="Legacy Lab",
        tenant_id=tenant_id,
    )
    lab_order = models.LabOrder(
        id=1654,
        patient_id=patient.id,
        laboratory_id=laboratory.id,
        doctor_id=doctor.id,
        work_type="Crown",
        cost=600.0,
        order_date=datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc),
        tenant_id=None,
    )
    async_db_session.add_all([doctor, patient, laboratory, lab_order])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-18", "2026-08-18")

    assert await service.get_total_lab_costs(start, end) == 600.0
    analytics = await service.get_doctor_revenue_analytics(start, end)
    doctor_row = next(row for row in analytics if row["doctor_id"] == doctor.id)
    assert doctor_row["lab_cost"] == 600.0

    details = await service.get_doctor_details_data(doctor.id, start, end)
    assert details["total_lab_cost"] == 600.0
    assert len(details["lab_orders"]) == 1
