"""
Pydantic schemas for Clinical Charges and Work-Item Billing Projections (Slice S33).
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ClinicalChargeRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    work_item_id: int
    care_session_id: Optional[int] = None
    doctor_id: Optional[int] = None
    legacy_treatment_id: Optional[int] = None
    amount: float
    discount: float
    status: str
    notes: Optional[str] = None
    version_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkItemBillingProjectionItem(BaseModel):
    work_item_id: int
    kind: str
    code: str
    work_item_status: str
    source: str  # "clinical_charge" | "legacy_treatment" | "none"
    amount: Optional[float] = None
    discount: Optional[float] = None
    status: Optional[str] = None
    charge_id: Optional[int] = None
    treatment_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PatientClinicalChargesResponse(BaseModel):
    charges: List[ClinicalChargeRead]
    projection: List[WorkItemBillingProjectionItem]

    model_config = ConfigDict(from_attributes=True)


class ClinicalChargeActionRequest(BaseModel):
    expected_version_id: Optional[int] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")
