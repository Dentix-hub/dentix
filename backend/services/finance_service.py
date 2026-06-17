from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import date, timedelta, datetime
from typing import Dict, Any
from .. import models


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
        """Get today's total revenue and breakdown."""
        today = date.today()

        # Optimized: Single Query aggregation
        stmt = (
            select(
                func.sum(models.Payment.amount).label("total_income"),
                func.count(models.Payment.id).label("transaction_count"),
            )
            .where(
                models.Payment.tenant_id == self.tenant_id,
                func.date(models.Payment.date) == today,
            )
        )
        res = await self.db.execute(stmt)
        result = res.first()

        total_income = result.total_income or 0
        transaction_count = result.transaction_count or 0

        # Expenses
        stmt_expense = (
            select(func.sum(models.Expense.cost))
            .where(
                models.Expense.tenant_id == self.tenant_id,
                func.date(models.Expense.date) == today,
            )
        )
        total_expenses = await self.db.scalar(stmt_expense) or 0
        net_profit = total_income - total_expenses

        return {
            "date": today.isoformat(),
            "total_revenue": float(total_income),
            "total_expenses": float(total_expenses),
            "net_profit": float(net_profit),
            "transaction_count": transaction_count,
        }

    async def get_period_expenses(self, period: str = "this_month") -> Dict[str, Any]:
        """Get expenses filtered by period with category breakdown."""
        stmt = select(models.Expense).where(
            models.Expense.tenant_id == self.tenant_id
        )

        today = date.today()
        if period == "today":
            stmt = stmt.where(func.date(models.Expense.date) == today)
        elif period in ("week", "this_week"):
            start_week = today - timedelta(days=today.weekday())
            stmt = stmt.where(models.Expense.date >= start_week)
        elif period in ("month", "this_month"):
            stmt = stmt.where(
                func.extract("month", models.Expense.date) == today.month,
                func.extract("year", models.Expense.date) == today.year,
            )

        res = await self.db.execute(stmt)
        expenses = res.scalars().all()

        # Calculate Category Breakdown (Python side for now, can be SQL GroupBy)
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
        Uses explicit transaction management.
        """
        # 1. Find Patient
        stmt = (
            select(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.name.ilike(f"%{patient_name}%"),
            )
        )
        res = await self.db.execute(stmt)
        patient = res.scalars().first()

        if not patient:
            raise ValueError(f"Patient '{patient_name}' not found.")

        # 2. Create Payment
        try:
            new_payment = models.Payment(
                tenant_id=self.tenant_id,
                patient_id=patient.id,
                amount=amount,
                date=datetime.now(),
                # payment_method="Cash", # Not in model
                notes="Created via AI Assistant",
                doctor_id=user_id,  # Was recorded_by
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
        except Exception as e:
            await self.db.rollback()
            raise e
