"""
Billing Service (Refactored to Async)

Financial calculations and payment processing for tenants.
Follows Single Responsibility Principle with extracted helper methods.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, date, timezone
from typing import Optional
from backend import models, schemas
from backend.crud import billing as billing_crud


class BillingService:
    """Service layer for billing and financial operations."""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self._today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).replace(tzinfo=None)

    async def _scalar(self, query) -> float:
        """Execute query and return scalar result as float, defaulting to 0.0."""
        res = await self.db.scalar(query)
        return float(res or 0.0)

    # --- Payment Operations ---
    async def create_payment(self, payment: schemas.PaymentCreate, doctor_id: int = None, commit: bool = True):
        """
        Create a payment record.

        Business Rules:
        - Patient must belong to this tenant
        - Payment amount must be positive
        """
        stmt = select(models.Patient).where(
            models.Patient.id == payment.patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
        patient = (await self.db.execute(stmt)).scalars().first()

        if not patient:
            raise ValueError("Patient not found")

        return await billing_crud.create_payment(
            db=self.db, payment=payment, tenant_id=self.tenant_id, doctor_id=doctor_id, commit=commit
        )

    # --- Revenue Calculations ---
    async def _calculate_revenue(self, for_today: bool = False) -> float:
        """
        Calculate revenue from treatments.
        Revenue = Cost - Discounts

        Args:
            for_today: If True, only calculate today's revenue
        """
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )

        if for_today:
            stmt = stmt.where(models.Treatment.date >= self._today_start)

        return await self._scalar(stmt)

    async def _calculate_total_cost(self) -> float:
        """Calculate total treatment cost (before discounts)."""
        stmt = (
            select(func.sum(models.Treatment.cost))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        return await self._scalar(stmt)

    async def _calculate_total_discount(self) -> float:
        """Calculate total discounts applied."""
        stmt = (
            select(func.sum(models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        return await self._scalar(stmt)

    async def _calculate_monthly_revenue(self) -> float:
        """Calculate revenue for the current month."""
        # Get first day of current month
        today = datetime.now(timezone.utc)
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)

        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= month_start,
            )
        )
        return await self._scalar(stmt)

    # --- Payment Calculations ---
    async def _calculate_payments(self, for_today: bool = False) -> float:
        """
        Calculate total payments received.

        Args:
            for_today: If True, only calculate today's payments
        """
        stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )

        if for_today:
            stmt = stmt.where(models.Payment.date >= self._today_start)

        return await self._scalar(stmt)

    # --- Expense Calculations ---
    async def _calculate_expenses(self, for_today: bool = False) -> dict:
        """
        Calculate expenses breakdown.

        Returns:
            dict with 'lab_costs' and 'other_expenses' keys
        """
        # Lab costs
        lab_stmt = select(func.sum(models.LabOrder.cost)).where(
            models.LabOrder.tenant_id == self.tenant_id
        )

        if for_today:
            lab_stmt = lab_stmt.where(
                models.LabOrder.order_date >= self._today_start
            )

        lab_costs = await self._scalar(lab_stmt)

        # Other expenses
        expense_stmt = select(func.sum(models.Expense.cost)).where(
            models.Expense.tenant_id == self.tenant_id
        )

        if for_today:
            expense_stmt = expense_stmt.where(models.Expense.date == date.today())

        other_expenses = await self._scalar(expense_stmt)

        return {
            "lab_costs": lab_costs,
            "other_expenses": other_expenses,
            "total": lab_costs + other_expenses,
        }

    # --- Aggregate Statistics ---
    async def get_financial_stats(self) -> dict:
        """
        Get comprehensive financial statistics for the tenant.

        Returns aggregated data from all sub-calculations.
        """
        # Revenue
        total_cost = await self._calculate_total_cost()
        total_discount = await self._calculate_total_discount()
        total_revenue = total_cost - total_discount
        today_revenue = await self._calculate_revenue(for_today=True)

        # Payments
        total_received = await self._calculate_payments()
        today_received = await self._calculate_payments(for_today=True)

        # Outstanding
        outstanding = max(0, total_revenue - total_received)
        today_outstanding = max(0, today_revenue - today_received)

        # Expenses
        all_expenses = await self._calculate_expenses()
        today_expenses = await self._calculate_expenses(for_today=True)

        # Profit
        net_profit = total_received - all_expenses["total"]

        return {
            "total_revenue": total_revenue,
            "total_received": total_received,
            "outstanding": outstanding,
            "total_expenses": all_expenses["total"],
            "net_profit": net_profit,
            "monthly_revenue": await self._calculate_monthly_revenue(),
            "today_revenue": today_revenue,
            "today_received": today_received,
            "today_outstanding": today_outstanding,
            "today_expenses": today_expenses["total"],
        }

    async def get_outstanding_balance(self, patient_id: Optional[int] = None) -> float:
        """
        Get outstanding balance for a patient or entire tenant.

        Args:
            patient_id: If provided, calculate for specific patient only
        """
        # Revenue query
        revenue_stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )

        # Payment query
        payment_stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )

        if patient_id:
            revenue_stmt = revenue_stmt.where(
                models.Treatment.patient_id == patient_id
            )
            payment_stmt = payment_stmt.where(
                models.Payment.patient_id == patient_id
            )

        revenue = await self._scalar(revenue_stmt)
        payments = await self._scalar(payment_stmt)

        return max(0, revenue - payments)

    async def get_today_payments_list(self) -> list:
        """Get list of payments made today."""
        stmt = (
            select(models.Payment, models.Patient.name)
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= self._today_start,
            )
            .order_by(models.Payment.date.desc())
        )
        result = await self.db.execute(stmt)
        results = result.all()

        return [
            {
                "id": p.id,
                "amount": p.amount,
                "date": p.date,
                "patient_name": name,
                "notes": p.notes,
            }
            for p, name in results
        ]

    async def get_today_debtors_list(self) -> list:
        """Get list of patients who incurred debt today (Treatment Cost Today > Payment Today)."""
        # 1. Get patients with treatments today
        stmt = (
            select(models.Treatment)
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= self._today_start,
            )
        )
        result = await self.db.execute(stmt)
        today_treatments = result.scalars().all()

        patient_ids = set(t.patient_id for t in today_treatments)
        debtors = []

        # Query 1 — costs bulk
        _cost_stmt = (
            select(
                models.Treatment.patient_id,
                func.sum(models.Treatment.cost - models.Treatment.discount).label("total_cost"),
            )
            .where(
                models.Treatment.patient_id.in_(patient_ids),
                models.Treatment.date >= self._today_start,
            )
            .group_by(models.Treatment.patient_id)
        )
        _cost_rows = await self.db.execute(_cost_stmt)
        costs_by_pid = {r.patient_id: float(r.total_cost or 0) for r in _cost_rows.fetchall()}

        # Query 2 — payments bulk
        _paid_stmt = (
            select(
                models.Payment.patient_id,
                func.sum(models.Payment.amount).label("total_paid"),
            )
            .where(
                models.Payment.patient_id.in_(patient_ids),
                models.Payment.date >= self._today_start,
            )
            .group_by(models.Payment.patient_id)
        )
        _paid_rows = await self.db.execute(_paid_stmt)
        paid_by_pid = {r.patient_id: float(r.total_paid or 0) for r in _paid_rows.fetchall()}

        # تحديد المدينين
        debtor_ids = [
            pid for pid in patient_ids
            if (costs_by_pid.get(pid, 0) - paid_by_pid.get(pid, 0)) > 0
        ]

        # Query 3 — patient details bulk
        debtors = []
        if debtor_ids:
            _pat_stmt = select(models.Patient).where(models.Patient.id.in_(debtor_ids))
            _pat_rows = await self.db.execute(_pat_stmt)
            patients_by_id = {p.id: p for p in _pat_rows.scalars().all()}

            for pid in debtor_ids:
                patient = patients_by_id.get(pid)
                if patient:
                    cost = costs_by_pid.get(pid, 0)
                    paid = paid_by_pid.get(pid, 0)
                    debtors.append({
                        "id":         patient.id,
                        "name":       patient.name,
                        "phone":      str(patient.phone),
                        "amount":     cost - paid,
                        "total_cost": cost,
                        "total_paid": paid,
                    })

        return debtors
