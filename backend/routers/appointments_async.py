"""
Async Appointments Router (v2)
Handles appointment scheduling and management using async database operations.

This is the async version of appointments.py for gradual migration.
Mount under /v2/appointments or replace original once tested.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas
from ..crud import appointment_async as crud
from ..crud import patient_async as patient_crud
from ..database import get_async_db
from .auth import get_current_user

router = APIRouter(prefix="/appointments", tags=["Appointments (Async)"])


@router.post("/", response_model=schemas.Appointment)
async def create_appointment(
    appointment: schemas.AppointmentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new appointment."""
    patient = await patient_crud.get_patient(db, appointment.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return await crud.create_appointment(db=db, appointment=appointment)


@router.get("/", response_model=List[schemas.Appointment])
async def read_appointments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all appointments for current tenant."""
    return await crud.get_appointments(db, current_user.tenant_id, skip=skip, limit=limit)


@router.get("/{appointment_id}", response_model=schemas.Appointment)
async def read_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific appointment by ID."""
    result = await crud.get_appointment(db, appointment_id, current_user.tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


@router.put("/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    status: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Update appointment status."""
    result = await crud.update_appointment_status(
        db, appointment_id, status, current_user.tenant_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete an appointment."""
    result = await crud.delete_appointment(db, appointment_id, current_user.tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Appointment deleted"}


@router.get("/by-date/{date_str}", response_model=List[schemas.Appointment])
async def get_appointments_by_date(
    date_str: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get appointments for a specific date (YYYY-MM-DD format)."""
    return await crud.get_appointments_by_date(db, date_str, current_user.tenant_id)
