"""Clinical treatment plans schemas (Slices G9a & G9b)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ClinicalWorkItemTargetRead(BaseModel):
    id: int
    target_kind: str
    tooth_key: str
    surface_code: Optional[str] = None
    root_id: Optional[str] = None
    canal_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalWorkItemSummaryRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    kind: str
    code: str
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    targets: List[ClinicalWorkItemTargetRead] = []

    model_config = ConfigDict(from_attributes=True)


class ClinicalTreatmentPlanItemCreate(BaseModel):
    work_item_id: int
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ClinicalTreatmentPlanItemRead(BaseModel):
    id: int
    tenant_id: int
    phase_id: int
    work_item_id: int
    item_order: int
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    work_item: Optional[ClinicalWorkItemSummaryRead] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalTreatmentPlanPhaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ClinicalTreatmentPlanPhaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ClinicalTreatmentPlanPhaseReorder(BaseModel):
    phase_ids: List[int] = Field(..., min_length=1, description="List of phase IDs in desired sequential order")

    model_config = ConfigDict(extra="forbid")


class ClinicalTreatmentPlanPhaseRead(BaseModel):
    id: int
    tenant_id: int
    plan_id: int
    phase_order: int
    name: str
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[ClinicalTreatmentPlanItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class ClinicalTreatmentPlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ClinicalTreatmentPlanRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    title: str
    status: str
    notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    version_id: int
    created_at: datetime
    updated_at: datetime
    phases: List[ClinicalTreatmentPlanPhaseRead] = []

    model_config = ConfigDict(from_attributes=True)


class ClinicalTreatmentPlanTransition(BaseModel):
    to_status: str = Field(..., min_length=1, max_length=32, description="Target status for treatment plan")

    model_config = ConfigDict(extra="forbid")
