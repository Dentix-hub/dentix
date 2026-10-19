"""
Care Session Schemas (Slice S18).
Defines request/response models for chairside CareSession lifecycle commands and queries.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)
