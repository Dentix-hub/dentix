from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal
from pydantic import BaseModel, ConfigDict, Field


ClinicalRolloutTargetMode = Literal[
    "LEGACY_ONLY",
    "SHADOW",
    "VNEXT_PRIMARY_READ_ONLY",
    "VNEXT_PRIMARY_READ_WRITE",
]


class TenantClinicalRolloutStatus(BaseModel):
    tenant_id: int
    tenant_name: str
    rollout_mode: Literal["LEGACY_ONLY", "SHADOW", "VNEXT_PRIMARY"]
    native_writes_enabled: bool
    finance_read_enabled: bool
    feature_flags: Dict[str, bool]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantClinicalRolloutModeRequest(BaseModel):
    mode: ClinicalRolloutTargetMode = Field(..., description="Target rollout mode for the tenant")


class TenantClinicalRolloutResponse(BaseModel):
    success: bool
    tenant_id: int
    message: str
    previous_mode: str
    current_mode: str
    native_writes_enabled: bool
    flags: Dict[str, bool]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
