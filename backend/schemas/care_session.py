"""
Care Session Schemas (Slices S18 & S19).
Defines request/response models for chairside CareSession lifecycle, steps, and observations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HistoricalStepCreate(BaseModel):
    step_order: Optional[int] = Field(None, description="Display order of step in historical visit")
    step_code: Optional[str] = Field(None, max_length=64, description="Step identifier")
    logical_step_code: Optional[str] = Field(None, max_length=64, description="Procedure-wide semantic logical step identity")
    occurrence_number: Optional[int] = Field(None, ge=1, description="Occurrence number for repeated steps")
    title: str = Field(..., min_length=1, max_length=255, description="Clinical step title or description")
    status: Optional[str] = Field("completed", description="Status of step: completed, in_progress, etc.")
    notes: Optional[str] = Field(None, description="Clinical notes for this step")
    work_item_id: Optional[int] = Field(None, description="Associated work item ID")

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def retain_legacy_code_label(cls, value: Any) -> Any:
        # Older historical callers used an explicit step code as the label.
        if isinstance(value, dict) and value.get("title") is None and isinstance(value.get("step_code"), str):
            return {**value, "title": value["step_code"]}
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Historical step title cannot be blank")
        return value


class HistoricalObservationCreate(BaseModel):
    observation_code: str = Field(default="measurement", min_length=1, max_length=64, description="Observation / measurement key")
    work_item_id: Optional[int] = Field(None, description="Optional clinical work item ID")
    tooth_key: Optional[str] = Field(None, description="Target tooth key in FDI notation (11-48, 51-85)")
    surface_code: Optional[str] = Field(None, description="Target tooth surface (M, O, D, B, L, etc.)")
    root_id: Optional[str] = Field(None, description="Root identifier (e.g. MB, ML, D, P)")
    canal_id: Optional[str] = Field(None, description="Canal identifier (e.g. MB1, MB2)")
    structured_value: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured measurement data")
    notes: Optional[str] = Field(None, description="Free-text clinical notes")

    model_config = ConfigDict(extra="ignore")


class CareSessionCreate(BaseModel):
    appointment_id: Optional[int] = None
    provider_user_id: Optional[int] = Field(None, description="Treating clinician for retrospective documentation")
    notes: Optional[str] = None
    work_item_ids: Optional[List[int]] = Field(default_factory=list, description="Associated clinical work item IDs for this care session")
    resume_work_item_id: Optional[int] = Field(None, description="Optional work item ID to resume in this new session")
    resume_work_item_ids: Optional[List[int]] = Field(default_factory=list, description="Optional list of work item IDs to resume in this new session")
    resume_from_session_id: Optional[int] = Field(None, description="Optional previous care session ID to carry forward steps and observations from")
    actual_visit_date: Optional[datetime] = Field(None, description="Actual visit date/time if distinct from recording time")
    is_historical: bool = Field(False, description="Flag indicating if this is documenting a past historical visit")
    historical_steps: Optional[List[HistoricalStepCreate]] = Field(
        default_factory=list, description="Optional steps performed during historical visit"
    )
    historical_observations: Optional[List[Union[HistoricalObservationCreate, Dict[str, Any]]]] = Field(
        default_factory=list, description="Optional measurements/observations recorded during historical visit"
    )

    model_config = ConfigDict(extra="forbid")


class CareSessionProcedureRead(BaseModel):
    id: int
    tenant_id: int
    care_session_id: int
    work_item_id: int
    notes: Optional[str] = None
    procedure_notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_reason_omitted: Optional[str] = None
    template_code: Optional[str] = None
    template_version: Optional[int] = None
    template_snapshot: Optional[Dict[str, Any]] = None
    work_item_version_id: Optional[int] = None
    work_item_status: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CareSessionAddendumCreate(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    notes: str = Field(..., min_length=1, max_length=20000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("reason", "notes")
    @classmethod
    def reject_blank_addendum(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Addendum text and reason cannot be blank")
        return value


class CareSessionProcedureUpdate(BaseModel):
    procedure_notes: Optional[str] = Field(None, description="Notes specific to this procedure in the visit")
    next_action: Optional[str] = Field(None, description="Next planned clinical action for this procedure")
    next_action_reason_omitted: Optional[str] = Field(None, description="Reason if next action is omitted")

    model_config = ConfigDict(extra="forbid")



# ---------------------------------------------------------------------------
# Appointment Integration & Next-Visit Request Schemas (Slice S22 / G11)
# ---------------------------------------------------------------------------


class CareSessionLinkAppointment(BaseModel):
    appointment_id: Optional[int] = Field(None, description="Appointment ID to link to the care session, or None to unlink")

    model_config = ConfigDict(extra="forbid")


class NextVisitRequestCreate(BaseModel):
    care_session_id: Optional[int] = Field(None, description="Optional care session ID generating this request")
    work_item_id: Optional[int] = Field(None, description="Optional clinical work item ID")
    associated_work_item_ids: Optional[List[int]] = Field(default_factory=list, description="Associated clinical work item IDs")
    assigned_doctor_id: Optional[int] = Field(None, description="Assigned doctor user ID")
    reason: Optional[str] = Field(None, description="Reason for next visit (auto-populated if omitted)")
    suggested_duration_minutes: int = Field(30, ge=5, le=480, description="Suggested appointment duration in minutes")
    preferred_time_window_start: Optional[datetime] = Field(None, description="Preferred window start datetime")
    preferred_time_window_end: Optional[datetime] = Field(None, description="Preferred window end datetime")
    notes: Optional[str] = Field(None, description="Clinical or front-desk instructions/notes")

    model_config = ConfigDict(extra="forbid")


class NextVisitRequestSchedule(BaseModel):
    date_time: datetime = Field(..., description="Scheduled appointment datetime (ISO format)")
    doctor_id: Optional[int] = Field(None, description="Assigned doctor user ID")
    duration_minutes: Optional[int] = Field(None, ge=5, le=480, description="Duration in minutes (defaults to suggested_duration_minutes)")
    price_list_id: Optional[int] = Field(None, description="Optional price list ID")
    notes: Optional[str] = Field(None, description="Appointment notes")

    model_config = ConfigDict(extra="forbid")


class NextVisitRequestStop(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for stopping follow-up reminders")

    model_config = ConfigDict(extra="forbid")


class NextVisitRequestPostpone(BaseModel):
    postponed_to_date: datetime = Field(..., description="New target reminder date")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for postponing follow-up")

    model_config = ConfigDict(extra="forbid")


class NextVisitRequestHandoff(BaseModel):
    handoff_to_user_id: int = Field(..., description="Target doctor user ID")
    reason: str = Field(..., min_length=1, max_length=500, description="Clinical reason for handoff")
    notes: Optional[str] = Field(None, max_length=1000, description="Next tasks and instructions for receiving doctor")

    model_config = ConfigDict(extra="forbid")


class NextVisitRequestRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    care_session_id: Optional[int] = None
    work_item_id: Optional[int] = None
    associated_work_item_ids: Optional[List[int]] = None
    assigned_doctor_id: Optional[int] = None
    requested_by_user_id: Optional[int] = None
    reason: str
    suggested_duration_minutes: int = 30
    preferred_time_window_start: Optional[datetime] = None
    preferred_time_window_end: Optional[datetime] = None
    status: str = "requested"
    notes: Optional[str] = None
    stopped_at: Optional[datetime] = None
    stopped_reason: Optional[str] = None
    stopped_by_user_id: Optional[int] = None
    postponed_to_date: Optional[datetime] = None
    postponed_reason: Optional[str] = None
    postponed_by_user_id: Optional[int] = None
    handoff_at: Optional[datetime] = None
    handoff_reason: Optional[str] = None
    handoff_by_user_id: Optional[int] = None
    handoff_to_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    fulfilled_appointment_id: Optional[int] = None
    assigned_doctor_name: Optional[str] = None
    procedure_name: Optional[str] = None
    due_category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_enriched_fields(cls, data: Any) -> Any:
        import re

        if isinstance(data, dict):
            if not data.get("fulfilled_appointment_id"):
                notes = data.get("notes")
                if notes and isinstance(notes, str):
                    m = re.search(r"\[APPOINTMENT:(\d+)\]", notes)
                    if m:
                        data["fulfilled_appointment_id"] = int(m.group(1))
            return data

        notes = getattr(data, "notes", None)
        if notes and isinstance(notes, str) and not getattr(data, "fulfilled_appointment_id", None):
            m = re.search(r"\[APPOINTMENT:(\d+)\]", notes)
            if m:
                setattr(data, "fulfilled_appointment_id", int(m.group(1)))

        patient = getattr(data, "patient", None)
        if patient:
            if not getattr(data, "patient_name", None):
                setattr(data, "patient_name", getattr(patient, "name", None))
            if not getattr(data, "patient_phone", None):
                setattr(data, "patient_phone", getattr(patient, "phone", None))
        return data


class NextVisitRequestScheduleResult(BaseModel):
    request: NextVisitRequestRead
    appointment_id: int
    appointment_date_time: datetime
    status: str = "scheduled"

    model_config = ConfigDict(from_attributes=True)


class FollowUpDashboardCounts(BaseModel):
    total: int = 0
    requested: int = 0
    overdue: int = 0
    upcoming: int = 0
    unscheduled: int = 0
    postponed: int = 0
    stopped: int = 0
    scheduled: int = 0


class FollowUpDashboardResponse(BaseModel):
    counts: FollowUpDashboardCounts
    items: List[NextVisitRequestRead]
    total_count: int


class NextVisitSuggestionRead(BaseModel):
    reason: str
    suggested_duration_minutes: int = 30
    care_session_id: Optional[int] = None
    work_item_id: Optional[int] = None
    procedure_code: Optional[str] = None
    tooth_key: Optional[str] = None
    next_step_title: Optional[str] = None
    remaining_steps_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CareSessionFinish(BaseModel):
    notes: Optional[str] = None
    next_visit_request: Optional[NextVisitRequestCreate] = Field(
        None, description="Optional chairside next-visit request to create when completing session"
    )
    next_visit_requests: Optional[List[NextVisitRequestCreate]] = Field(
        None, description="Optional multiple chairside next-visit requests"
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_requests(self) -> "CareSessionFinish":
        if self.next_visit_request is not None and self.next_visit_requests is not None:
            raise ValueError("Provide either next_visit_request or next_visit_requests, not both")
        return self



class CareSessionTransition(BaseModel):
    to_status: str = Field(..., description="Target status: paused, in_progress, completed, cancelled")
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CareSessionUpdate(BaseModel):
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Care Session Step Schemas (Slice S19 / G10-M04, G10-M05, G10-M15)
# ---------------------------------------------------------------------------


class CareSessionStepCreate(BaseModel):
    step_code: str = Field(..., min_length=1, max_length=64, description="Step identifier code")
    title: str = Field(..., min_length=1, max_length=255, description="Human-readable step title")
    step_order: Optional[int] = Field(None, ge=1, description="Sequential step order (auto-assigned if omitted)")
    work_item_id: Optional[int] = Field(None, description="Optional associated clinical work item ID")
    logical_step_code: Optional[str] = Field(None, max_length=64, description="Logical step identifier code")
    occurrence_number: Optional[int] = Field(None, ge=1, description="Repetition or occurrence index (auto-computed if omitted)")
    template_step_id: Optional[str] = Field(None, max_length=64, description="Template step reference ID")
    is_repeat: Optional[bool] = Field(False, description="Flag indicating if this step is a repeated action")
    repeat_reason: Optional[str] = Field(None, description="Reason for repeating step")
    status: Optional[str] = Field("pending", description="Initial status: pending, in_progress, partial, completed, skipped")
    notes: Optional[str] = Field(None, description="Free-text clinical notes for this step")

    model_config = ConfigDict(extra="forbid")


class CareSessionStepUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="Target status: pending, in_progress, partial, completed, skipped")
    notes: Optional[str] = Field(None, description="Updated step clinical notes")
    step_order: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(extra="forbid")


class CareSessionStepRead(BaseModel):
    id: int
    tenant_id: int
    care_session_id: int
    work_item_id: Optional[int] = None
    step_order: int
    step_code: str
    logical_step_code: Optional[str] = None
    occurrence_number: int = 1
    template_step_id: Optional[str] = None
    is_repeat: bool = False
    repeat_reason: Optional[str] = None
    title: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    version_id: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



class CareSessionTemplateApply(BaseModel):
    template_code: str = Field(..., min_length=1, max_length=64, description="Workflow template code (e.g. ENDO_RCT, PROS_CROWN)")
    work_item_id: Optional[int] = Field(None, description="Optional clinical work item ID to attach to generated steps")

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Care Observation Schemas (Slice S19 / G10-M07, G10-M15)
# ---------------------------------------------------------------------------


class CareObservationCreate(BaseModel):
    observation_code: str = Field(..., min_length=1, max_length=64, description="Observation / measurement key")
    step_id: Optional[int] = Field(None, description="Optional care session step ID")
    work_item_id: Optional[int] = Field(None, description="Optional clinical work item ID")
    tooth_key: Optional[str] = Field(None, description="Target tooth key in FDI notation (11-48, 51-85)")
    surface_code: Optional[str] = Field(None, description="Target tooth surface (M, O, D, B, L, etc.)")
    root_id: Optional[str] = Field(None, description="Root identifier (e.g. MB, ML, D, P)")
    canal_id: Optional[str] = Field(None, description="Canal identifier (e.g. MB1, MB2)")
    structured_value: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured measurement data")
    notes: Optional[str] = Field(None, description="Free-text clinical notes")

    model_config = ConfigDict(extra="forbid")


class CareObservationRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    care_session_id: int
    step_id: Optional[int] = None
    work_item_id: Optional[int] = None
    observation_code: str
    tooth_key: Optional[str] = None
    surface_code: Optional[str] = None
    root_id: Optional[str] = None
    canal_id: Optional[str] = None
    structured_value: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    recorded_at: Optional[datetime] = None
    recorded_by_user_id: Optional[int] = None
    is_superseded: bool = False
    superseded_by_id: Optional[int] = None
    amendment_reason: Optional[str] = None
    reference_source_session_id: Optional[int] = None
    reference_source_date: Optional[datetime] = None
    reference_source_observation_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_structured_keys(cls, data: Any) -> Any:
        if hasattr(data, "structured_value") and isinstance(data.structured_value, dict):
            sv = data.structured_value or {}
            return {
                "id": data.id,
                "tenant_id": data.tenant_id,
                "patient_id": data.patient_id,
                "care_session_id": data.care_session_id,
                "step_id": data.step_id,
                "work_item_id": data.work_item_id,
                "observation_code": data.observation_code,
                "tooth_key": data.tooth_key,
                "surface_code": sv.get("surface_code"),
                "root_id": sv.get("root_id"),
                "canal_id": sv.get("canal_id"),
                "structured_value": sv,
                "notes": data.notes,
                "recorded_at": data.recorded_at,
                "recorded_by_user_id": data.recorded_by_user_id,
                "is_superseded": getattr(data, "is_superseded", False),
                "superseded_by_id": getattr(data, "superseded_by_id", None),
                "amendment_reason": getattr(data, "amendment_reason", None),
                "reference_source_session_id": getattr(data, "reference_source_session_id", None),
                "reference_source_date": getattr(data, "reference_source_date", None),
                "reference_source_observation_id": getattr(data, "reference_source_observation_id", None),
                "created_at": data.created_at,
            }
        elif isinstance(data, dict):
            sv = data.get("structured_value") or {}
            if "surface_code" not in data and "surface_code" in sv:
                data["surface_code"] = sv["surface_code"]
            if "root_id" not in data and "root_id" in sv:
                data["root_id"] = sv["root_id"]
            if "canal_id" not in data and "canal_id" in sv:
                data["canal_id"] = sv["canal_id"]
        return data


class CareObservationAmend(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for amendment")
    observation_code: Optional[str] = None
    tooth_key: Optional[str] = None
    surface_code: Optional[str] = None
    root_id: Optional[str] = None
    canal_id: Optional[str] = None
    structured_value: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("reason")
    @classmethod
    def reject_blank_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Amendment reason cannot be blank")
        return value


class CareSessionDraftSave(BaseModel):
    draft_data: Dict[str, Any] = Field(..., description="Draft payload containing uncommitted form state")
    expected_version_id: Optional[int] = Field(None, description="Expected draft version ID for optimistic concurrency")
    care_session_id: Optional[int] = Field(None, description="Optional active care session ID")

    model_config = ConfigDict(extra="forbid")


class CareSessionDraftRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    author_user_id: int
    care_session_id: Optional[int] = None
    draft_data: Dict[str, Any] = Field(default_factory=dict)
    draft_payload: Optional[Dict[str, Any]] = None
    version_id: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def map_draft_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "draft_payload" in data and "draft_data" not in data:
                data["draft_data"] = data["draft_payload"]
            return data
        payload = getattr(data, "draft_payload", None)
        if payload is not None and not getattr(data, "draft_data", None):
            return {
                "id": getattr(data, "id", None),
                "tenant_id": getattr(data, "tenant_id", None),
                "patient_id": getattr(data, "patient_id", None),
                "author_user_id": getattr(data, "author_user_id", None),
                "care_session_id": getattr(data, "care_session_id", None),
                "draft_data": payload,
                "draft_payload": payload,
                "version_id": getattr(data, "version_id", 1),
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
            }
        return data


# ---------------------------------------------------------------------------
# Care Session Read Models
# ---------------------------------------------------------------------------


class CareSessionRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    appointment_id: Optional[int] = None
    provider_user_id: Optional[int] = None
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    actual_visit_date: Optional[datetime] = None
    recorded_by_user_id: Optional[int] = None
    is_historical: bool = False
    amends_session_id: Optional[int] = None
    amendment_reason: Optional[str] = None
    notes: Optional[str] = None
    version_id: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    summary: Optional[str] = None
    procedures: List[CareSessionProcedureRead] = Field(default_factory=list)
    steps: List[CareSessionStepRead] = Field(default_factory=list)
    observations: List[CareObservationRead] = Field(default_factory=list)
    next_visit_requests: List[NextVisitRequestRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def handle_unloaded_relationships(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        raw = getattr(data, "_raw", data)
        try:
            from sqlalchemy.inspection import inspect as sa_inspect
            ins = sa_inspect(raw)
            if ins is not None:
                unloaded = ins.unloaded
                return {
                    "id": getattr(data, "id", None),
                    "tenant_id": getattr(data, "tenant_id", None),
                    "patient_id": getattr(data, "patient_id", None),
                    "appointment_id": getattr(data, "appointment_id", None),
                    "provider_user_id": getattr(data, "provider_user_id", None),
                    "status": getattr(data, "status", None),
                    "started_at": getattr(data, "started_at", None),
                    "finished_at": getattr(data, "finished_at", None),
                    "actual_visit_date": getattr(data, "actual_visit_date", None),
                    "recorded_by_user_id": getattr(data, "recorded_by_user_id", None),
                    "is_historical": getattr(data, "is_historical", False),
                    "amends_session_id": getattr(data, "amends_session_id", None),
                    "amendment_reason": getattr(data, "amendment_reason", None),
                    "notes": getattr(data, "notes", None),
                    "version_id": getattr(data, "version_id", 1),
                    "created_at": getattr(data, "created_at", None),
                    "updated_at": getattr(data, "updated_at", None),
                    "summary": getattr(data, "summary", None),
                    "procedures": [] if "procedures" in unloaded else getattr(data, "procedures", []),
                    "steps": [] if "steps" in unloaded else getattr(data, "steps", []),
                    "observations": [] if "observations" in unloaded else getattr(data, "observations", []),
                    "next_visit_requests": [] if "next_visit_requests" in unloaded else getattr(data, "next_visit_requests", []),
                }
        except Exception:
            pass
        return data



# ---------------------------------------------------------------------------
# Care Session Resumable Schemas (Slice S21 / G10-M12, G10-M13)
# ---------------------------------------------------------------------------


class ResumableWorkItemRead(BaseModel):
    work_item_id: int
    procedure_code: str
    tooth_key: Optional[str] = None
    surface_code: Optional[str] = None
    title: str
    status: str
    total_steps: int = 0
    completed_steps_count: int = 0
    completed_steps: List[CareSessionStepRead] = Field(default_factory=list)
    remaining_steps: List[CareSessionStepRead] = Field(default_factory=list)
    observations: List[CareObservationRead] = Field(default_factory=list)
    last_session_id: Optional[int] = None
    last_session_at: Optional[datetime] = None
    last_notes: Optional[str] = None
    summary: Optional[str] = None
    next_step_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CareSessionResumableResponse(BaseModel):
    has_resumable: bool = False
    active_session: Optional[CareSessionRead] = None
    paused_session: Optional[CareSessionRead] = None
    items: List[ResumableWorkItemRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

