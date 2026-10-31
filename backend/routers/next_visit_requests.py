"""
Next-Visit Requests Router (Slice S25 / G11-M04, G11-M05, G11-M09..M12).
Provides reception triage queue and conversion of chairside follow-up requests into scheduled appointments.
Enforces G11-M08: NEVER auto-books an appointment without explicit front-desk confirmation.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.database import get_async_db
from backend.services.care_session_service import CareSessionService


router = APIRouter(prefix="/next-visit-requests", tags=["Next-Visit Requests"])


class CancelRequestPayload(BaseModel):
    reason: Optional[str] = Field(None, description="Optional cancellation reason")


@router.get(
    "",
    response_model=StandardResponse[List[schemas.NextVisitRequestRead]],
    summary="List reception next-visit requests queue",
    description="Retrieve pending chairside next-visit requests awaiting front-desk triage and scheduling (G11-M04).",
)
async def list_reception_queue(
    status: Optional[str] = Query("requested", description="Filter by status: requested, scheduled, cancelled, completed, or all"),
    patient_id: Optional[int] = Query(None, description="Filter by specific patient ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    requests = await service.list_reception_queue(
        status=status,
        patient_id=patient_id,
        skip=skip,
        limit=limit,
    )
    return success_response(
        data=[schemas.NextVisitRequestRead.model_validate(r) for r in requests],
        message="Next-visit requests queue retrieved successfully",
    )


@router.get(
    "/dashboard",
    response_model=StandardResponse[schemas.FollowUpDashboardResponse],
    summary="Get follow-up dashboard metrics and requests",
    description="Retrieve clinic-wide follow-up requests with metrics, overdue/upcoming classification, and search/filters.",
)
async def get_follow_up_dashboard(
    status: Optional[str] = Query(None, description="Filter by status: requested, scheduled, postponed, stopped, completed, or all"),
    doctor_id: Optional[int] = Query(None, description="Filter by responsible doctor"),
    due_category: Optional[str] = Query(None, description="Filter by due classification: overdue, upcoming, unscheduled, all"),
    date_from: Optional[datetime] = Query(None, description="Filter by target date from"),
    date_to: Optional[datetime] = Query(None, description="Filter by target date to"),
    procedure_code: Optional[str] = Query(None, description="Filter by procedure code"),
    search: Optional[str] = Query(None, description="Search by patient name, phone, or request notes"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    dashboard_data = await service.get_follow_up_dashboard(
        status=status,
        doctor_id=doctor_id,
        due_category=due_category,
        date_from=date_from,
        date_to=date_to,
        procedure_code=procedure_code,
        search=search,
        skip=skip,
        limit=limit,
    )
    return success_response(
        data=dashboard_data,
        message="Follow-up dashboard data retrieved successfully",
    )


@router.post(
    "/{request_id}/schedule",
    response_model=StandardResponse[schemas.NextVisitRequestScheduleResult],
    status_code=status.HTTP_201_CREATED,
    summary="Schedule next-visit request as appointment",
    description="Converts a chairside next-visit request into a confirmed appointment with front-desk action (G11-M05). Enforces G11-M08: never auto-books without user confirmation.",
)
async def schedule_next_visit_request(
    request_id: int,
    payload: schemas.NextVisitRequestSchedule,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_CREATE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req, appt = await service.schedule_next_visit_request(request_id, payload)
    result = schemas.NextVisitRequestScheduleResult(
        request=schemas.NextVisitRequestRead.model_validate(req),
        appointment_id=appt.id,
        appointment_date_time=appt.date_time,
        status="scheduled",
    )
    return success_response(
        data=result,
        message=f"Appointment #{appt.id} scheduled successfully from next-visit request",
    )


@router.post(
    "/{request_id}/cancel",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    summary="Cancel next-visit request",
    description="Dismisses or cancels a pending next-visit request if the patient declines or follow-up is not required.",
)
async def cancel_next_visit_request(
    request_id: int,
    payload: Optional[CancelRequestPayload] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_CANCEL)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    reason = payload.reason if payload else None
    req = await service.cancel_next_visit_request(request_id, reason=reason)
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit request cancelled successfully",
    )


@router.get(
    "/{request_id}",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    summary="Get next-visit request by ID",
    description="Retrieve specific next-visit request details.",
)
async def get_next_visit_request(
    request_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    await service.ensure_native_writes_enabled()

    stmt = (
        select(models.NextVisitRequest)
        .options(selectinload(models.NextVisitRequest.patient))
        .where(
            models.NextVisitRequest.id == request_id,
            models.NextVisitRequest.tenant_id == current_user.tenant_id,
        )
    )
    req = (await db.execute(stmt)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Next-visit request not found")
    await service._verify_patient(req.patient_id)
    if req.patient:
        setattr(req, "patient_name", req.patient.name)
        setattr(req, "patient_phone", req.patient.phone)
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit request retrieved successfully",
    )
