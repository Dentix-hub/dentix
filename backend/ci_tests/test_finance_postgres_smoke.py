"""PostgreSQL-only Finance correctness gates.

This file deliberately lives outside backend/tests so the SQLite-forcing
conftest does not replace DATABASE_URL. It validates Finance through the same
AsyncSession/RLS/event-hook stack used by the application in production and
executes the legacy tenant backfill migration against real PostgreSQL.
"""

from datetime import date, datetime

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.alembic.versions import f2a4c6e8b0d1_backfill_finance_event_tenant_ids as tenant_backfill
from backend.database import AsyncSessionLocal, RlsContext, async_engine
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService


@pytest.mark.asyncio
async def test_finance_truth_runs_on_postgresql_through_application_session():
    tenant_id = 99165
    other_tenant_id = 99166

    # Seed tenant parents first under the application's explicit RLS bypass.
    # Keeping this as a separate commit avoids relying on ORM flush ordering for
    # unrelated objects that only share scalar foreign-key IDs.
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.Tenant(
                        id=tenant_id,
                        name="Finance PostgreSQL Audit",
                        timezone="Africa/Cairo",
                    ),
                    models.Tenant(
                        id=other_tenant_id,
                        name="Other PostgreSQL Audit",
                        timezone="Africa/Cairo",
                    ),
                ]
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
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
            db.add_all([doctor, other_doctor, staff, patient, laboratory])
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            treatment = models.Treatment(
                id=991655,
                patient_id=991653,
                doctor_id=991651,
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
                patient_id=991653,
                doctor_id=991651,
                amount=400.0,
                date=datetime(2026, 8, 18, 11, 0),
                tenant_id=tenant_id,
            )
            lab_order = models.LabOrder(
                id=991657,
                patient_id=991653,
                laboratory_id=991654,
                doctor_id=991651,
                work_type="Crown",
                cost=200.0,
                order_date=datetime(2026, 8, 18, 12, 0),
                tenant_id=tenant_id,
            )
            before_hire = models.Appointment(
                id=991658,
                patient_id=991653,
                date_time=datetime(2026, 8, 10, 10, 0),
                status="Scheduled",
                tenant_id=tenant_id,
                is_deleted=False,
            )
            after_hire = models.Appointment(
                id=991659,
                patient_id=991653,
                date_time=datetime(2026, 8, 20, 10, 0),
                status="Scheduled",
                tenant_id=tenant_id,
                is_deleted=False,
            )
            db.add_all([treatment, payment, lab_order, before_hire, after_hire])
            await db.commit()

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


@pytest.mark.asyncio
async def test_legacy_tenant_backfill_migration_executes_under_postgresql_rls():
    tenant_id = 99265
    other_tenant_id = 99266
    user_id = 992651
    patient_id = 992653
    laboratory_id = 992654
    treatment_id = 992655

    # Parents need valid tenant ownership; child/event rows intentionally mimic
    # historical records where tenant_id was left NULL.
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.Tenant(
                        id=tenant_id,
                        name="Migration Backfill Tenant",
                        timezone="Africa/Cairo",
                    ),
                    models.Tenant(
                        id=other_tenant_id,
                        name="Migration Isolation Tenant",
                        timezone="Africa/Cairo",
                    ),
                ]
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.User(
                        id=user_id,
                        username="pg_backfill_doctor",
                        email="pg-backfill-doctor@example.com",
                        hashed_password="h",
                        role="doctor",
                        tenant_id=tenant_id,
                    ),
                    models.Patient(
                        id=patient_id,
                        name="Backfill Patient",
                        age=37,
                        phone="01099265992",
                        medical_history="None",
                        notes="Migration backfill audit",
                        tenant_id=tenant_id,
                        is_deleted=False,
                    ),
                    models.Laboratory(
                        id=laboratory_id,
                        name="Backfill Laboratory",
                        tenant_id=tenant_id,
                    ),
                ]
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.Treatment(
                        id=treatment_id,
                        patient_id=patient_id,
                        doctor_id=user_id,
                        diagnosis="Backfill",
                        procedure="Crown",
                        cost=700.0,
                        discount=0.0,
                        date=datetime(2026, 8, 18, 8, 0),
                        tenant_id=None,
                        is_deleted=False,
                    ),
                    models.Payment(
                        id=992656,
                        patient_id=patient_id,
                        doctor_id=user_id,
                        amount=100.0,
                        date=datetime(2026, 8, 18, 9, 0),
                        tenant_id=None,
                    ),
                    models.Appointment(
                        id=992657,
                        patient_id=patient_id,
                        doctor_id=user_id,
                        date_time=datetime(2026, 8, 18, 10, 0),
                        status="Scheduled",
                        tenant_id=None,
                        is_deleted=False,
                    ),
                    models.LabOrder(
                        id=992658,
                        patient_id=patient_id,
                        laboratory_id=laboratory_id,
                        doctor_id=user_id,
                        work_type="Crown",
                        cost=150.0,
                        order_date=datetime(2026, 8, 18, 11, 0),
                        tenant_id=None,
                    ),
                    models.TreatmentSession(
                        id=992659,
                        treatment_id=treatment_id,
                        session_date=datetime(2026, 8, 18, 12, 0),
                        tenant_id=None,
                    ),
                    models.LabPayment(
                        id=992660,
                        laboratory_id=laboratory_id,
                        amount=50.0,
                        date=datetime(2026, 8, 18, 13, 0),
                        tenant_id=None,
                    ),
                    models.SalaryPayment(
                        id=992661,
                        user_id=user_id,
                        month="2026-08",
                        amount=250.0,
                        payment_date=datetime(2026, 8, 18, 14, 0),
                        tenant_id=None,
                    ),
                ]
            )
            await db.commit()

    def _run_upgrade(sync_connection):
        migration_context = MigrationContext.configure(sync_connection)
        with Operations.context(migration_context):
            tenant_backfill.upgrade()

    async with async_engine.begin() as connection:
        await connection.run_sync(_run_upgrade)

    # The repaired row must become visible to its tenant and remain hidden from
    # an unrelated tenant, proving the migration did not weaken FORCE RLS.
    async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
        repaired = (
            await db.execute(
                select(models.Treatment).where(models.Treatment.id == treatment_id)
            )
        ).scalars().first()
        assert repaired is not None
        assert repaired.tenant_id == tenant_id

        for model, row_id in (
            (models.Payment, 992656),
            (models.Appointment, 992657),
            (models.LabOrder, 992658),
            (models.TreatmentSession, 992659),
            (models.LabPayment, 992660),
            (models.SalaryPayment, 992661),
        ):
            row = (
                await db.execute(select(model).where(model.id == row_id))
            ).scalars().first()
            assert row is not None
            assert row.tenant_id == tenant_id

    async with AsyncSessionLocal(context=RlsContext(tenant_id=other_tenant_id)) as db:
        hidden = (
            await db.execute(
                select(models.Treatment).where(models.Treatment.id == treatment_id)
            )
        ).scalars().first()
        assert hidden is None

    await async_engine.dispose()
