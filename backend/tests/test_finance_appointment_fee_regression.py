"""Regression test for staff per-appointment compensation aggregation."""

from datetime import datetime, timezone

import pytest

from backend import models
from backend.routers.accounting import get_comprehensive_stats


@pytest.mark.asyncio
async def test_staff_fee_counts_appointments_not_treatment_rows(async_db_session):
    tenant_id = 151
    admin = models.User(
        id=1511,
        username="appointment_fee_admin",
        email="appointment-fee-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    assistant = models.User(
        id=1512,
        username="appointment_fee_assistant",
        email="appointment-fee-assistant@example.com",
        hashed_password="h",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=0.0,
        per_appointment_fee=50.0,
    )
    patient = models.Patient(
        id=1513,
        name="One Visit Two Treatments",
        age=35,
        phone="01015101510",
        medical_history="None",
        notes="Appointment fee regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    appointment = models.Appointment(
        id=1514,
        patient_id=patient.id,
        date_time=datetime(2026, 8, 18, 10, 0),
        status="Scheduled",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    treatment_a = models.Treatment(
        id=1515,
        patient_id=patient.id,
        procedure="Filling A",
        diagnosis="Caries",
        cost=500.0,
        discount=0.0,
        date=datetime(2026, 8, 18, 10, 15, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    treatment_b = models.Treatment(
        id=1516,
        patient_id=patient.id,
        procedure="Filling B",
        diagnosis="Caries",
        cost=500.0,
        discount=0.0,
        date=datetime(2026, 8, 18, 10, 30, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all(
        [admin, assistant, patient, appointment, treatment_a, treatment_b]
    )
    await async_db_session.commit()

    response = await get_comprehensive_stats(
        start_date="2026-08-18",
        end_date="2026-08-18",
        patient_id=None,
        db=async_db_session,
        current_user=admin,
    )
    data = response["data"]
    assert data["income"]["total_appointments"] == 1
    assert data["deductions"]["staff_dues"]["total"] == 50.0
    assert data["deductions"]["staff_dues"]["details"][0]["appointments_in_period"] == 1
