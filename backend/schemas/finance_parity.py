from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class PatientFinanceParitySummary(BaseModel):
    patient_id: int
    patient_name: str
    legacy_charges: Decimal
    shadow_charges: Decimal
    charge_delta: Decimal
    payments_total: Decimal
    legacy_balance: Decimal
    shadow_balance: Decimal
    balance_delta: Decimal
    is_parity_match: bool
    status: str  # PARITY_MATCH | SHADOW_SURPLUS | LEGACY_SURPLUS
    legacy_treatments_count: int
    clinical_charges_count: int
    work_items_count: int
    discrepancy_reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PatientFinanceParityDetail(PatientFinanceParitySummary):
    tenant_id: int
    evaluated_at: datetime
    work_item_projections: List[Dict[str, Any]] = Field(default_factory=list)
    clinical_charges: List[Dict[str, Any]] = Field(default_factory=list)
    legacy_treatments: List[Dict[str, Any]] = Field(default_factory=list)


class TenantFinanceParityReport(BaseModel):
    tenant_id: int
    tenant_name: str
    evaluated_at: datetime
    total_patients_evaluated: int
    patients_with_parity: int
    patients_with_discrepancy: int
    is_tenant_parity_match: bool

    total_legacy_charges: Decimal
    total_shadow_charges: Decimal
    total_charge_delta: Decimal

    total_payments: Decimal
    total_legacy_balance: Decimal
    total_shadow_balance: Decimal
    total_balance_delta: Decimal

    patients: List[PatientFinanceParitySummary] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LabDoubleChargeAnomaly(BaseModel):
    patient_id: int
    patient_name: Optional[str] = None
    anomaly_type: str  # duplicate_manual_treatment | linked_treatment_price_mismatch | orphaned_linked_treatment | multiple_linked_treatments | unlinked_lab_with_manual_treatment
    lab_order_id: Optional[int] = None
    lab_work_type: Optional[str] = None
    lab_order_price: Optional[Decimal] = None
    lab_order_date: Optional[datetime] = None
    tooth_number: Optional[str] = None
    linked_treatment_id: Optional[int] = None
    candidate_treatment_ids: List[int] = Field(default_factory=list)
    total_treatment_cost: Decimal
    estimated_overcharge_amount: Decimal
    remediation_suggestion: str

    model_config = ConfigDict(from_attributes=True)


class TenantLabAnomalyReport(BaseModel):
    tenant_id: int
    tenant_name: str
    evaluated_at: datetime
    total_anomalies_count: int
    patients_affected_count: int
    total_potential_overcharge: Decimal
    anomalies: List[LabDoubleChargeAnomaly] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

