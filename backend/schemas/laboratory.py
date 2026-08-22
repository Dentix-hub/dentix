"""Laboratory and lab order schemas."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

from backend.utils.tenant_time import utc_now_naive
from backend.core.money import NonNegativeMoney, PositiveMoney


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
    patient_id: Optional[int] = None
    laboratory_id: Optional[int] = None
    work_type: str
    tooth_number: Optional[str] = None
    shade: Optional[str] = None
    material: Optional[str] = None
    cost: NonNegativeMoney = Decimal("0.00")
    price_to_patient: NonNegativeMoney = Decimal("0.00")
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
    cost: Optional[NonNegativeMoney] = None
    price_to_patient: Optional[NonNegativeMoney] = None
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
    laboratory_id: Optional[int] = None
    amount: PositiveMoney
    date: datetime = Field(default_factory=utc_now_naive)
    notes: Optional[str] = None
    method: str = "Cash"


class LabPaymentCreate(LabPaymentBase):
    pass


class LabPayment(LabPaymentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
