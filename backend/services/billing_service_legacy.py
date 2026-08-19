"""Async billing service with tenant-business-day semantics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.crud import billing as billing_crud
from backend.crud import reporting as reporting_crud
from backend.services.tenant_time_service import (
    TenantTimeContext,
    get_tenant_time_context,
)


class BillingService:
    """Service layer for billing and financial operations.

    ``doctor_patient_scope_id`` follows the established DENTIX financial
    visibility rule: doctor financial data is scoped by
    ``Patient.assigned_doctor_id`` rather than ``Payment.doctor_id``.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        *,
        doctor_patient_scope_id: int | None = None,
        is_doctor: bool = False,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.doctor_patient_scope_id = doctor_patient_scope_id
        self.is_doctor = is_doctor
        self._time_context: TenantTimeContext | None = None

    async def _get_time_context(self) -> TenantTimeContext:
        if self._time_context is None:
            self._time_context = await get_tenant_time_context(
                self.db,
                self.tenant_id,
            )
        return self._time_context

    def _apply_patient_scope(self, stmt):
        if self.doctor_patient_scope_id is not None:
            stmt = stmt.where(
                models.Patient.assigned_doctor_id == self.doctor_patient_scope_id
            )
        return stmt

    async def _scalar(self, query) -> float:
        res = await self.db.scalar(query)
        return float(res or 0.0)

    # --- Payment Operations ---
    async def create_payment(
        self,
        payment: schemas.PaymentCreate,
        doctor_id: int = None,
        commit: bool = True,
    ):
        stmt = select(models.Patient).where(
            models.Patient.id == payment.patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
        patient = (await self.db.execute(stmt)).scalars().first()
        if not patient:
            raise ValueError("Patient not found")

        return await billing_crud.create_payment(
            db=self.db,
            payment=payment,
            tenant_id=self.tenant_id,
            doctor_id=doctor_id,
            commit=commit,
        )

    # --- Revenue Calculations ---
    async def _calculate_revenue(self, for_today: bool = False) -> float:
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        stmt = self._apply_patient_scope(stmt)

        if for_today:
            context = await self._get_time_context()
            stmt = stmt.where(
                models.Treatment.date >= context.utc_start,
                models.Treatment.date < context.utc_end,
            )

        return await self._scalar(stmt)

    async def _calculate_total_cost(self) -> float:
        stmt = (
            select(func.sum(models.Treatment.cost))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    async def _calculate_total_discount(self) -> float:
        stmt = (
            select(func.sum(models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    async def _calculate_monthly_revenue(self) -> float:
        # Keep the existing month semantics in this surgical fix.
        month_start = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= month_start,
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    # --- Payment Calculations ---
    async def _calculate_payments(self, for_today: bool = False) -> float:
        stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        stmt = self._apply_patient_scope(stmt)

        if for_today:
            context = await self._get_time_context()
            stmt = stmt.where(
                models.Payment.date >= context.utc_start,
                models.Payment.date < context.utc_end,
            )

        return await self._scalar(stmt)

    # --- Expense Calculations ---
    async def _calculate_expenses(self, for_today: bool = False) -> dict:
        context = await self._get_time_context() if for_today else None

        lab_stmt = (
            select(func.sum(models.LabOrder.cost))
            .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
            .where(
                models.LabOrder.tenant_id == self.tenant_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        lab_stmt = self._apply_patient_scope(lab_stmt)
        if context is not None:
            lab_stmt = lab_stmt.where(
                models.LabOrder.order_date >= context.utc_start,
                models.LabOrder.order_date < context.utc_end,
            )
        lab_costs = await self._scalar(lab_stmt)

        if self.is_doctor:
            other_expenses = 0.0
        else:
            expense_stmt = select(func.sum(models.Expense.cost)).where(
                models.Expense.tenant_id == self.tenant_id
            )
            if context is not None:
                expense_stmt = expense_stmt.where(
                    models.Expense.date == context.business_date
                )
            other_expenses = await self._scalar(expense_stmt)

        return {
            "lab_costs": lab_costs,
            "other_expenses": other_expenses,
            "total": lab_costs + other_expenses,
        }

    # --- Aggregate Statistics ---
    async def get_financial_stats(self) -> dict:
        context = await self._get_time_context()
        return await reporting_crud.get_financial_stats(
            self.db,
            self.tenant_id,
            timezone_name=context.timezone_name,
            business_date=context.business_date,
            doctor_patient_scope_id=self.doctor_patient_scope_id,
            is_doctor=self.is_doctor,
        )

    async def get_outstanding_balance(
        self,
        patient_id: Optional[int] = None,
    ) -> float:
        revenue_stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        payment_stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        revenue_stmt = self._apply_patient_scope(revenue_stmt)
        payment_stmt = self._apply_patient_scope(payment_stmt)

        if patient_id:
            revenue_stmt = revenue_stmt.where(
                models.Treatment.patient_id == patient_id
            )
            payment_stmt = payment_stmt.where(
                models.Payment.patient_id == patient_id
            )

        revenue = await self._scalar(revenue_stmt)
        payments = await self._scalar(payment_stmt)
        return max(0.0, revenue - payments)

    async def get_today_payments_list(self) -> list:
        context = await self._get_time_context()
        return await reporting_crud.get_today_payments(
            self.db,
            self.tenant_id,
            timezone_name=context.timezone_name,
            business_date=context.business_date,
            doctor_patient_scope_id=self.doctor_patient_scope_id,
        )

    async def get_today_debtors_list(self) -> list:
        context = await self._get_time_context()
        return await reporting_crud.get_today_debtors(
            self.db,
            self.tenant_id,
            timezone_name=context.timezone_name,
            business_date=context.business_date,
            doctor_patient_scope_id=self.doctor_patient_scope_id,
        )
