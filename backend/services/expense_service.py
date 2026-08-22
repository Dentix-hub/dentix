"""Expense domain service with tenant and financial invariants."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud, models, schemas


class ExpenseService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def create_expense(
        self, expense: schemas.ExpenseCreate, *, commit: bool = True
    ) -> models.Expense:
        if expense.cost <= 0:
            raise ValueError("Expense cost must be greater than zero")
        return await crud.create_expense(
            db=self.db,
            expense=expense,
            tenant_id=self.tenant_id,
            commit=commit,
        )
