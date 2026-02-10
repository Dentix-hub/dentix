"""
Standardized Response Models for AI Tools.
Decouples internal service dictionaries from AI Tool outputs.
"""

from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class BaseToolResponse(BaseModel):
    success: bool
    message: str
    risk_level: str = "SAFE"
    data: Optional[Dict[str, Any]] = None


class PatientSummary(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    age: Optional[int] = None


class PatientFileResponse(BaseToolResponse):
    patient: Optional[PatientSummary] = None
    recent_treatments: List[Dict] = []
    found: bool = False


class PatientListResponse(BaseToolResponse):
    count: int
    patients: List[PatientSummary] = []


class AppointmentSlot(BaseModel):
    time: str
    available: bool


class AppointmentListResponse(BaseToolResponse):
    appointments: List[Dict] = []
