"""Cancelled appointments must not create staff per-appointment dues."""

from datetime import datetime

import pytest

from backend import models
from backend.routers.accounting import get_comprehensive_stats


@pytest.mark.asyncio
async def test_cancelled_appointment_is_excluded_from_staff_fee(async_db_session):
    tenant_id = 153
    admin = models.User(
        id=1531,
        username="cancel_fee_admin",
        email="cancel-fee-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    assistant = models.User(
        id=1532,
        username="cancel_fee_assistant",
        email="cancel-fee-assistant@example.com",
        hashed_password="h",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=0.0,
        per_appointment_fee=50.0,
    )
    patient = models.Patient(
        id=1533,
        name="Cancelled Visit Patient",
        age=35,
        phone="01015301530",
        medical_history="None",
        notes="Cancelled appointment regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    scheduled = models.Appointment(
        id=1534,
        patient_id=patient.id,
        date_time=datetime(2026, 8, 18, 10, 0),
        status="Scheduled",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    cancelled = models.Appointment(
        id=1535,
        patient_id=patient.id,
        date_time=datetime(2026, 8, 18, 11, 0),
        status="Cancelled",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all([admin, assistant, patient, scheduled, cancelled])
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
