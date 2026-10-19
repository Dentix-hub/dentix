"""
Care Sessions Router (Slice S18).
Endpoints for chairside CareSession lifecycle: start, finish, transition, and queries (G10-M01, G10-M02, G10-M03, G10-M18).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.database import get_async_db
from backend.services.care_session_service import CareSessionService

router = APIRouter(prefix="/patients", tags=["Care Sessions"])


@router.post(
    "/{patient_id}/care-sessions",
    response_model=StandardResponse[schemas.CareSessionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Start care session",
    description="Start a new care session chairside for a patient. Enforces Decision D3: strictly one active session per patient.",
)
async def start_care_session(
    patient_id: int,
    payload: schemas.CareSessionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    session = await service.start_session(patient_id, payload)
    return success_response(
        data=schemas.CareSessionRead.model_validate(session),
        message="Care session started successfully",
    )


@router.post(
    "/{patient_id}/care-sessions/{session_id}/finish",
    response_model=StandardResponse[schemas.CareSessionRead],
    summary="Finish care session",
    description="Complete an active or paused care session and record finished timestamp.",
)
async def finish_care_session(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionFinish,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    session = await service.finish_session(patient_id, session_id, payload)
    return success_response(
        data=schemas.CareSessionRead.model_validate(session),
        message="Care session finished successfully",
    )


@router.post(
    "/{patient_id}/care-sessions/{session_id}/transition",
    response_model=StandardResponse[schemas.CareSessionRead],
    summary="Transition care session status",
    description="Transition care session between allowed lifecycle statuses (pause, resume, cancel).",
)
async def transition_care_session(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionTransition,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    session = await service.transition_session(patient_id, session_id, payload)
    return success_response(
        data=schemas.CareSessionRead.model_validate(session),
        message=f"Care session transitioned to '{payload.to_status}' successfully",
    )


@router.get(
    "/{patient_id}/care-sessions/active",
    response_model=StandardResponse[Optional[schemas.CareSessionRead]],
    summary="Get active care session",
    description="Retrieve the currently active ('in_progress') care session for a patient, if any.",
)
async def get_active_care_session(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    session = await service.get_active_session(patient_id)
    return success_response(
        data=schemas.CareSessionRead.model_validate(session) if session else None,
        message="Active care session retrieved" if session else "No active care session",
    )


@router.get(
    "/{patient_id}/care-sessions/{session_id}",
    response_model=StandardResponse[schemas.CareSessionRead],
    summary="Get care session by ID",
    description="Retrieve details of a specific care session.",
)
async def get_care_session(
    patient_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    session = await service.get_session(patient_id, session_id)
    return success_response(
        data=schemas.CareSessionRead.model_validate(session),
        message="Care session retrieved successfully",
    )


@router.get(
    "/{patient_id}/care-sessions",
    response_model=StandardResponse[List[schemas.CareSessionRead]],
    summary="List patient care sessions",
    description="List all care sessions for a patient with optional status filtering.",
)
async def list_care_sessions(
    patient_id: int,
    status: Optional[str] = Query(None, description="Filter by status (e.g. in_progress, completed, paused, cancelled)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    sessions = await service.list_sessions(patient_id, status=status)
    return success_response(
        data=[schemas.CareSessionRead.model_validate(s) for s in sessions],
        message="Care sessions retrieved successfully",
    )
