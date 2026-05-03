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
import traceback
from backend.models.system import SystemError, ErrorLevel, ErrorSource

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
    try:
        patient = crud.get_patient(db, appointment.patient_id, current_user.tenant_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        data = crud.create_appointment(db=db, appointment=appointment)
        return success_response(data=data, message="Appointment created successfully")
    except Exception as e:
        db.rollback()
        error_log = SystemError(
            level=ErrorLevel.ERROR,
            source=ErrorSource.BACKEND,
            message=f"Appointment POST Error: {str(e)}",
            stack_trace=traceback.format_exc(),
            path=str(request.url.path),
            method="POST",
            user_id=current_user.id,
            tenant_id=current_user.tenant_id
        )
        db.add(error_log)
        db.commit()
        logger.error(f"Appointment Creation Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=StandardResponse[List[schemas.Appointment]],
    summary="List appointments",
    description="Get all appointments for the current tenant. Doctors see only their own.",
)
def read_appointments(
    request: Request,
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
        return success_response(data=results, message="Appointments retrieved successfully")
    except Exception as e:
        error_log = SystemError(
            level=ErrorLevel.ERROR,
            source=ErrorSource.BACKEND,
            message=f"Appointment GET Error: {str(e)}",
            stack_trace=traceback.format_exc(),
            path=str(request.url.path),
            method="GET",
            user_id=current_user.id,
            tenant_id=current_user.tenant_id
        )
        db.add(error_log)
        db.commit()
        logger.error(f"Appointment Fetch Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{appointment_id}",
    response_model=StandardResponse[schemas.Appointment],
    summary="Update appointment",
    description="Update appointment details like time, notes, or doctor. Requires APPOINTMENT_UPDATE permission.",
)
def update_appointment(
    request: Request,
    appointment_id: int,
    appointment: schemas.AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_UPDATE)),
):
    """Update an appointment."""
    try:
        updated = crud.update_appointment(
            db, appointment_id, appointment, current_user.tenant_id
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return success_response(data=updated, message="Appointment updated successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Appointment Update Failed: {str(e)}\n{traceback.format_exc()}")
        
        try:
            error_log = SystemError(
                level=ErrorLevel.ERROR,
                source=ErrorSource.BACKEND,
                message=f"Appointment PUT Error: {str(e)}",
                stack_trace=traceback.format_exc(),
                path=str(request.url.path),
                method="PUT",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id
            )
            db.add(error_log)
            db.commit()
        except Exception as log_e:
            db.rollback()
            logger.error(f"Failed to log error to DB: {str(log_e)}")
            
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")


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
