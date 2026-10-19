"""
Care Sessions Router (Slices S18 & S19).
Endpoints for chairside CareSession lifecycle, steps, and observations
(G10-M01, G10-M02, G10-M03, G10-M04, G10-M05, G10-M07, G10-M15, G10-M17, G10-M18).
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


# ---------------------------------------------------------------------------
# Care Session Lifecycle Endpoints (Slice S18)
# ---------------------------------------------------------------------------


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
    description="Complete an active or paused care session, record finished timestamp, and record finalization audit trail.",
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


# ---------------------------------------------------------------------------
# Care Session Step Endpoints (Slice S19 / G10-M04, G10-M05, G10-M15)
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/care-sessions/{session_id}/steps",
    response_model=StandardResponse[schemas.CareSessionStepRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add care session step",
    description="Add an ordered structured step to a care session.",
)
async def add_care_session_step(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionStepCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    step = await service.add_step(patient_id, session_id, payload)
    return success_response(
        data=schemas.CareSessionStepRead.model_validate(step),
        message="Care session step added successfully",
    )


@router.patch(
    "/{patient_id}/care-sessions/{session_id}/steps/{step_id}",
    response_model=StandardResponse[schemas.CareSessionStepRead],
    summary="Update care session step",
    description="Update step status (pending, in_progress, partial, completed, skipped) and preserve free notes.",
)
async def update_care_session_step(
    patient_id: int,
    session_id: int,
    step_id: int,
    payload: schemas.CareSessionStepUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    step = await service.update_step(patient_id, session_id, step_id, payload)
    return success_response(
        data=schemas.CareSessionStepRead.model_validate(step),
        message="Care session step updated successfully",
    )


@router.post(
    "/{patient_id}/care-sessions/{session_id}/steps/from-template",
    response_model=StandardResponse[List[schemas.CareSessionStepRead]],
    status_code=status.HTTP_201_CREATED,
    summary="Initialize care session steps from workflow template",
    description="Populate care session steps from canonical workflow template blueprints (e.g. ENDO_RCT, PROS_CROWN).",
)
async def apply_template_to_care_session(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionTemplateApply,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    steps = await service.apply_template(patient_id, session_id, payload)
    return success_response(
        data=[schemas.CareSessionStepRead.model_validate(s) for s in steps],
        message=f"Applied workflow template '{payload.template_code}' with {len(steps)} steps",
    )


@router.get(
    "/{patient_id}/care-sessions/{session_id}/steps",
    response_model=StandardResponse[List[schemas.CareSessionStepRead]],
    summary="List care session steps",
    description="List ordered structured steps performed within a care session.",
)
async def list_care_session_steps(
    patient_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    steps = await service.list_steps(patient_id, session_id)
    return success_response(
        data=[schemas.CareSessionStepRead.model_validate(s) for s in steps],
        message="Care session steps retrieved successfully",
    )


# ---------------------------------------------------------------------------
# Care Observation Endpoints (Slice S19 / G10-M07, G10-M15)
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/care-sessions/{session_id}/observations",
    response_model=StandardResponse[schemas.CareObservationRead],
    status_code=status.HTTP_201_CREATED,
    summary="Record care observation",
    description="Record structured chairside observation or measurement (canal working lengths, MAF, irrigant, etc.).",
)
async def record_care_observation(
    patient_id: int,
    session_id: int,
    payload: schemas.CareObservationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    obs = await service.add_observation(patient_id, session_id, payload)
    return success_response(
        data=schemas.CareObservationRead.model_validate(obs),
        message="Care observation recorded successfully",
    )


@router.get(
    "/{patient_id}/care-sessions/{session_id}/observations",
    response_model=StandardResponse[List[schemas.CareObservationRead]],
    summary="List care observations",
    description="List observations recorded in a care session with optional step filtering.",
)
async def list_care_observations(
    patient_id: int,
    session_id: int,
    step_id: Optional[int] = Query(None, description="Optional step ID filter"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    observations = await service.list_observations(patient_id, session_id, step_id=step_id)
    return success_response(
        data=[schemas.CareObservationRead.model_validate(o) for o in observations],
        message="Care observations retrieved successfully",
    )


# ---------------------------------------------------------------------------
# Care Session Query Endpoints (Slices S18 & S21 / G10-M12)
# ---------------------------------------------------------------------------


@router.get(
    "/{patient_id}/care-sessions/resumable",
    response_model=StandardResponse[schemas.CareSessionResumableResponse],
    summary="Get resumable care session context",
    description="Retrieve active/paused care session and in-progress procedures with their recorded steps and canal observations for one-click chairside resumption (G10-M12).",
)
async def get_resumable_care_session_context(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    context = await service.get_resumable_context(patient_id)
    return success_response(
        data=schemas.CareSessionResumableResponse.model_validate(context),
        message="Resumable care session context retrieved successfully",
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
    description="Retrieve details of a specific care session, including steps and observations.",
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
