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
from backend.services.care_session_material_service import CareSessionMaterialService
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
# Care Session Procedures & Workspace Operations (Requirement 1 & 3)
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/care-sessions/{session_id}/procedures/{work_item_id}",
    response_model=StandardResponse[schemas.CareSessionProcedureRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add procedure to active care session",
    description="Associate an active procedure with an in-progress care session and populate its template snapshot.",
)
async def add_procedure_to_care_session(
    patient_id: int,
    session_id: int,
    work_item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    proc = await service.add_procedure_to_session(patient_id, session_id, work_item_id)
    return success_response(
        data=schemas.CareSessionProcedureRead.model_validate(proc),
        message="Procedure associated with care session successfully",
    )


@router.delete(
    "/{patient_id}/care-sessions/{session_id}/procedures/{work_item_id}",
    response_model=StandardResponse[bool],
    summary="Remove procedure from care session",
    description="Remove an unworked procedure selected accidentally from the visit without deleting the procedure itself.",
)
async def remove_procedure_from_care_session(
    patient_id: int,
    session_id: int,
    work_item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    removed = await service.remove_procedure_from_session(patient_id, session_id, work_item_id)
    return success_response(
        data=removed,
        message="Procedure removed from care session",
    )


@router.patch(
    "/{patient_id}/care-sessions/{session_id}/procedures/{work_item_id}",
    response_model=StandardResponse[schemas.CareSessionProcedureRead],
    summary="Update care session procedure notes and next action",
    description="Save procedure-specific notes and next action within the active visit.",
)
async def update_care_session_procedure(
    patient_id: int,
    session_id: int,
    work_item_id: int,
    payload: schemas.CareSessionProcedureUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    proc = await service.update_session_procedure(patient_id, session_id, work_item_id, payload)
    return success_response(
        data=schemas.CareSessionProcedureRead.model_validate(proc),
        message="Procedure details updated successfully",
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
    include_superseded: bool = Query(False, description="Whether to include superseded observation amendments"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    observations = await service.list_observations(
        patient_id, session_id, step_id=step_id, include_superseded=include_superseded
    )
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


# ---------------------------------------------------------------------------
# Server Drafts Endpoints (Section 2.6 - declared before dynamic {session_id} to avoid route shadowing)
# ---------------------------------------------------------------------------


@router.put(
    "/{patient_id}/care-sessions/draft",
    response_model=StandardResponse[schemas.CareSessionDraftRead],
    summary="Save care session draft",
    description="Autosave chairside visit documentation draft with optimistic concurrency control.",
)
async def save_care_session_draft(
    patient_id: int,
    payload: schemas.CareSessionDraftSave,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    draft = await service.save_draft(patient_id, payload)
    return success_response(
        data=schemas.CareSessionDraftRead.model_validate(draft),
        message="Care session draft saved successfully",
    )


@router.get(
    "/{patient_id}/care-sessions/draft",
    response_model=StandardResponse[Optional[schemas.CareSessionDraftRead]],
    summary="Recover care session draft",
    description="Recover editable documentation draft for current author on this patient.",
)
async def get_care_session_draft(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    draft = await service.get_draft(patient_id)
    return success_response(
        data=schemas.CareSessionDraftRead.model_validate(draft) if draft else None,
        message="Care session draft recovered" if draft else "No draft found",
    )


@router.delete(
    "/{patient_id}/care-sessions/draft",
    response_model=StandardResponse[bool],
    summary="Discard care session draft",
    description="Clear saved draft after successful finalization or author discard.",
)
async def delete_care_session_draft(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    deleted = await service.delete_draft(patient_id)
    return success_response(
        data=deleted,
        message="Draft discarded successfully" if deleted else "No draft to discard",
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


# ---------------------------------------------------------------------------
# Appointment Integration & Next-Visit Request Endpoints (Slice S22 / G11)
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/care-sessions/{session_id}/link-appointment",
    response_model=StandardResponse[schemas.CareSessionRead],
    summary="Link session to appointment",
    description="Link or unlink a care session to an existing appointment (G11-M01).",
)
async def link_care_session_appointment(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionLinkAppointment,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    session = await service.link_appointment(patient_id, session_id, payload.appointment_id)
    return success_response(
        data=schemas.CareSessionRead.model_validate(session),
        message="Appointment linked to care session successfully" if payload.appointment_id else "Appointment unlinked from care session",
    )


@router.get(
    "/{patient_id}/care-sessions/{session_id}/suggest-next-visit",
    response_model=StandardResponse[schemas.NextVisitSuggestionRead],
    summary="Suggest next visit reason and duration",
    description="Auto-suggest appointment reason and duration based on remaining steps and procedure (G11-M06, G11-M07).",
)
async def suggest_next_visit(
    patient_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    suggestion = await service.suggest_next_visit(patient_id, session_id=session_id)
    return success_response(
        data=schemas.NextVisitSuggestionRead.model_validate(suggestion),
        message="Next visit suggestion generated successfully",
    )


@router.post(
    "/{patient_id}/care-sessions/{session_id}/next-visit-requests",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create chairside next-visit request from session",
    description="Create next-visit request linked to an active/finished care session (G11-M02). Enforces G11-M08: never auto-books an appointment.",
)
async def create_care_session_next_visit_request(
    patient_id: int,
    session_id: int,
    payload: schemas.NextVisitRequestCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req = await service.create_next_visit_request(patient_id, payload, session_id=session_id)
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit request created successfully",
    )


@router.get(
    "/{patient_id}/care-sessions/{session_id}/next-visit-requests",
    response_model=StandardResponse[List[schemas.NextVisitRequestRead]],
    summary="List care session next-visit requests",
    description="List next-visit requests generated from a specific care session.",
)
async def list_care_session_next_visit_requests(
    patient_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    requests = await service.list_next_visit_requests(patient_id, session_id=session_id)
    return success_response(
        data=[schemas.NextVisitRequestRead.model_validate(r) for r in requests],
        message="Next-visit requests retrieved successfully",
    )


@router.post(
    "/{patient_id}/next-visit-requests",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create patient next-visit request",
    description="Create chairside next-visit request for reception triage (G11-M02). Enforces G11-M08: never auto-books.",
)
async def create_patient_next_visit_request(
    patient_id: int,
    payload: schemas.NextVisitRequestCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req = await service.create_next_visit_request(patient_id, payload)
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit request created successfully",
    )


@router.get(
    "/{patient_id}/next-visit-requests",
    response_model=StandardResponse[List[schemas.NextVisitRequestRead]],
    summary="List patient next-visit requests",
    description="List all next-visit requests for a patient with optional status filtering.",
)
async def list_patient_next_visit_requests(
    patient_id: int,
    status: Optional[str] = Query(None, description="Optional status filter (e.g. requested, scheduled, cancelled)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    requests = await service.list_next_visit_requests(patient_id, status=status)
    return success_response(
        data=[schemas.NextVisitRequestRead.model_validate(r) for r in requests],
        message="Patient next-visit requests retrieved successfully",
    )


@router.post(
    "/{patient_id}/next-visit-requests/{request_id}/stop",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    summary="Stop next-visit follow-up",
    description="Stop active next-visit reminders with an explicit recorded reason (audited).",
)
async def stop_patient_next_visit_request(
    patient_id: int,
    request_id: int,
    payload: schemas.NextVisitRequestStop,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req = await service.stop_next_visit_request(request_id, payload.reason, patient_id=patient_id)
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit follow-up stopped successfully",
    )


@router.post(
    "/{patient_id}/next-visit-requests/{request_id}/postpone",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    summary="Postpone next-visit follow-up",
    description="Postpone a next-visit reminder with a reason and new target date (audited).",
)
async def postpone_patient_next_visit_request(
    patient_id: int,
    request_id: int,
    payload: schemas.NextVisitRequestPostpone,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req = await service.postpone_next_visit_request(
        request_id, payload.postponed_to_date, payload.reason, patient_id=patient_id
    )
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit follow-up postponed successfully",
    )


@router.post(
    "/{patient_id}/next-visit-requests/{request_id}/resume",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    summary="Resume next-visit follow-up",
    description="Resume follow-up reminders that were previously stopped or postponed (audited).",
)
async def resume_patient_next_visit_request(
    patient_id: int,
    request_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req = await service.resume_next_visit_request(request_id, patient_id=patient_id)
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit follow-up resumed successfully",
    )


@router.post(
    "/{patient_id}/next-visit-requests/{request_id}/handoff",
    response_model=StandardResponse[schemas.NextVisitRequestRead],
    summary="Handoff next-visit follow-up",
    description="Transfer follow-up responsibility to another clinic doctor (audited).",
)
async def handoff_patient_next_visit_request(
    patient_id: int,
    request_id: int,
    payload: schemas.NextVisitRequestHandoff,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    req = await service.handoff_next_visit_request(
        request_id, payload.handoff_to_user_id, payload.reason, payload.notes, patient_id=patient_id
    )
    return success_response(
        data=schemas.NextVisitRequestRead.model_validate(req),
        message="Next-visit follow-up handed off successfully",
    )


# ---------------------------------------------------------------------------
# Observation Amendments (Section 2.7)
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/care-sessions/{session_id}/observations/{observation_id}/amend",
    response_model=StandardResponse[schemas.CareObservationRead],
    summary="Amend care observation",
    description="Traceably amend a chairside observation / measurement, preserving the original record and recording audit event.",
)
async def amend_care_observation(
    patient_id: int,
    session_id: int,
    observation_id: int,
    payload: schemas.CareObservationAmend,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    new_obs = await service.amend_observation(patient_id, observation_id, payload, session_id=session_id)
    return success_response(
        data=schemas.CareObservationRead.model_validate(new_obs),
        message="Observation amended successfully",
    )



@router.post(
    "/{patient_id}/care-sessions/{session_id}/addenda",
    response_model=StandardResponse[schemas.CareSessionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Append a traceable correction to completed visit notes",
)
async def add_care_session_addendum(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionAddendumCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionService(db, current_user.tenant_id, current_user)
    result = await service.add_session_addendum(patient_id, session_id, payload)
    return success_response(data=schemas.CareSessionRead.model_validate(result), message="Visit addendum recorded")


# ---------------------------------------------------------------------------
# Point-of-Care Materials (Slice S30 / G13-M04, G13-M06, G13-M07, G13-M09)
# ---------------------------------------------------------------------------


@router.get(
    "/{patient_id}/clinical-work-items/{work_item_id}/material-suggestions",
    response_model=StandardResponse[schemas.MaterialSuggestionResponse],
    summary="Suggest materials for a work item",
    description="Read-only material suggestions by canonical procedure code (G13-M04). Deducts nothing (G13-M05).",
)
async def suggest_work_item_materials(
    patient_id: int,
    work_item_id: int,
    step_code: Optional[str] = Query(None, description="Optional workflow step code (echoed)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionMaterialService(db, current_user.tenant_id, current_user)
    result = await service.suggest_materials(patient_id, work_item_id, step_code)
    return success_response(data=result, message="Material suggestions retrieved successfully")


@router.post(
    "/{patient_id}/care-sessions/{session_id}/material-usages",
    response_model=StandardResponse[List[schemas.CareSessionMaterialUsageRead]],
    status_code=status.HTTP_201_CREATED,
    summary="Record care session material usage",
    description="Deduct stock at the point of use and record TreatmentMaterialUsage linked to the care session (G13-M06/M07). Single transaction; no partial deduction.",
)
async def record_care_session_materials(
    patient_id: int,
    session_id: int,
    payload: schemas.CareSessionMaterialUsageCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = CareSessionMaterialService(db, current_user.tenant_id, current_user)
    usages = await service.record_material_usage(patient_id, session_id, payload)
    return success_response(
        data=await service.to_usage_reads(usages),
        message="Care session materials recorded successfully",
    )


@router.get(
    "/{patient_id}/clinical-work-items/{work_item_id}/material-cost",
    response_model=StandardResponse[schemas.WorkItemMaterialCostRead],
    summary="Aggregate work item material cost",
    description="Material usage and cost aggregated across all care sessions of a work item (G13-M09).",
)
async def get_work_item_material_cost(
    patient_id: int,
    work_item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = CareSessionMaterialService(db, current_user.tenant_id, current_user)
    result = await service.get_work_item_material_cost(patient_id, work_item_id)
    return success_response(data=result, message="Work item material cost retrieved successfully")
