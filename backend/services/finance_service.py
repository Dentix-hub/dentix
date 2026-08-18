from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import timedelta
from typing import Dict, Any

from .. import models
from backend.schemas.billing import PaymentCreate
from backend.services.billing_service import BillingService
from backend.services.tenant_time_service import get_tenant_time_context


class FinanceService:
    """Business logic for AI/automation financial operations."""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_daily_revenue(self) -> Dict[str, Any]:
        """Get tenant-business-day cash inflow and manual expense breakdown."""
        context = await get_tenant_time_context(self.db, self.tenant_id)

        stmt = (
            select(
                func.sum(models.Payment.amount).label("total_income"),
                func.count(models.Payment.id).label("transaction_count"),
            )
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= context.utc_start,
                models.Payment.date < context.utc_end,
            )
        )
        result = (await self.db.execute(stmt)).first()
        total_income = result.total_income or 0
        transaction_count = result.transaction_count or 0

        stmt_expense = select(func.sum(models.Expense.cost)).where(
            models.Expense.tenant_id == self.tenant_id,
            models.Expense.date == context.business_date,
        )
        total_expenses = await self.db.scalar(stmt_expense) or 0
        net_profit = total_income - total_expenses

        return {
            "date": context.business_date.isoformat(),
            "total_revenue": float(total_income),
            "total_expenses": float(total_expenses),
            "net_profit": float(net_profit),
            "transaction_count": transaction_count,
        }

    async def get_period_expenses(self, period: str = "this_month") -> Dict[str, Any]:
        """Get expenses filtered by period with tenant-local calendar semantics."""
        context = await get_tenant_time_context(self.db, self.tenant_id)
        today = context.business_date

        stmt = select(models.Expense).where(models.Expense.tenant_id == self.tenant_id)
        if period == "today":
            stmt = stmt.where(models.Expense.date == today)
        elif period in ("week", "this_week"):
            start_week = today - timedelta(days=today.weekday())
            stmt = stmt.where(models.Expense.date >= start_week)
        elif period in ("month", "this_month"):
            stmt = stmt.where(
                func.extract("month", models.Expense.date) == today.month,
                func.extract("year", models.Expense.date) == today.year,
            )

        expenses = (await self.db.execute(stmt)).scalars().all()
        breakdown = {}
        total = 0
        for expense in expenses:
            category = expense.category or "Uncategorized"
            breakdown[category] = breakdown.get(category, 0) + (expense.cost or 0)
            total += expense.cost or 0

        return {
            "period": period,
            "total_expenses": total,
            "breakdown": breakdown,
            "count": len(expenses),
        }

    async def create_payment(
        self,
        patient_name: str,
        amount: float,
        user_id: int,
    ) -> Dict[str, Any]:
        """Create a payment through the canonical BillingService path.

        `user_id` is retained for backwards call compatibility; the recorder is
        not automatically the treating doctor. Provider attribution is resolved
        from the patient's active treatment history by BillingService.
        """
        stmt = select(models.Patient).where(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Patient.name.ilike(f"%{patient_name}%"),
        )
        patient = (await self.db.execute(stmt)).scalars().first()
        if not patient:
            raise ValueError(f"Patient '{patient_name}' not found.")

        _ = user_id  # recorder identity is intentionally not provider attribution
        payment = await BillingService(self.db, self.tenant_id).create_payment(
            PaymentCreate(
                patient_id=patient.id,
                amount=amount,
                notes="Created via AI Assistant",
            ),
            doctor_id=None,
            commit=True,
        )
        return {
            "success": True,
            "payment_id": payment.id,
            "amount": amount,
            "patient": patient.name,
            "date": payment.date.isoformat(),
        }
