import pytest
from sqlalchemy import select
from backend import crud, schemas, models
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_soft_delete_patient(async_db_session):
    tenant_id = 999999

    # 1. Create Patient
    p_data = schemas.PatientCreate(
        name="Soft Delete Test", age=30, phone="ENCRYPTED", medical_history="", notes=""
    )
    patient = await crud.create_patient(async_db_session, p_data, tenant_id)
    assert patient.id is not None
    assert not patient.is_deleted

    # 2. Soft Delete
    await crud.delete_patient(async_db_session, patient.id, tenant_id)

    # 3. Verify
    # Should not find it via get_patient
    deleted = await crud.get_patient(async_db_session, patient.id, tenant_id)
    assert deleted is None

    # But should still exist in DB (Direct Check)
    stmt = select(models.Patient).where(models.Patient.id == patient.id)
    res = await async_db_session.execute(stmt)
    raw_patient = res.scalars().first()
    assert raw_patient.is_deleted
    assert raw_patient.deleted_at is not None


@pytest.mark.asyncio
async def test_soft_delete_appointment(async_db_session):
    tenant_id = 999999

    # Setup Patient
    p_data = schemas.PatientCreate(
        name="Appt Test", age=25, phone="ENC2", medical_history="", notes=""
    )
    patient = await crud.create_patient(async_db_session, p_data, tenant_id)

    # 1. Create Appointment
    appt_time = datetime.now(timezone.utc) + timedelta(days=1)
    a_data = schemas.AppointmentCreate(
        patient_id=patient.id,
        date_time=appt_time,
        doctor_id=1,  # Mock Doctor
        status="Scheduled",
    )
    appt = await crud.create_appointment(async_db_session, a_data, tenant_id=tenant_id)

    # 2. Soft Delete
    await crud.delete_appointment(async_db_session, appt.id, tenant_id)

    # 3. Verify
    # Should be filtered out from list
    appts = await crud.get_appointments(async_db_session, tenant_id)
    ids = [a.id for a in appts]
    assert appt.id not in ids

    # Direct DB Check
    stmt = select(models.Appointment).where(models.Appointment.id == appt.id)
    res = await async_db_session.execute(stmt)
    raw_appt = res.scalars().first()
    assert raw_appt.is_deleted


@pytest.mark.asyncio
async def test_double_booking_prevention(async_db_session):
    tenant_id = 999999
    doctor_id = 500
    slot_time = datetime.now(timezone.utc) + timedelta(days=2)

    p_data = schemas.PatientCreate(
        name="Double Book Test", age=40, phone="ENC3", medical_history="", notes=""
    )
    patient = await crud.create_patient(async_db_session, p_data, tenant_id)

    # 1. First Booking
    a1_data = schemas.AppointmentCreate(
        patient_id=patient.id,
        date_time=slot_time,
        doctor_id=doctor_id,
        status="Scheduled",
    )
    await crud.create_appointment(async_db_session, a1_data, tenant_id=tenant_id)

    # 2. Second Booking (Same Doctor, Same Time)
    a2_data = schemas.AppointmentCreate(
        patient_id=patient.id,
        date_time=slot_time,
        doctor_id=doctor_id,
        status="Scheduled",
    )

    # Expect ValueError
    with pytest.raises(ValueError) as excinfo:
        await crud.create_appointment(async_db_session, a2_data, tenant_id=tenant_id)

    assert "Doctor is already booked at this time" in str(excinfo.value)
