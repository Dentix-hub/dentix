import asyncio
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.core.exceptions import TenantException
from backend.services.cache_service import invalidate_dashboard_cache
from backend.crud.billing import precompute_dashboard_cache
from backend.services.event_service import event_service


async def get_appointments(
    db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100, doctor_id: int = None, return_query: bool = False
):
    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Appointment.is_deleted == False,  # noqa: E712
        )
    )

    if doctor_id:
        stmt = stmt.where(models.Appointment.doctor_id == doctor_id)

    stmt = stmt.options(joinedload(models.Appointment.patient))

    if return_query:
        return stmt

    stmt = (
        stmt.order_by(models.Appointment.date_time.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_appointment(
    db: AsyncSession,
    appointment: schemas.AppointmentCreate,
    tenant_id: int,
):
    # REGRESSION (2026-06-18): Fail-fast if tenant_id is missing.
    # Previously this dropped tenant_id=None into the INSERT, which caused
    # psycopg2.errors.NotNullViolation (actually from RLS policy, since
    # the appointments.tenant_id is technically nullable=True) and surfaced
    # as a 500 to the client. Now we refuse up-front with a clear TenantException.
    if tenant_id is None:
        raise TenantException(
            "tenant_id is required to create an appointment. "
            "Authenticated user must belong to a tenant (super_admin excluded)."
        )

    # Double Booking Prevention
    if appointment.doctor_id:
        # Check if doctor has an appointment at the exact same time
        stmt = (
            select(models.Appointment)
            .where(
                models.Appointment.doctor_id == appointment.doctor_id,
                models.Appointment.date_time == appointment.date_time,
                models.Appointment.is_deleted == False,  # noqa: E712
                models.Appointment.status != "Cancelled",
            )
        )
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            raise ValueError("Doctor is already booked at this time.")

    data = appointment.model_dump()
    data["tenant_id"] = tenant_id
    db_appointment = models.Appointment(**data)
    db.add(db_appointment)
    await db.commit()
    # REGRESSION (2026-06-19): Eager-load patient relationship after commit.
    # The Pydantic response schema declares Appointment.patient and
    # Appointment.patient_name (a Python @property that reads self.patient.name).
    # Accessing either after the route returns (i.e., outside the async
    # greenlet context) raises sqlalchemy.exc.MissingGreenlet. joinedload
    # populates the relationship during the same query so the post-await
    # Pydantic walk has everything it needs.
    await db.refresh(
        db_appointment,
        attribute_names=["patient"],
    )
    # Also explicitly force the patient row's `name` column to load while we
    # still hold the greenlet (the patient_name property reads `self.patient.name`).
    _ = db_appointment.patient.name if db_appointment.patient else None

    # Fetch tenant_id from patient for cache invalidation
    stmt_patient = select(models.Patient).where(models.Patient.id == db_appointment.patient_id)
    result_patient = await db.execute(stmt_patient)
    patient = result_patient.scalars().first()
    if patient:
        invalidate_dashboard_cache(patient.tenant_id)
        asyncio.create_task(
            precompute_dashboard_cache(tenant_id=patient.tenant_id, db=db)
        )
        event_service.emit_event(
            db,
            event_type="appointment.created",
            aggregate_type="appointment",
            aggregate_id=str(db_appointment.id),
            payload={
                "appointment_id": db_appointment.id,
                "patient_id": db_appointment.patient_id,
                "time": db_appointment.date_time.isoformat() if db_appointment.date_time else None,
            },
            tenant_id=patient.tenant_id,
        )
        await db.commit()
    return db_appointment


async def update_appointment_status(
    db: AsyncSession, appointment_id: int, status: str, tenant_id: int
):
    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(
            models.Appointment.id == appointment_id,
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        .options(joinedload(models.Appointment.patient))
    )
    result = await db.execute(stmt)
    db_appt = result.scalars().first()
    if not db_appt or not db_appt.patient or db_appt.patient.tenant_id != tenant_id:
        return None

    db_appt.status = status
    await db.commit()
    await db.refresh(db_appt)
    invalidate_dashboard_cache(tenant_id)
    asyncio.create_task(
        precompute_dashboard_cache(tenant_id=tenant_id, db=db)
    )
    return db_appt


async def delete_appointment(db: AsyncSession, appointment_id: int, tenant_id: int):
    """Soft Delete Appointment."""
    from datetime import datetime, timezone

    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(
            models.Appointment.id == appointment_id,
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        .options(joinedload(models.Appointment.patient))
    )
    result = await db.execute(stmt)
    db_appt = result.scalars().first()
    if not db_appt or not db_appt.patient or db_appt.patient.tenant_id != tenant_id:
        return None

    db_appt.is_deleted = True
    db_appt.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_appt)
    invalidate_dashboard_cache(tenant_id)
    asyncio.create_task(
        precompute_dashboard_cache(tenant_id=tenant_id, db=db)
    )
    return db_appt


async def update_appointment(
    db: AsyncSession, appointment_id: int, appointment: schemas.AppointmentUpdate, tenant_id: int
):
    """Update appointment details."""
    stmt = (
        select(models.Appointment)
        .join(models.Patient)
        .where(
            models.Appointment.id == appointment_id,
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        .options(joinedload(models.Appointment.patient))
    )
    result = await db.execute(stmt)
    db_appt = result.scalars().first()

    if not db_appt or not db_appt.patient or db_appt.patient.tenant_id != tenant_id:
        return None

    update_data = appointment.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_appt, key, value)

    try:
        await db.commit()
        await db.refresh(db_appt)
        invalidate_dashboard_cache(tenant_id)
        asyncio.create_task(
            precompute_dashboard_cache(tenant_id=tenant_id, db=db)
        )
        return db_appt
    except Exception as e:
        await db.rollback()
        raise e
