import pytest
from backend import crud, schemas, models
from datetime import datetime, timedelta, timezone

# Using db fixture from conftest.py implicitly


def test_soft_delete_patient(db_session):
    tenant_id = 999999

    # 1. Create Patient
    p_data = schemas.PatientCreate(name="Soft Delete Test", age=30, phone="ENCRYPTED")
    patient = crud.create_patient(db_session, p_data, tenant_id)
    assert patient.id is not None
    assert not patient.is_deleted

    # 2. Soft Delete
    crud.delete_patient(db_session, patient.id, tenant_id)

    # 3. Verify
    # Should not find it via get_patient
    deleted = crud.get_patient(db_session, patient.id, tenant_id)
    assert deleted is None

    # But should still exist in DB (Direct Check)
    raw_patient = (
        db_session.query(models.Patient).filter(models.Patient.id == patient.id).first()
    )
    assert raw_patient.is_deleted
    assert raw_patient.deleted_at is not None


def test_soft_delete_appointment(db_session):
    tenant_id = 999999

    # Setup Patient
    p_data = schemas.PatientCreate(name="Appt Test", age=25, phone="ENC2")
    patient = crud.create_patient(db_session, p_data, tenant_id)

    # 1. Create Appointment
    appt_time = datetime.now(timezone.utc) + timedelta(days=1)
    a_data = schemas.AppointmentCreate(
        patient_id=patient.id,
        date_time=appt_time,
        doctor_id=1,  # Mock Doctor
        status="Scheduled",
    )
    appt = crud.create_appointment(db_session, a_data)

    # 2. Soft Delete
    crud.delete_appointment(db_session, appt.id, tenant_id)

    # 3. Verify
    # Should be filtered out from list
    appts = crud.get_appointments(db_session, tenant_id)
    ids = [a.id for a in appts]
    assert appt.id not in ids

    # Direct DB Check
    raw_appt = (
        db_session.query(models.Appointment).filter(models.Appointment.id == appt.id).first()
    )
    assert raw_appt.is_deleted


def test_double_booking_prevention(db_session):
    tenant_id = 999999
    doctor_id = 500
    slot_time = datetime.now(timezone.utc) + timedelta(days=2)

    p_data = schemas.PatientCreate(name="Double Book Test", age=40, phone="ENC3")
    patient = crud.create_patient(db_session, p_data, tenant_id)

    # 1. First Booking
    a1_data = schemas.AppointmentCreate(
        patient_id=patient.id,
        date_time=slot_time,
        doctor_id=doctor_id,
        status="Scheduled",
    )
    crud.create_appointment(db_session, a1_data)

    # 2. Second Booking (Same Doctor, Same Time)
    a2_data = schemas.AppointmentCreate(
        patient_id=patient.id,
        date_time=slot_time,
        doctor_id=doctor_id,
        status="Scheduled",
    )

    # Expect ValueError
    with pytest.raises(ValueError) as excinfo:
        crud.create_appointment(db_session, a2_data)

    assert "Doctor is already booked at this time" in str(excinfo.value)
