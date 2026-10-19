"""
Care Session Schemas (Slices S18 & S19).
Defines request/response models for chairside CareSession lifecycle, steps, and observations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CareSessionCreate(BaseModel):
    appointment_id: Optional[int] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CareSessionFinish(BaseModel):
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


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
    notes: Optional[str] = None
    version_id: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    steps: List[CareSessionStepRead] = Field(default_factory=list)
    observations: List[CareObservationRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def handle_unloaded_relationships(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        try:
            from sqlalchemy.inspection import inspect as sa_inspect
            ins = sa_inspect(data)
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
                    "notes": getattr(data, "notes", None),
                    "version_id": getattr(data, "version_id", 1),
                    "created_at": getattr(data, "created_at", None),
                    "updated_at": getattr(data, "updated_at", None),
                    "steps": [] if "steps" in unloaded else getattr(data, "steps", []),
                    "observations": [] if "observations" in unloaded else getattr(data, "observations", []),
                }
        except Exception:
            pass
        return data
