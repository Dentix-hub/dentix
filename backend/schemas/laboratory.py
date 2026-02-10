"""Laboratory and lab order schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class LaboratoryBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None
    notes: Optional[str] = None


class LaboratoryCreate(LaboratoryBase):
    pass


class LaboratoryUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class Laboratory(LaboratoryBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabOrderBase(BaseModel):
    patient_id: int
    laboratory_id: int
    work_type: str
    tooth_number: Optional[str] = None
    shade: Optional[str] = None
    material: Optional[str] = None
    cost: float = 0.0
    price_to_patient: float = 0.0
    status: str = "pending"
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None


class LabOrderCreate(LabOrderBase):
    pass


class LabOrderUpdate(BaseModel):
    laboratory_id: Optional[int] = None
    work_type: Optional[str] = None
    tooth_number: Optional[str] = None
    shade: Optional[str] = None
    material: Optional[str] = None
    cost: Optional[float] = None
    price_to_patient: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    received_date: Optional[datetime] = None


class LabOrder(LabOrderBase):
    id: int
    order_date: datetime
    received_date: Optional[datetime] = None
    patient_name: Optional[str] = None
    laboratory_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LabPaymentBase(BaseModel):
    laboratory_id: int
    amount: float
    date: datetime = datetime.utcnow()
    notes: Optional[str] = None
    method: str = "Cash"


class LabPaymentCreate(LabPaymentBase):
    pass


class LabPayment(LabPaymentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
