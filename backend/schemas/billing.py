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
    pass


class Payment(PaymentBase):
    id: int
    date: datetime
    patient_name: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True)


class ExpenseBase(BaseModel):
    item_name: str
    cost: float
    category: str
    date: date
    notes: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class Expense(ExpenseBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True)


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
