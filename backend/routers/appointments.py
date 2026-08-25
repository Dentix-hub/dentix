"""
Appointments Router
Handles appointment scheduling and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.exc import StaleDataError
from pydantic import TypeAdapter
from typing import List
import os
from datetime import datetime, timezone
import logging

from .. import schemas, crud
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.exceptions import TenantException
from backend.core.limiter import limiter
from backend.core.response import success_response, StandardResponse
from ..utils.audit_logger import log_admin_action
import traceback
from backend.models.system import SystemError, ErrorLevel, ErrorSource
from backend.core.logging_sanitizer import sanitize_text, sanitize_stack_trace

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=StandardResponse[schemas.Appointment],
    status_code=201,
    summary="Create appointment",
    description="Create a new appointment. Rejects patients outside the tenant scope. Doctors can only create for their own schedule.",
)
async def create_appointment(
    request: Request,
    appointment: schemas.AppointmentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_CREATE)),
):
    """Create a new appointment with tenant isolation enforcement."""
    tenant_id = current_user.tenant_id

    # REGRESSION (2026-06-18): Guard at the router boundary too. Belt-and-suspenders:
    # even if auth dependency somehow lets through a user with tenant_id=None,
    # we refuse here with a clear 400 rather than letting it explode as 500
    # from the RLS policy or the underlying INSERT.
    if tenant_id is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot create appointment: authenticated user has no tenant assigned.",
        )

    try:
        patient = await crud.get_patient(db, appointment.patient_id, tenant_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        data = await crud.create_appointment(db=db, appointment=appointment, tenant_id=tenant_id)
        return success_response(data=data, message="Appointment created successfully")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        error_log = SystemError(
            level=ErrorLevel.ERROR,
            source=ErrorSource.BACKEND,
            message=sanitize_text(f"Appointment POST Error: {str(e)}", max_length=4000) or "Appointment Error",
            stack_trace=sanitize_stack_trace(traceback.format_exc(), max_length=12000),
            path=sanitize_text(str(request.url.path), max_length=2048),
            method="POST",
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(error_log)
        await db.commit()
        logger.error("Appointment Creation Failed: %s", sanitize_text(str(e)))
        raise HTTPException(status_code=500, detail="Failed to create appointment")


@router.get(
    "",
    response_model=StandardResponse[List[schemas.Appointment]],
    summary="List appointments",
    description="Get all appointments for the current tenant. Doctors see only their own.",
)
async def read_appointments(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    cursor: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    """Get all appointments for current tenant."""
    try:
        doctor_id = current_user.id if current_user.role == "doctor" else None

        if cursor is not None or limit != 100:
            from backend.core.pagination import CursorParams, apply_cursor_pagination, build_cursor_response
            from backend.core.response import cursor_paginated_response
            from backend import models

            query = await crud.get_appointments(db, current_user.tenant_id, doctor_id=doctor_id, return_query=True)
            cursor_params = CursorParams(cursor=cursor, limit=limit if limit != 100 else 20)

            paginated_query = apply_cursor_pagination(query, models.Appointment, cursor_params, sort_column_name="date_time", descending=True)
            result = await db.execute(paginated_query)
            results = result.scalars().all()

            items, next_cursor, has_more = build_cursor_response(results, cursor_params.limit, sort_column_name="date_time")
            return cursor_paginated_response(
                data=items,
                limit=cursor_params.limit,
                next_cursor=next_cursor,
                has_more=has_more,
                message="Appointments retrieved successfully"
            )
        else:
            results = await crud.get_appointments(
                db, current_user.tenant_id, skip=skip, limit=limit, doctor_id=doctor_id
            )
            return success_response(data=results, message="Appointments retrieved successfully")
    except Exception as e:
        error_log = SystemError(
            level=ErrorLevel.ERROR,
            source=ErrorSource.BACKEND,
            message=sanitize_text(f"Appointment GET Error: {str(e)}", max_length=4000) or "Appointment Error",
            stack_trace=sanitize_stack_trace(traceback.format_exc(), max_length=12000),
            path=sanitize_text(str(request.url.path), max_length=2048),
            method="GET",
            user_id=current_user.id,
            tenant_id=current_user.tenant_id
        )
        db.add(error_log)
        await db.commit()
        logger.error("Appointment Fetch Failed: %s", sanitize_text(str(e)))
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")


@router.get("/debug-errors")
async def get_debug_errors(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Retrieve last 10 system errors for debugging."""
    stmt = select(SystemError).order_by(SystemError.created_at.desc()).limit(10)
    result = await db.execute(stmt)
    errors = result.scalars().all()
    return success_response(data={
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": [
            {
                "id": e.id,
                "message": e.message,
                "stack_trace": e.stack_trace,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "path": e.path,
                "method": e.method
            }
            for e in errors
        ]
    })


@router.put(
    "/{appointment_id}",
    response_model=StandardResponse[schemas.Appointment],
    summary="Update appointment",
    description="Update appointment details. Requires APPOINTMENT_UPDATE permission.",
)
async def update_appointment(
    request: Request,
    appointment_id: int,
    appointment: schemas.AppointmentUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.APPOINTMENT_UPDATE)),
):
    """Update an appointment."""
    try:
        updated = await crud.update_appointment(
            db, appointment_id, appointment, current_user.tenant_id
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return success_response(data=updated, message="Appointment updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Appointment Update Failed: %s", sanitize_text(str(e)))

        try:
            error_log = SystemError(
                level=ErrorLevel.ERROR,
                source=ErrorSource.BACKEND,
                message=sanitize_text(f"Appointment PUT Error: {str(e)}", max_length=4000) or "Appointment Error",
                stack_trace=sanitize_stack_trace(traceback.format_exc(), max_length=12000),
                path=sanitize_text(str(request.url.path), max_length=2048),
                method="PUT",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id
            )
            db.add(error_log)
            await db.commit()
        except Exception as log_e:
            await db.rollback()
            logger.error("Failed to log error to DB: %s", sanitize_text(str(log_e)))

        raise HTTPException(status_code=500, detail="Failed to update appointment")


@router.put(
    "/{appointment_id}/status",
    summary="Update appointment status",
    description="Change appointment status (e.g. Scheduled → Completed/Cancelled). Requires APPOINTMENT_UPDATE permission.",
)
async def update_appointment_status(
    appointment_id: int,
    status: str,
    db: AsyncSession = Depends(get_async_db),
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
        updated = await crud.update_appointment_status(
            db, appointment_id, status, current_user.tenant_id
        )
        if not updated:
            # The audit row was staged before CRUD so successful mutations keep
            # the existing atomic commit behavior. Roll it back when the target
            # does not exist/is not visible rather than returning a false success.
            await db.rollback()
            raise HTTPException(status_code=404, detail="Appointment not found")
        return success_response(
            data={"appointment_id": appointment_id, "status": status},
            message="Appointment status updated successfully",
        )
    except StaleDataError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="هذا الموعد تم تعديله من مستخدم آخر. يرجى تحديث الصفحة والمحاولة مرة أخرى.",
        )


@router.delete(
    "/{appointment_id}",
    summary="Delete appointment",
    description="Delete an appointment. Logs the action for audit trail. Requires APPOINTMENT_CANCEL permission.",
)
async def delete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_async_db),
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
    deleted = await crud.delete_appointment(db, appointment_id, current_user.tenant_id)
    if not deleted:
        # Clear the staged audit entry when no tenant-visible appointment was
        # actually deleted; callers must not receive a false-success response.
        await db.rollback()
        raise HTTPException(status_code=404, detail="Appointment not found")
    return success_response(
        data={"appointment_id": appointment_id},
        message="Appointment deleted successfully",
    )
