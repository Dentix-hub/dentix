"""
Appointments Router
Handles appointment scheduling and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from pydantic import TypeAdapter
from typing import List
import logging

from .. import schemas, crud
from .auth import get_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from backend.core.response import success_response, StandardResponse
from ..utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=StandardResponse[schemas.Appointment],
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
    return success_response(data=crud.create_appointment(db=db, appointment=appointment), message="Appointment created successfully")


@router.get(
    "",
    response_model=StandardResponse[List[schemas.Appointment]],
    summary="List appointments",
    description="Get all appointments for the current tenant. Doctors see only their own.",
)
def read_appointments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    """Get all appointments for current tenant."""
    try:
        doctor_id = current_user.id if current_user.role == "doctor" else None
        results = crud.get_appointments(
            db, current_user.tenant_id, skip=skip, limit=limit, doctor_id=doctor_id
        )
        # Manual validation to catch response model errors during diagnosis
        adapter = TypeAdapter(List[schemas.Appointment])
        validated_results = adapter.validate_python(results)
        return success_response(data=validated_results, message="Appointments retrieved successfully")
    except Exception as e:
        logger.error(f"Failed to fetch appointments: {e}", exc_info=True)
        # Detailed error for diagnosis
        error_msg = str(e)
        if "ValidationError" in type(e).__name__:
             # Extract more info if it's a validation error
             error_msg = f"Validation Error on data: {e}"
        raise HTTPException(status_code=500, detail=f"Failed: {type(e).__name__}: {error_msg}")


@router.put(
    "/{appointment_id}/status",
    summary="Update appointment status",
    description="Change appointment status (e.g. Scheduled → Completed/Cancelled). Requires APPOINTMENT_UPDATE permission.",
)
def update_appointment_status(
    appointment_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_UPDATE)),
):
    """Update appointment status."""
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="update",
        entity_type="appointment",
        entity_id=appointment_id,
        details=f"Status changed to '{status}'",
    )
    try:
        crud.update_appointment_status(
            db, appointment_id, status, current_user.tenant_id
        )
        return success_response(
            data={"appointment_id": appointment_id, "status": status},
            message="Appointment status updated successfully",
        )
    except StaleDataError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="هذا الموعد تم تعديله من مستخدم آخر. يرجى تحديث الصفحة والمحاولة مرة أخرى.",
        )


@router.delete(
    "/{appointment_id}",
    summary="Delete appointment",
    description="Delete an appointment. Logs the action for audit trail. Requires APPOINTMENT_CANCEL permission.",
)
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
    crud.delete_appointment(db, appointment_id, current_user.tenant_id)
    return success_response(
        data={"appointment_id": appointment_id},
        message="Appointment deleted successfully",
    )
