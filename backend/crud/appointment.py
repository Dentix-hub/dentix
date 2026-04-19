from sqlalchemy.orm import Session, joinedload
from backend import models, schemas


def get_appointments(
    db: Session, tenant_id: int, skip: int = 0, limit: int = 100, doctor_id: int = None
):
    query = (
        db.query(models.Appointment)
        .join(models.Patient)
        .filter(
            models.Patient.tenant_id == tenant_id,
            not models.Patient.is_deleted,
            not models.Appointment.is_deleted,
        )
    )

    if doctor_id:
        query = query.filter(models.Appointment.doctor_id == doctor_id)

    return (
        query.options(joinedload(models.Appointment.patient))
        .order_by(models.Appointment.date_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_appointment(db: Session, appointment: schemas.AppointmentCreate):
    # Double Booking Prevention
    if appointment.doctor_id:
        # Check if doctor has an appointment at the exact same time
        # We assume 15-30 min slots usually, but strict check on start time is a good first step
        existing = (
            db.query(models.Appointment)
            .filter(
                models.Appointment.doctor_id == appointment.doctor_id,
                models.Appointment.date_time == appointment.date_time,
                not models.Appointment.is_deleted,
                models.Appointment.status != "Cancelled",
            )
            .first()
        )

        if existing:
            raise ValueError("Doctor is already booked at this time.")

    db_appointment = models.Appointment(**appointment.dict())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def update_appointment_status(
    db: Session, appointment_id: int, status: str, tenant_id: int
):
    db_appt = (
        db.query(models.Appointment)
        .join(models.Patient)
        .filter(
            models.Appointment.id == appointment_id,
            models.Patient.tenant_id == tenant_id,
            not models.Appointment.is_deleted,
        )
        .first()
    )
    if db_appt:
        db_appt.status = status
        db.commit()
        db.refresh(db_appt)
    return db_appt


def delete_appointment(db: Session, appointment_id: int, tenant_id: int):
    """Soft Delete Appointment."""
    from datetime import datetime

    db_appt = (
        db.query(models.Appointment)
        .join(models.Patient)
        .filter(
            models.Appointment.id == appointment_id,
            models.Patient.tenant_id == tenant_id,
            not models.Appointment.is_deleted,
        )
        .first()
    )
    if db_appt:
        db_appt.is_deleted = True
        db_appt.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(db_appt)
    return db_appt
