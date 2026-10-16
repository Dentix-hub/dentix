"""Clinical treatment plans schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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
