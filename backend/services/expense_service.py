"""Expense domain service with tenant and financial invariants."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud, models, schemas

FORBIDDEN_EXPENSE_CATEGORY = "laboratory"
FORBIDDEN_EXPENSE_CATEGORY_MESSAGE = "مدفوعات المعامل تتسجل من صفحة المعامل، مش من المصروفات"


class ExpenseService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def create_expense(
        self, expense: schemas.ExpenseCreate, *, commit: bool = True
    ) -> models.Expense:
        if expense.cost <= 0:
            raise ValueError("Expense cost must be greater than zero")
        if expense.category and expense.category.strip().lower() == FORBIDDEN_EXPENSE_CATEGORY:
            raise ValueError(FORBIDDEN_EXPENSE_CATEGORY_MESSAGE)
        return await crud.create_expense(
            db=self.db,
            expense=expense,
            tenant_id=self.tenant_id,
            commit=commit,
        )

    async def update_expense(
        self, expense_id: int, expense_data: schemas.ExpenseUpdate, *, commit: bool = True
    ) -> models.Expense:
        stmt = select(models.Expense).where(
            models.Expense.id == expense_id,
            models.Expense.tenant_id == self.tenant_id,
        )
        existing = (await self.db.execute(stmt)).scalars().first()
        if not existing:
            raise ValueError("Expense not found")
        if expense_data.category is not None:
            if expense_data.category.strip().lower() == FORBIDDEN_EXPENSE_CATEGORY:
                raise ValueError(FORBIDDEN_EXPENSE_CATEGORY_MESSAGE)
            existing.category = expense_data.category
        if expense_data.item_name is not None:
            existing.item_name = expense_data.item_name
        if expense_data.cost is not None:
            if expense_data.cost <= 0:
                raise ValueError("Expense cost must be greater than zero")
            existing.cost = expense_data.cost
        if expense_data.date is not None:
            existing.date = expense_data.date
        if expense_data.notes is not None:
            existing.notes = expense_data.notes
        if commit:
            await self.db.commit()
            await self.db.refresh(existing)
        else:
            await self.db.flush()
        return existing
