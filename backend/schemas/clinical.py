"""Clinical/treatment-related schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AppointmentBase(BaseModel):
    patient_id: int
    date_time: datetime
    status: str = "Scheduled"
    notes: Optional[str] = None
    doctor_id: Optional[int] = None
    price_list_id: Optional[int] = None


class AppointmentCreate(AppointmentBase):
    pass


class Appointment(AppointmentBase):
    id: int
    patient_name: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True)


class ToothStatusBase(BaseModel):
    patient_id: int
    tooth_number: int
    condition: str
    notes: Optional[str] = None


class ToothStatusCreate(ToothStatusBase):
    pass


class ToothStatus(ToothStatusBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True)


class TreatmentBase(BaseModel):
    patient_id: int
    tooth_number: Optional[int] = None
    diagnosis: Optional[str] = None
    procedure: Optional[str] = None
    doctor_id: Optional[int] = None
    cost: float
    discount: float = 0.0
    canal_count: Optional[int] = None
    canal_lengths: Optional[str] = None
    sessions: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None



class ConsumedMaterialItem(BaseModel):
    material_id: int
    quantity: float


class TreatmentCreate(TreatmentBase):
    consumedMaterials: Optional[list[ConsumedMaterialItem]] = None


class Treatment(TreatmentBase):
    id: int
    date: Optional[datetime] = None
    consumedMaterials: Optional[list[ConsumedMaterialItem]] = None

    model_config = ConfigDict(
        from_attributes=True)


class ProcedureBase(BaseModel):
    name: str
    price: float


class ProcedureCreate(ProcedureBase):
    price: float


class Procedure(ProcedureBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True)


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

    model_config = ConfigDict(
        from_attributes=True)


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

    model_config = ConfigDict(
        from_attributes=True)
