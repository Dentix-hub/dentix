"""Clinical/treatment-related schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
from .patient import PatientSummary
from .laboratory import LabOrderCreate
from .procedure_chart_style import ProcedureChartStyleEmbedded
from backend.core.money import NonNegativeMoney


class AppointmentBase(BaseModel):
    patient_id: int
    date_time: datetime
    duration_minutes: int = 30
    status: str = "Scheduled"
    notes: Optional[str] = None
    doctor_id: Optional[int] = None
    price_list_id: Optional[int] = None


class AppointmentUpdate(BaseModel):
    patient_id: Optional[int] = None
    date_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    doctor_id: Optional[int] = None
    price_list_id: Optional[int] = None


class AppointmentCreate(AppointmentBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patient_id": 1,
                    "date_time": "2026-04-15T10:00:00",
                    "status": "Scheduled",
                    "notes": "Regular checkup",
                    "doctor_id": 2,
                }
            ]
        }
    )


class Appointment(AppointmentBase):
    id: int
    date_time: Optional[datetime] = None  # Safe retrieval
    patient: Optional[PatientSummary] = None
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ToothStatusBase(BaseModel):
    patient_id: int
    tooth_number: int
    condition: str
    notes: Optional[str] = None
    surface: Optional[str] = None
    surfaces: Optional[list[str]] = None
    tooth_key: Optional[str] = None

    @model_validator(mode="after")
    def validate_tooth_status(self):
        valid_surfaces = {"M", "D", "O", "I", "B", "L", "P"}
        if self.surfaces:
            normalized = []
            for s in self.surfaces:
                s_clean = s.strip().upper()
                if s_clean not in valid_surfaces:
                    raise ValueError(f"Invalid surface code '{s}'. Allowed: {sorted(valid_surfaces)}")
                if s_clean not in normalized:
                    normalized.append(s_clean)
            self.surfaces = normalized
            if not self.surface:
                self.surface = "".join(sorted(normalized))
        elif self.surface:
            letters = [c.upper() for c in self.surface.replace(",", "").replace(" ", "").strip()]
            for c in letters:
                if c not in valid_surfaces:
                    raise ValueError(f"Invalid surface code '{c}'. Allowed: {sorted(valid_surfaces)}")
            self.surfaces = sorted(list(set(letters)))
            self.surface = "".join(self.surfaces)

        if not self.tooth_key and self.tooth_number is not None:
            self.tooth_key = str(self.tooth_number)
        return self


class ToothStatusCreate(ToothStatusBase):
    pass


class ToothStatus(ToothStatusBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TreatmentBase(BaseModel):
    patient_id: int
    tooth_number: Optional[int] = None
    tooth_key: Optional[str] = None
    target_kind: Optional[str] = "tooth"
    surface: Optional[str] = None
    surfaces: Optional[list[str]] = None
    diagnosis: Optional[str] = None
    procedure: Optional[str] = None
    lab_choice: Optional[Literal["external_lab", "in_clinic"]] = None
    doctor_id: Optional[int] = None
    cost: NonNegativeMoney
    discount: Optional[NonNegativeMoney] = Decimal("0.00")
    canal_count: Optional[int] = None
    canal_lengths: Optional[str] = None
    sessions: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Done"  # Pending, In Progress, Done

    @model_validator(mode="after")
    def validate_treatment_rules(self):
        if self.discount is None:
            self.discount = Decimal("0.00")
        if self.discount > self.cost:
            raise ValueError("discount cannot exceed treatment cost")

        valid_surfaces = {"M", "D", "O", "I", "B", "L", "P"}
        if self.surfaces:
            normalized = []
            for s in self.surfaces:
                s_clean = s.strip().upper()
                if s_clean not in valid_surfaces:
                    raise ValueError(f"Invalid surface code '{s}'. Allowed: {sorted(valid_surfaces)}")
                if s_clean not in normalized:
                    normalized.append(s_clean)
            self.surfaces = normalized
            if not self.surface:
                self.surface = "".join(sorted(normalized))
            self.target_kind = "surface"
        elif self.surface:
            letters = [c.upper() for c in self.surface.replace(",", "").replace(" ", "").strip()]
            for c in letters:
                if c not in valid_surfaces:
                    raise ValueError(f"Invalid surface code '{c}'. Allowed: {sorted(valid_surfaces)}")
            self.surfaces = sorted(list(set(letters)))
            self.surface = "".join(self.surfaces)
            self.target_kind = "surface"

        if self.tooth_number is not None and not self.tooth_key:
            self.tooth_key = str(self.tooth_number)
        elif self.tooth_key and self.tooth_number is None:
            try:
                self.tooth_number = int(self.tooth_key)
            except ValueError:
                pass
        return self


class ConsumedMaterialItem(BaseModel):
    material_id: int
    quantity: float = Field(gt=0)
    session_id: Optional[int] = None
    weight_score: Optional[float] = 1.0
    is_manual_override: Optional[bool] = False
    material_type: Optional[str] = None
    category_id: Optional[int] = None


class TreatmentCreate(TreatmentBase):
    idempotency_key: Optional[str] = Field(None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    lab_order: Optional[LabOrderCreate] = None
    consumedMaterials: Optional[list[ConsumedMaterialItem]] = None
    skip_stock_check: Optional[bool] = False
    price_list_id: Optional[int] = None
    clinical_work_item_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patient_id": 1,
                    "procedure": "Composite Filling",
                    "cost": 500.0,
                    "diagnosis": "Dental Caries",
                    "tooth_number": 14,
                    "surface": "MOD",
                    "doctor_id": 2,
                    "notes": "Mesio-occluso-distal composite",
                    "consumedMaterials": [
                        {"material_id": 1, "quantity": 1.0}
                    ],
                }
            ]
        }
    )


class ToothProcedureItem(BaseModel):
    """Single procedure specification within a multi-procedure tooth treatment."""
    procedure: str
    lab_choice: Optional[Literal["external_lab", "in_clinic"]] = None
    lab_order: Optional[LabOrderCreate] = None
    idempotency_key: Optional[str] = Field(None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    cost: NonNegativeMoney = Decimal("0.00")
    discount: NonNegativeMoney = Decimal("0.00")
    diagnosis: Optional[str] = None
    surface: Optional[str] = None
    surfaces: Optional[list[str]] = None
    canal_count: Optional[int] = None
    canal_lengths: Optional[str] = None
    sessions: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Done"
    consumedMaterials: Optional[list[ConsumedMaterialItem]] = None
    skip_stock_check: Optional[bool] = False
    price_list_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_procedure_item(self):
        if self.discount > self.cost:
            raise ValueError("discount cannot exceed procedure cost")
        valid_surfaces = {"M", "D", "O", "I", "B", "L", "P"}
        if self.surfaces:
            normalized = []
            for s in self.surfaces:
                s_clean = s.strip().upper()
                if s_clean not in valid_surfaces:
                    raise ValueError(f"Invalid surface code '{s}'. Allowed: {sorted(valid_surfaces)}")
                if s_clean not in normalized:
                    normalized.append(s_clean)
            self.surfaces = normalized
            if not self.surface:
                self.surface = "".join(sorted(normalized))
        elif self.surface:
            letters = [c.upper() for c in self.surface.replace(",", "").replace(" ", "").strip()]
            for c in letters:
                if c not in valid_surfaces:
                    raise ValueError(f"Invalid surface code '{c}'. Allowed: {sorted(valid_surfaces)}")
            self.surfaces = sorted(list(set(letters)))
            self.surface = "".join(self.surfaces)
        return self


class ToothMultiProcedureCreate(BaseModel):
    """Payload to record multiple procedures and optional findings on a single tooth."""
    patient_id: int
    tooth_number: int
    tooth_key: Optional[str] = None
    procedures: list[ToothProcedureItem] = Field(..., min_length=1)
    doctor_id: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_tooth(self):
        if not self.tooth_key:
            self.tooth_key = str(self.tooth_number)
        return self


class ToothFindingItem(BaseModel):
    """Single clinical finding specification on a tooth (e.g. CARIES, FRACTURE)."""
    finding_code: str
    surface: Optional[str] = None
    surfaces: Optional[list[str]] = None
    severity: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_finding_surfaces(self):
        valid_surfaces = {"M", "D", "O", "I", "B", "L", "P"}
        if self.surfaces:
            normalized = [s.strip().upper() for s in self.surfaces if s.strip().upper() in valid_surfaces]
            self.surfaces = sorted(list(set(normalized)))
            if not self.surface:
                self.surface = "".join(self.surfaces)
        elif self.surface:
            letters = [c.upper() for c in self.surface.replace(",", "").replace(" ", "").strip() if c.upper() in valid_surfaces]
            self.surfaces = sorted(list(set(letters)))
            self.surface = "".join(self.surfaces)
        return self


class ToothFindingCreate(BaseModel):
    """Payload to record one or more clinical findings on a tooth."""
    patient_id: int
    tooth_number: int
    tooth_key: Optional[str] = None
    findings: list[ToothFindingItem] = Field(..., min_length=1)
    doctor_id: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_tooth(self):
        if not self.tooth_key:
            self.tooth_key = str(self.tooth_number)
        return self


class ToothSymptomCreate(BaseModel):
    """Payload to record symptoms on a tooth (e.g. PAIN, sensitivity)."""
    patient_id: int
    tooth_number: int
    tooth_key: Optional[str] = None
    symptom: str
    severity: Optional[str] = "moderate"
    notes: Optional[str] = None
    doctor_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_tooth(self):
        if not self.tooth_key:
            self.tooth_key = str(self.tooth_number)
        return self


class TreatmentSessionBase(BaseModel):
    treatment_id: int
    notes: Optional[str] = None
    session_date: Optional[datetime] = None


class TreatmentSessionCreate(TreatmentSessionBase):
    pass


class TreatmentSession(TreatmentSessionBase):
    id: int
    session_date: datetime

    model_config = ConfigDict(from_attributes=True)


class Treatment(TreatmentBase):
    id: int
    date: Optional[datetime] = None
    consumedMaterials: Optional[list[ConsumedMaterialItem]] = None
    treatment_sessions: Optional[list[TreatmentSession]] = None

    model_config = ConfigDict(from_attributes=True)


class ToothClinicalRecordResponse(BaseModel):
    """Response returned when recording multi-procedure, findings, or symptoms."""
    patient_id: int
    tooth_number: int
    tooth_key: str
    treatments: list[Treatment] = Field(default_factory=list)
    work_item_ids: list[int] = Field(default_factory=list)
    event_ids: list[int] = Field(default_factory=list)
    message: str = "Clinical record saved successfully"


class ProcedureBase(BaseModel):
    name: str
    price: NonNegativeMoney
    code: Optional[str] = None
    category: Optional[str] = None


class ProcedureCreate(ProcedureBase):
    price: NonNegativeMoney


class Procedure(ProcedureBase):
    id: int
    tenant_id: Optional[int] = None
    canonical_code: Optional[str] = None
    requires_lab: bool = False
    chart_style: Optional[ProcedureChartStyleEmbedded] = None

    model_config = ConfigDict(from_attributes=True)


class PrescriptionBase(BaseModel):
    patient_id: int
    medications: str
    notes: Optional[str] = None
    date: Optional[datetime] = None


class PrescriptionCreate(PrescriptionBase):
    pass


class Prescription(PrescriptionBase):
    id: int
    date: datetime

    model_config = ConfigDict(from_attributes=True)


class PrescriptionPatientInfo(BaseModel):
    id: int
    name: str


class PrescriptionClinicInfo(BaseModel):
    doctor_name: Optional[str] = None
    doctor_title: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None


class PrescriptionPrint(BaseModel):
    """Server-authoritative print DTO; the client renders it verbatim."""
    prescription: Prescription
    patient: PrescriptionPatientInfo
    clinic: PrescriptionClinicInfo


class SavedMedicationBase(BaseModel):
    name: str
    strength: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    notes: Optional[str] = None


class SavedMedicationCreate(SavedMedicationBase):
    pass


class SavedMedication(SavedMedicationBase):
    id: int
    tenant_id: int

    model_config = ConfigDict(from_attributes=True)
