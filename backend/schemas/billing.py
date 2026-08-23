"""Billing and financial schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from backend.core.money import Money, NonNegativeMoney, PositiveMoney


class PaymentBase(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    amount: PositiveMoney
    date: Optional[datetime] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patient_id": 1,
                    "amount": 250.0,
                    "notes": "Payment for composite filling",
                }
            ]
        }
    )


class Payment(PaymentBase):
    id: int
    date: datetime
    patient_name: Optional[str] = None
    patient_file_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseBase(BaseModel):
    item_name: str
    cost: PositiveMoney
    category: str
    date: date
    notes: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "item_name": "Dental composite material",
                    "cost": 1200.0,
                    "category": "Materials",
                    "date": "2026-04-14",
                    "notes": "Monthly restock",
                }
            ]
        }
    )


class Expense(ExpenseBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class FinancialStats(BaseModel):
    total_revenue: float
    total_received: float
    outstanding: float
    monthly_revenue: float
    total_expenses: float = 0.0
    net_profit: float = 0.0
    today_revenue: float = 0.0
    today_received: float = 0.0
    today_outstanding: float = 0.0
    today_expenses: float = 0.0


class DashboardStats(BaseModel):
    total_patients: int
    new_patients_today: int
    total_appointments_today: int
    revenue_chart: List[dict] = []
    total_revenue: float
    total_received: float
    outstanding: float
    monthly_revenue: float
    total_expenses: float = 0.0
    net_profit: float = 0.0
    today_revenue: float = 0.0
    today_received: float = 0.0
    today_outstanding: float = 0.0
    today_expenses: float = 0.0
    business_date: Optional[str] = None
    tenant_timezone: Optional[str] = None


# --- Printable Invoice (server-authoritative DTO; clients print, never recompute) ---

class InvoiceLineItem(BaseModel):
    id: int
    date: Optional[datetime] = None
    procedure: Optional[str] = None
    diagnosis: Optional[str] = None
    tooth_number: Optional[int] = None
    status: Optional[str] = None
    cost: NonNegativeMoney
    discount: NonNegativeMoney
    net_amount: NonNegativeMoney


class InvoicePayment(BaseModel):
    id: int
    date: Optional[datetime] = None
    amount: PositiveMoney
    notes: Optional[str] = None


class InvoiceTotals(BaseModel):
    gross_total: NonNegativeMoney
    discount_total: NonNegativeMoney
    net_total: NonNegativeMoney
    paid_total: NonNegativeMoney
    remaining_total: Money


class PatientInvoice(BaseModel):
    invoice_number: str
    currency: str
    clinic_name: str
    clinic_tagline: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    patient_id: int
    patient_name: str
    patient_phone: Optional[str] = None
    data_as_of: Optional[datetime] = None
    line_items: List[InvoiceLineItem]
    payments: List[InvoicePayment]
    totals: InvoiceTotals
