from datetime import date, datetime

import pytest

from backend import models
from backend.crud.reporting import (
    get_dashboard_stats,
    get_financial_stats,
    get_today_debtors,
    get_today_payments,
)


@pytest.mark.asyncio
async def test_today_outstanding_matches_debtor_modal_and_excludes_future(async_db_session):
    db = async_db_session
    tenant = models.Tenant(name="Timezone Clinic", timezone="Africa/Cairo", is_active=True)
    db.add(tenant)
    await db.flush()

    doctor_a = models.User(
        username="tz_doctor_a",
        email="tz_doctor_a@test.com",
        hashed_password="not-used",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
    )
    doctor_b = models.User(
        username="tz_doctor_b",
        email="tz_doctor_b@test.com",
        hashed_password="not-used",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add_all([doctor_a, doctor_b])
    await db.flush()

    patient_a = models.Patient(
        name="Patient A",
        age=30,
        phone="01000000001",
        email=None,
        address=None,
        medical_history="",
        notes="",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor_a.id,
        created_at=datetime(2026, 8, 16, 21, 0),
    )
    patient_b = models.Patient(
        name="Patient B",
        age=31,
        phone="01000000002",
        email=None,
        address=None,
        medical_history="",
        notes="",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor_b.id,
        created_at=datetime(2026, 8, 16, 20, 59, 59),
    )
    db.add_all([patient_a, patient_b])
    await db.flush()

    db.add_all(
        [
            models.Treatment(
                patient_id=patient_a.id,
                doctor_id=doctor_a.id,
                tenant_id=tenant.id,
                diagnosis="test",
                procedure="test",
                cost=500,
                discount=0,
                date=datetime(2026, 8, 16, 21, 0),
            ),
            models.Payment(
                patient_id=patient_a.id,
                doctor_id=doctor_a.id,
                tenant_id=tenant.id,
                amount=200,
                date=datetime(2026, 8, 17, 12, 0),
            ),
            models.Treatment(
                patient_id=patient_b.id,
                doctor_id=doctor_b.id,
                tenant_id=tenant.id,
                diagnosis="test",
                procedure="test",
                cost=400,
                discount=0,
                date=datetime(2026, 8, 17, 10, 0),
            ),
            models.Payment(
                patient_id=patient_b.id,
                doctor_id=doctor_b.id,
                tenant_id=tenant.id,
                amount=500,
                date=datetime(2026, 8, 17, 11, 0),
            ),
            models.Payment(
                patient_id=patient_a.id,
                doctor_id=doctor_a.id,
                tenant_id=tenant.id,
                amount=999,
                date=datetime(2026, 8, 17, 21, 0),
            ),
            models.Appointment(
                patient_id=patient_a.id,
                doctor_id=doctor_a.id,
                tenant_id=tenant.id,
                date_time=datetime(2026, 8, 17, 0, 0),
                status="Scheduled",
            ),
            models.Appointment(
                patient_id=patient_a.id,
                doctor_id=doctor_a.id,
                tenant_id=tenant.id,
                date_time=datetime(2026, 8, 18, 0, 0),
                status="Scheduled",
            ),
        ]
    )
    await db.flush()

    business_date = date(2026, 8, 17)
    debtors = await get_today_debtors(
        db,
        tenant.id,
        timezone_name=tenant.timezone,
        business_date=business_date,
    )
    stats = await get_financial_stats(
        db,
        tenant.id,
        timezone_name=tenant.timezone,
        business_date=business_date,
    )
    payments = await get_today_payments(
        db,
        tenant.id,
        timezone_name=tenant.timezone,
        business_date=business_date,
    )
    dashboard = await get_dashboard_stats(
        db,
        tenant.id,
        timezone_name=tenant.timezone,
        business_date=business_date,
        appointment_doctor_id=doctor_a.id,
    )

    assert len(debtors) == 1
    assert debtors[0]["id"] == patient_a.id
    assert debtors[0]["amount"] == pytest.approx(300.0)
    assert stats["today_outstanding"] == pytest.approx(
        sum(row["amount"] for row in debtors)
    )
    assert stats["today_received"] == pytest.approx(700.0)
    assert all(row["amount"] != 999 for row in payments)
    assert all(row["date"].endswith("Z") for row in payments)
    assert dashboard["new_patients_today"] == 1
    assert dashboard["total_appointments_today"] == 1
    assert dashboard["business_date"] == "2026-08-17"
    assert dashboard["tenant_timezone"] == "Africa/Cairo"


@pytest.mark.asyncio
async def test_doctor_patient_scope_uses_assigned_patient(async_db_session):
    db = async_db_session
    tenant = models.Tenant(name="Scoped Clinic", timezone="Africa/Cairo", is_active=True)
    db.add(tenant)
    await db.flush()

    doctor_a = models.User(
        username="scope_doctor_a",
        email="scope_doctor_a@test.com",
        hashed_password="not-used",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
    )
    doctor_b = models.User(
        username="scope_doctor_b",
        email="scope_doctor_b@test.com",
        hashed_password="not-used",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add_all([doctor_a, doctor_b])
    await db.flush()

    patient_a = models.Patient(
        name="Scoped A",
        age=30,
        phone="01000000101",
        email=None,
        address=None,
        medical_history="",
        notes="",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor_a.id,
    )
    patient_b = models.Patient(
        name="Scoped B",
        age=30,
        phone="01000000102",
        email=None,
        address=None,
        medical_history="",
        notes="",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor_b.id,
    )
    db.add_all([patient_a, patient_b])
    await db.flush()

    for patient, amount in ((patient_a, 100), (patient_b, 200)):
        db.add(
            models.Payment(
                patient_id=patient.id,
                doctor_id=doctor_b.id if patient.id == patient_a.id else doctor_a.id,
                tenant_id=tenant.id,
                amount=amount,
                date=datetime(2026, 8, 17, 12, 0),
            )
        )
    await db.flush()

    rows = await get_today_payments(
        db,
        tenant.id,
        timezone_name=tenant.timezone,
        business_date=date(2026, 8, 17),
        doctor_patient_scope_id=doctor_a.id,
    )
    assert [row["patient_name"] for row in rows] == ["Scoped A"]
    assert rows[0]["amount"] == pytest.approx(100.0)
