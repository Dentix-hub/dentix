"""
Clinical Commands Schemas (Slice S04).
Defines request/response models for native clinical work item mutations and queries.
"""

from datetime import datetime
from typing import List, Optional
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

    model_config = ConfigDict(from_attributes=True)
