"""
Care Session Material Schemas (Slice S30 / G13-M04, G13-M06, G13-M07, G13-M09).
Request/response models for point-of-care material suggestion, session-level
material consumption, and work-item material cost aggregation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CareSessionMaterialItem(BaseModel):
    material_id: int
    quantity: float = Field(gt=0)
    weight_score: Optional[float] = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")


class CareSessionMaterialUsageCreate(BaseModel):
    work_item_id: Optional[int] = Field(
        None, description="Optional ClinicalWorkItem this consumption belongs to"
    )
    items: List[CareSessionMaterialItem] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class CareSessionMaterialUsageRead(BaseModel):
    id: int
    care_session_id: int
    work_item_id: Optional[int] = None
    material_id: int
    material_name: Optional[str] = None
    material_type: Optional[str] = None
    session_id: Optional[int] = Field(
        None, description="MaterialSession (open package) id for divisible/reusable materials"
    )
    weight_score: Optional[float] = None
    quantity_used: Optional[float] = None
    cost_calculated: Optional[float] = Field(
        None, description="NULL until resolved (divisible materials are costed on package close)"
    )
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MaterialSuggestionResponse(BaseModel):
    work_item_id: int
    procedure_code: str
    step_code: Optional[str] = None
    procedure_ids: List[int] = Field(default_factory=list)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)


class WorkItemSessionMaterialCost(BaseModel):
    care_session_id: Optional[int] = None
    usage_count: int
    pending_cost_count: int
    cost: float
    usages: List[CareSessionMaterialUsageRead]


class WorkItemMaterialCostRead(BaseModel):
    work_item_id: int
    total_cost: float
    usage_count: int
    pending_cost_count: int
    sessions: List[WorkItemSessionMaterialCost]
