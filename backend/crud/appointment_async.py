"""
Async Appointment CRUD Operations

Mirrors the synchronous appointment.py CRUD but uses AsyncSession and SQLAlchemy 2.0 patterns.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend import models, schemas


async def get_appointments(
    db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100
):
    """Get all appointments for a tenant with patient eager loading."""
    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(models.Patient.tenant_id == tenant_id)
        .options(selectinload(models.Appointment.patient))
        .order_by(models.Appointment.date_time.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_appointment(db: AsyncSession, appointment_id: int, tenant_id: int):
    """Get a single appointment by ID with tenant isolation."""
    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(
            models.Appointment.id == appointment_id,
            models.Patient.tenant_id == tenant_id,
        )
        .options(selectinload(models.Appointment.patient))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_appointment(db: AsyncSession, appointment: schemas.AppointmentCreate):
    """Create a new appointment."""
    db_appointment = models.Appointment(**appointment.model_dump())
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    return db_appointment


async def update_appointment_status(
    db: AsyncSession, appointment_id: int, status: str, tenant_id: int
):
    """Update appointment status."""
    db_appt = await get_appointment(db, appointment_id, tenant_id)
    if db_appt:
        db_appt.status = status
        await db.commit()
        await db.refresh(db_appt)
    return db_appt


async def delete_appointment(db: AsyncSession, appointment_id: int, tenant_id: int):
    """Delete an appointment."""
    db_appt = await get_appointment(db, appointment_id, tenant_id)
    if db_appt:
        await db.delete(db_appt)
        await db.commit()
    return db_appt


async def get_appointments_by_date(db: AsyncSession, date_str: str, tenant_id: int):
    """Get appointments for a specific date."""
    from datetime import datetime

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Appointment.date_time
            >= datetime.combine(target_date, datetime.min.time()),
            models.Appointment.date_time
            < datetime.combine(target_date, datetime.max.time()),
        )
        .options(selectinload(models.Appointment.patient))
        .order_by(models.Appointment.date_time)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
