"""Clinical/treatment-related schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from .patient import PatientSummary
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


class ToothStatusCreate(ToothStatusBase):
    pass


class ToothStatus(ToothStatusBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TreatmentBase(BaseModel):
    patient_id: int
    tooth_number: Optional[int] = None
    diagnosis: Optional[str] = None
    procedure: Optional[str] = None
    doctor_id: Optional[int] = None
    cost: NonNegativeMoney
    discount: NonNegativeMoney = Decimal("0.00")
    canal_count: Optional[int] = None
    canal_lengths: Optional[str] = None
    sessions: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Done"  # Pending, In Progress, Done

    @model_validator(mode="after")
    def validate_discount_not_above_cost(self):
        if self.discount > self.cost:
            raise ValueError("discount cannot exceed treatment cost")
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
    consumedMaterials: Optional[list[ConsumedMaterialItem]] = None
    skip_stock_check: Optional[bool] = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patient_id": 1,
                    "procedure": "Composite Filling",
                    "cost": 500.0,
                    "diagnosis": "Dental Caries",
                    "tooth_number": 14,
                    "doctor_id": 2,
                    "notes": "Mesial surface",
                    "consumedMaterials": [
                        {"material_id": 1, "quantity": 1.0}
                    ],
                }
            ]
        }
    )


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


class ProcedureBase(BaseModel):
    name: str
    price: NonNegativeMoney


class ProcedureCreate(ProcedureBase):
    price: NonNegativeMoney


class Procedure(ProcedureBase):
    id: int

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
