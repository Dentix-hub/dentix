from sqlalchemy.orm import Session, joinedload
from backend import models, schemas
from backend.services.cache_service import invalidate_dashboard_cache


def get_appointments(
    db: Session, tenant_id: int, skip: int = 0, limit: int = 100, doctor_id: int = None
):
    query = (
        db.query(models.Appointment)
        .join(models.Patient)
        .filter(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Appointment.is_deleted == False,  # noqa: E712
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
                models.Appointment.is_deleted == False,  # noqa: E712
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
    # Fetch tenant_id from patient for cache invalidation
    patient = db.query(models.Patient).filter(models.Patient.id == db_appointment.patient_id).first()
    if patient:
        invalidate_dashboard_cache(patient.tenant_id)
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
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if db_appt:
        db_appt.status = status
        db.commit()
        db.refresh(db_appt)
        invalidate_dashboard_cache(tenant_id)
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
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if db_appt:
        db_appt.is_deleted = True
        from datetime import timezone
        db_appt.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_appt)
        invalidate_dashboard_cache(tenant_id)
    return db_appt
