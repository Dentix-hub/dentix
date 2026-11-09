"""Expense domain service with tenant and financial invariants."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud, models, schemas

FORBIDDEN_EXPENSE_CATEGORY = "laboratory"
FORBIDDEN_EXPENSE_CATEGORY_MESSAGE = "مدفوعات المعامل تتسجل من صفحة المعامل، مش من المصروفات"


class ExpenseService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def ensure_commercial_writes_enabled(self) -> None:
        """Enforce commercial entitlement for expense writes."""
        from fastapi import HTTPException
        from backend.core.config import get_subscription_enforcement_mode
        from backend.core.commercial_registry import CapabilityKey
        from backend.services.entitlement_service import EntitlementService

        mode = get_subscription_enforcement_mode()
        if mode in {"off", "observe"}:
            return
        if not self.tenant_id or not hasattr(self.db, "get"):
            return
        stmt = (
            select(models.Tenant)
            .options(selectinload(models.Tenant.subscription_plan))
            .where(models.Tenant.id == self.tenant_id)
        )
        res = await self.db.execute(stmt)
        tenant = res.scalar_one_or_none()
        if tenant:
            emergency_restrictions, commercial_overrides = (
                await EntitlementService.async_resolve_restrictions_and_overrides(
                    self.db, self.tenant_id
                )
            )
            eval_res = EntitlementService.evaluate_tenant_entitlements(
                tenant,
                override_mode=mode,
                emergency_restrictions=emergency_restrictions,
                commercial_overrides=commercial_overrides,
            )
            if not eval_res.can_write_billable:
                billing_dec = eval_res.commercial_decisions.get(CapabilityKey.BILLING.value, {})
                detail_msg = (
                    billing_dec.get("explanation_ar")
                    or billing_dec.get("explanation_en")
                    or eval_res.reason
                    or "انتهت صلاحية الاشتراك أو الباقة لا تتضمن خاصية المصروفات. يرجى التجديد للتمكن من الإضافة أو التعديل."
                )
                raise HTTPException(
                    status_code=403,
                    detail=detail_msg,
                )

    async def create_expense(
        self, expense: schemas.ExpenseCreate, *, commit: bool = True
    ) -> models.Expense:
        await self.ensure_commercial_writes_enabled()
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

