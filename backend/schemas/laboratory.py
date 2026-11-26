"""Laboratory and lab order schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

from backend.utils.tenant_time import utc_now_naive
from backend.core.money import NonNegativeMoney, PositiveMoney

ALLOWED_LAB_ORDER_STATUSES = {
    "pending",
    "in_progress",
    "sent",
    "sent_to_lab",
    "try_in",
    "ready",
    "received",
    "completed",
    "delivered",
    "cancelled",
}


class LaboratoryBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None
    notes: Optional[str] = None


class LaboratoryCreate(LaboratoryBase):
    name: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Laboratory name cannot be empty")
        return trimmed


class LaboratoryUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Laboratory name cannot be empty")
        return trimmed


class Laboratory(LaboratoryBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabOrderBase(BaseModel):
    patient_id: Optional[int] = None
    laboratory_id: Optional[int] = None
    work_item_id: Optional[int] = None
    treatment_id: Optional[int] = None
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
    paid_now: NonNegativeMoney = Decimal("0.00")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        trimmed = (v or "").strip()
        if trimmed.lower() not in ALLOWED_LAB_ORDER_STATUSES:
            raise ValueError(f"Invalid lab order status: '{v}'")
        return trimmed


class LabHandoffCreate(BaseModel):
    """Payload for 1-tap chairside lab handoff linked directly to a clinical work item (G12-M06)."""
    laboratory_id: int
    work_type: Optional[str] = None
    tooth_number: Optional[str] = None
    shade: Optional[str] = None
    material: Optional[str] = None
    cost: NonNegativeMoney = Decimal("0.00")
    price_to_patient: NonNegativeMoney = Decimal("0.00")
    delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


class LabOrderUpdate(BaseModel):
    laboratory_id: Optional[int] = None
    work_item_id: Optional[int] = None
    treatment_id: Optional[int] = None
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

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if trimmed.lower() not in ALLOWED_LAB_ORDER_STATUSES:
            raise ValueError(f"Invalid lab order status: '{v}'")
        return trimmed


class LabOrder(LabOrderBase):
    id: int
    order_date: datetime
    received_date: Optional[datetime] = None
    patient_name: Optional[str] = None
    laboratory_name: Optional[str] = None
    is_existing: Optional[bool] = None
    paid_amount: NonNegativeMoney = Decimal("0.00")
    remaining_amount: NonNegativeMoney = Decimal("0.00")
    payment_status: str = "unpaid"

    model_config = ConfigDict(from_attributes=True)


class LabPaymentBase(BaseModel):
    laboratory_id: Optional[int] = None
    lab_order_id: Optional[int] = None
    amount: PositiveMoney
    date: datetime = Field(default_factory=utc_now_naive)
    notes: Optional[str] = None
    method: str = "Cash"


class LabPaymentCreate(LabPaymentBase):
    pass


class LabPaymentAllocate(BaseModel):
    lab_order_id: int


class LabPayment(LabPaymentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
