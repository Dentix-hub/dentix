"""
Clinical Commands Schemas (Slice S04).
Defines request/response models for native clinical work item mutations and queries.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.clinical.catalog import (
    CANONICAL_FINDING_CODES,
    CANONICAL_PROCEDURE_CODES,
    validate_treatment_status,
)
from backend.models.clinical_core import (
    FDI_TOOTH_KEYS,
    ROOT_IDS,
    SURFACE_CODES,
    TARGET_KINDS,
)
from backend.schemas.clinical import ToothStatus, Treatment
from backend.schemas.clinical_workspace import WorkspaceToothSummary


def validate_target_shape(
    target_kind: str,
    tooth_key: str,
    surface_code: Optional[str] = None,
    root_id: Optional[str] = None,
    canal_id: Optional[str] = None,
) -> None:
    """Validate anatomical target shape against TARGET_SHAPE_CONSTRAINT and FDI rules."""
    if target_kind not in TARGET_KINDS:
        raise ValueError(f"Invalid target_kind '{target_kind}'. Allowed: {TARGET_KINDS}")
    if tooth_key not in FDI_TOOTH_KEYS:
        raise ValueError(f"Invalid tooth_key '{tooth_key}'. Must be a valid FDI 2-digit tooth key.")

    if target_kind == "tooth":
        if surface_code is not None or root_id is not None or canal_id is not None:
            raise ValueError("Target kind 'tooth' requires surface_code, root_id, and canal_id to be NULL")
    elif target_kind == "surface":
        if surface_code is None or root_id is not None or canal_id is not None:
            raise ValueError("Target kind 'surface' requires surface_code to be set and root_id, canal_id to be NULL")
        if surface_code not in SURFACE_CODES:
            raise ValueError(f"Invalid surface_code '{surface_code}'. Allowed: {SURFACE_CODES}")
    elif target_kind == "root":
        if surface_code is not None or root_id is None or canal_id is not None:
            raise ValueError("Target kind 'root' requires root_id to be set and surface_code, canal_id to be NULL")
        if root_id not in ROOT_IDS:
            raise ValueError(f"Invalid root_id '{root_id}'. Allowed: {ROOT_IDS}")
    elif target_kind == "canal":
        if surface_code is not None or root_id is None:
            raise ValueError("Target kind 'canal' requires root_id to be set and surface_code to be NULL")
        if root_id not in ROOT_IDS:
            raise ValueError(f"Invalid root_id '{root_id}'. Allowed: {ROOT_IDS}")
        if canal_id is not None and len(canal_id.strip()) == 0:
            raise ValueError("Target kind 'canal' canal_id cannot be an empty string if provided")


class ClinicalTargetInput(BaseModel):
    target_kind: str
    tooth_key: str
    surface_code: Optional[str] = None
    root_id: Optional[str] = None
    canal_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ClinicalTargetRead(BaseModel):
    id: int
    target_kind: str
    tooth_key: str
    surface_code: Optional[str] = None
    root_id: Optional[str] = None
    canal_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalWorkItemCreate(BaseModel):
    kind: str
    code: str
    status: str = "proposed"
    notes: Optional[str] = None
    targets: List[ClinicalTargetInput] = Field(default_factory=list)
    idempotency_key: Optional[str] = Field(None, max_length=128)

    model_config = ConfigDict(extra="forbid")


class ClinicalWorkItemUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    targets: Optional[List[ClinicalTargetInput]] = None
    expected_version_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")



class ClinicalWorkItemRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    kind: str
    code: str
    status: str
    notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    version_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    targets: List[ClinicalTargetRead] = Field(default_factory=list)
    # G12-M11: Read-only lab order indicator & sync metadata
    lab_order_id: Optional[int] = None
    lab_status: Optional[str] = None
    lab_ready: bool = False
    shade: Optional[str] = None
    material: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalFindingCreate(BaseModel):
    code: str
    status: str = "proposed"
    notes: Optional[str] = None
    targets: List[ClinicalTargetInput] = Field(default_factory=list)
    tooth_key: Optional[str] = None
    surfaces: Optional[List[str]] = None
    surface: Optional[str] = None
    surface_code: Optional[str] = None
    severity: Optional[str] = None
    idempotency_key: Optional[str] = Field(None, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def populate_targets(self) -> "ClinicalFindingCreate":
        if not self.targets and self.tooth_key:
            surfs = []
            if self.surfaces:
                surfs = [s.strip().upper() for s in self.surfaces if s.strip()]
            elif self.surface:
                surfs = [c.upper() for c in self.surface.replace(",", "").replace(" ", "").strip() if c.strip()]
            elif self.surface_code:
                surfs = [self.surface_code.strip().upper()]

            if surfs:
                for s in surfs:
                    self.targets.append(
                        ClinicalTargetInput(
                            target_kind="surface",
                            tooth_key=str(self.tooth_key),
                            surface_code=s,
                        )
                    )
            else:
                self.targets.append(
                    ClinicalTargetInput(
                        target_kind="tooth",
                        tooth_key=str(self.tooth_key),
                    )
                )
        return self


class ClinicalFindingBulkCreate(BaseModel):
    items: List[ClinicalFindingCreate] = Field(..., min_length=1, max_length=50)
    idempotency_key: Optional[str] = Field(None, max_length=128)

    model_config = ConfigDict(extra="forbid")


class ClinicalProcedureCreate(BaseModel):
    code: str
    status: str = "proposed"
    notes: Optional[str] = None
    targets: List[ClinicalTargetInput] = Field(default_factory=list)
    tooth_key: Optional[str] = None
    surfaces: Optional[List[str]] = None
    surface: Optional[str] = None
    surface_code: Optional[str] = None
    idempotency_key: Optional[str] = Field(None, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def populate_targets(self) -> "ClinicalProcedureCreate":
        if not self.targets and self.tooth_key:
            surfs = []
            if self.surfaces:
                surfs = [s.strip().upper() for s in self.surfaces if s.strip()]
            elif self.surface:
                surfs = [c.upper() for c in self.surface.replace(",", "").replace(" ", "").strip() if c.strip()]
            elif self.surface_code:
                surfs = [self.surface_code.strip().upper()]

            if surfs:
                for s in surfs:
                    self.targets.append(
                        ClinicalTargetInput(
                            target_kind="surface",
                            tooth_key=str(self.tooth_key),
                            surface_code=s,
                        )
                    )
            else:
                self.targets.append(
                    ClinicalTargetInput(
                        target_kind="tooth",
                        tooth_key=str(self.tooth_key),
                    )
                )
        return self


class ClinicalProcedureBulkCreate(BaseModel):
    items: List[ClinicalProcedureCreate] = Field(..., min_length=1, max_length=50)
    idempotency_key: Optional[str] = Field(None, max_length=128)

    model_config = ConfigDict(extra="forbid")


class ClinicalBulkWorkItemResponse(BaseModel):
    items: List[ClinicalWorkItemRead]
    count: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Slice S06: Correction, History & Tooth Detail Schemas (G7-M08, G7-M10, G7-M11)
# ---------------------------------------------------------------------------


class ClinicalWorkItemCorrectionCreate(BaseModel):
    mode: Literal["entered_in_error", "supersede"]
    reason: str = Field(..., min_length=1, max_length=500)
    replacement: Optional[ClinicalWorkItemCreate] = None
    expected_version_id: Optional[int] = None
    idempotency_key: Optional[str] = Field(None, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_mode_and_replacement(self) -> "ClinicalWorkItemCorrectionCreate":
        if self.mode == "supersede" and self.replacement is None:
            raise ValueError("Replacement work item is required when mode is 'supersede'")
        if self.mode == "entered_in_error" and self.replacement is not None:
            raise ValueError("Replacement work item must not be provided when mode is 'entered_in_error'")
        return self


class ClinicalWorkItemCorrectionResponse(BaseModel):
    original_work_item: ClinicalWorkItemRead
    replacement_work_item: Optional[ClinicalWorkItemRead] = None
    correction_event_id: int
    mode: str
    reason: str

    model_config = ConfigDict(from_attributes=True)


class ClinicalEventRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    work_item_id: Optional[int] = None
    care_session_id: Optional[int] = None
    event_type: str
    occurred_at: datetime
    actor_user_id: Optional[int] = None
    payload: dict = Field(default_factory=dict)
    notes: Optional[str] = None
    created_at: datetime
    targets: List[ClinicalTargetRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ClinicalToothDetailRead(BaseModel):
    tooth_key: str
    summary: Optional[WorkspaceToothSummary] = None
    work_items: List[ClinicalWorkItemRead] = Field(default_factory=list)
    events: List[ClinicalEventRead] = Field(default_factory=list)
    legacy_treatments: List[Treatment] = Field(default_factory=list)
    legacy_tooth_statuses: List[ToothStatus] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

