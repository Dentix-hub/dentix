"""Billing and financial schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


class PaymentBase(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    amount: float
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

    model_config = ConfigDict(from_attributes=True)


class ExpenseBase(BaseModel):
    item_name: str
    cost: float
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
