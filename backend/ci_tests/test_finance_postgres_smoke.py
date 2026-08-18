"""PostgreSQL-only Finance smoke used by the temporary forensic audit workflow.

This file deliberately lives outside backend/tests so the SQLite-forcing
conftest does not replace DATABASE_URL. It validates Finance through the same
AsyncSession/RLS/event-hook stack used by the application in production.
"""

from datetime import date, datetime

import pytest

from backend import models, schemas
from backend.database import AsyncSessionLocal, RlsContext, async_engine
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService


@pytest.mark.asyncio
async def test_finance_truth_runs_on_postgresql_through_application_session():
    tenant_id = 99165
    other_tenant_id = 99166

    # Seed two tenants under the application's explicit RLS bypass. This mirrors
    # platform-maintenance behavior while still exercising the production
    # asyncpg engine and its timestamp normalization hooks.
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            tenant = models.Tenant(
                id=tenant_id,
                name="Finance PostgreSQL Audit",
                timezone="Africa/Cairo",
            )
            other_tenant = models.Tenant(
                id=other_tenant_id,
                name="Other PostgreSQL Audit",
                timezone="Africa/Cairo",
            )
            doctor = models.User(
                id=991651,
                username="pg_finance_doctor",
                email="pg-finance-doctor@example.com",
                hashed_password="h",
                role="doctor",
                tenant_id=tenant_id,
                commission_percent=20.0,
            )
            other_doctor = models.User(
                id=991661,
                username="pg_other_doctor",
                email="pg-other-doctor@example.com",
                hashed_password="h",
                role="doctor",
                tenant_id=other_tenant_id,
            )
            staff = models.User(
                id=991652,
                username="pg_finance_assistant",
                email="pg-finance-assistant@example.com",
                hashed_password="h",
                role="assistant",
                tenant_id=tenant_id,
                fixed_salary=0.0,
                per_appointment_fee=50.0,
                hire_date=date(2026, 8, 16),
            )
            patient = models.Patient(
                id=991653,
                name="PostgreSQL Finance Patient",
                age=40,
                phone="01099165991",
                medical_history="None",
                notes="PostgreSQL Finance audit",
                tenant_id=tenant_id,
                is_deleted=False,
            )
            laboratory = models.Laboratory(
                id=991654,
                name="PostgreSQL Audit Lab",
                tenant_id=tenant_id,
            )
            treatment = models.Treatment(
                id=991655,
                patient_id=patient.id,
                doctor_id=doctor.id,
                procedure="Crown",
                diagnosis="Missing tooth",
                cost=1000.0,
                discount=100.0,
                date=datetime(2026, 8, 18, 10, 0),
                tenant_id=tenant_id,
                is_deleted=False,
            )
            payment = models.Payment(
                id=991656,
                patient_id=patient.id,
                doctor_id=doctor.id,
                amount=400.0,
                date=datetime(2026, 8, 18, 11, 0),
                tenant_id=tenant_id,
            )
            lab_order = models.LabOrder(
                id=991657,
                patient_id=patient.id,
                laboratory_id=laboratory.id,
                doctor_id=doctor.id,
                work_type="Crown",
                cost=200.0,
                order_date=datetime(2026, 8, 18, 12, 0),
                tenant_id=tenant_id,
            )
            before_hire = models.Appointment(
                id=991658,
                patient_id=patient.id,
                date_time=datetime(2026, 8, 10, 10, 0),
                status="Scheduled",
                tenant_id=tenant_id,
                is_deleted=False,
            )
            after_hire = models.Appointment(
                id=991659,
                patient_id=patient.id,
                date_time=datetime(2026, 8, 20, 10, 0),
                status="Scheduled",
                tenant_id=tenant_id,
                is_deleted=False,
            )
            db.add_all(
                [
                    tenant,
                    other_tenant,
                    doctor,
                    other_doctor,
                    staff,
                    patient,
                    laboratory,
                    treatment,
                    payment,
                    lab_order,
                    before_hire,
                    after_hire,
                ]
            )
            await db.commit()

    try:
        # Re-open exactly as a tenant-scoped request would. RLS must isolate the
        # other tenant while every Finance calculation remains correct.
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            service = AccountingService(db, tenant_id)
            start, end = service.parse_date_range("2026-08-01", "2026-08-31")

            assert await service.get_total_income(start, end) == 900.0
            assert await service.get_total_collected(start, end) == 400.0
            assert await service.get_total_lab_costs(start, end) == 200.0
            assert await BillingService(db, tenant_id).get_outstanding_balance() == 500.0

            staff_rows, staff_total = await service.calculate_staff_dues(
                start,
                end,
                total_appointments=2,
            )
            staff_row = next(row for row in staff_rows if row["id"] == 991652)
            assert staff_row["appointments_in_period"] == 1
            assert staff_row["appointment_earnings"] == 50.0
            assert staff_total == 50.0

            details = await service.get_patient_financial_details(991653)
            assert details["total_invoiced"] == 900.0
            assert details["total_paid"] == 400.0
            assert details["outstanding_balance"] == 500.0

            july = await service.get_salary_status_for_month("2026-07")
            july_staff = next(row for row in july["employees"] if row["id"] == 991652)
            assert july_staff["payable_amount"] == 0.0

            cross_tenant_payment = schemas.PaymentCreate(
                patient_id=991653,
                doctor_id=991661,
                amount=50.0,
                date=datetime(2026, 8, 18, 14, 0),
            )
            with pytest.raises(ValueError, match="Doctor not found"):
                await BillingService(db, tenant_id).create_payment(cross_tenant_payment)
    finally:
        await async_engine.dispose()
