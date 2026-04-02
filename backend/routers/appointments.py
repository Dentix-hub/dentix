"""
Appointments Router
Handles appointment scheduling and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import logging

from .. import schemas, crud
from .auth import get_current_user, get_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from ..utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "/",
    response_model=schemas.Appointment,
    summary="Create appointment",
    description="Schedule a new appointment for a patient. Validates patient existence.",
)
@limiter.limit("15/minute")
def create_appointment(
    request: Request,
    appointment: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_CREATE)),
):
    """Create a new appointment."""
    patient = crud.get_patient(db, appointment.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.create_appointment(db=db, appointment=appointment)


@router.get(
    "/",
    response_model=List[schemas.Appointment],
    summary="List appointments",
    description="Get all appointments for the current tenant. Doctors see only their own.",
)
def read_appointments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all appointments for current tenant."""
    try:
        doctor_id = current_user.id if current_user.role == "doctor" else None
        return crud.get_appointments(
            db, current_user.tenant_id, skip=skip, limit=limit, doctor_id=doctor_id
        )
    except Exception as e:
        logger.error(f"Failed to fetch appointments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve appointments")


@router.put("/{appointment_id}/status")
def update_appointment_status(
    appointment_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_UPDATE)),
):
    """Update appointment status."""
    from sqlalchemy.orm.exc import StaleDataError

    log_admin_action(
        db=db,
        admin_user=current_user,
        action="update",
        entity_type="appointment",
        entity_id=appointment_id,
        details=f"Status changed to '{status}'",
    )
    try:
        return crud.update_appointment_status(
            db, appointment_id, status, current_user.tenant_id
        )
    except StaleDataError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="هذا الموعد تم تعديله من مستخدم آخر. يرجى تحديث الصفحة والمحاولة مرة أخرى.",
        )


@router.delete("/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_CANCEL)),
):
    """Delete an appointment."""
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="appointment",
        entity_id=appointment_id,
        details=f"Deleted appointment #{appointment_id}",
    )
    return crud.delete_appointment(db, appointment_id, current_user.tenant_id)
