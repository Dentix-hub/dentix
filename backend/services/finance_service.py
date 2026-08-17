from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import timedelta
from typing import Dict, Any

from .. import models
from backend.services.tenant_time_service import get_tenant_time_context
from backend.utils.tenant_time import utc_now_naive


class FinanceService:
    """
    Business Logic for Financial Operations.
    Refactored from monolithic AI router.
    Optimized to use SQL Aggregations instead of Python loops.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_daily_revenue(self) -> Dict[str, Any]:
        """Get the tenant-business-day revenue and expense breakdown."""
        context = await get_tenant_time_context(self.db, self.tenant_id)

        stmt = (
            select(
                func.sum(models.Payment.amount).label("total_income"),
                func.count(models.Payment.id).label("transaction_count"),
            )
            .where(
                models.Payment.tenant_id == self.tenant_id,
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

        stmt = select(models.Expense).where(
            models.Expense.tenant_id == self.tenant_id
        )

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
        for exp in expenses:
            cat = exp.category or "Uncategorized"
            breakdown[cat] = breakdown.get(cat, 0) + (exp.cost or 0)
            total += exp.cost or 0

        return {
            "period": period,
            "total_expenses": total,
            "breakdown": breakdown,
            "count": len(expenses),
        }

    async def create_payment(
        self, patient_name: str, amount: float, user_id: int
    ) -> Dict[str, Any]:
        """
        Create a new payment record securely.
        Uses the canonical UTC-naive persistence convention.
        """
        stmt = select(models.Patient).where(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.name.ilike(f"%{patient_name}%"),
        )
        patient = (await self.db.execute(stmt)).scalars().first()

        if not patient:
            raise ValueError(f"Patient '{patient_name}' not found.")

        try:
            new_payment = models.Payment(
                tenant_id=self.tenant_id,
                patient_id=patient.id,
                amount=amount,
                date=utc_now_naive(),
                notes="Created via AI Assistant",
                doctor_id=user_id,
            )
            self.db.add(new_payment)
            await self.db.commit()
            await self.db.refresh(new_payment)

            return {
                "success": True,
                "payment_id": new_payment.id,
                "amount": amount,
                "patient": patient.name,
                "date": new_payment.date.isoformat(),
            }
        except Exception:
            await self.db.rollback()
            raise
