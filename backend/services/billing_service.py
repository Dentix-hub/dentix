"""Correctness facade for billing service financial aggregates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select

from backend import models, schemas
from backend.crud import billing as billing_crud
from backend.services.billing_service_legacy import BillingService as LegacyBillingService


class BillingService(LegacyBillingService):
    """Preserve BillingService API while enforcing active-treatment semantics."""

    async def create_payment(
        self,
        payment: schemas.PaymentCreate,
        doctor_id: int = None,
        commit: bool = True,
    ):
        patient_stmt = select(models.Patient).where(
            models.Patient.id == payment.patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,
        )
        patient = (await self.db.execute(patient_stmt)).scalars().first()
        if not patient:
            raise ValueError("Patient not found")

        resolved_doctor_id = doctor_id or payment.doctor_id
        if resolved_doctor_id is None:
            doctor_stmt = (
                select(models.Treatment.doctor_id)
                .where(
                    models.Treatment.patient_id == payment.patient_id,
                    models.Treatment.tenant_id == self.tenant_id,
                    models.Treatment.is_deleted == False,
                    models.Treatment.doctor_id.isnot(None),
                )
                .order_by(models.Treatment.date.desc(), models.Treatment.id.desc())
                .limit(1)
            )
            resolved_doctor_id = (await self.db.execute(doctor_stmt)).scalar_one_or_none()

        return await billing_crud.create_payment(
            db=self.db,
            payment=payment,
            tenant_id=self.tenant_id,
            doctor_id=resolved_doctor_id,
            commit=commit,
        )

    async def _calculate_revenue(self, for_today: bool = False) -> float:
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
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
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    async def _calculate_total_discount(self) -> float:
        stmt = (
            select(func.sum(models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    async def _calculate_monthly_revenue(self) -> float:
        month_start = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Treatment.date >= month_start,
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    async def get_outstanding_balance(
        self, patient_id: Optional[int] = None
    ) -> float:
        revenue_stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
            )
        )
        payment_stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient)
            .where(
                models.Payment.tenant_id == self.tenant_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
            )
        )
        revenue_stmt = self._apply_patient_scope(revenue_stmt)
        payment_stmt = self._apply_patient_scope(payment_stmt)
        if patient_id:
            revenue_stmt = revenue_stmt.where(models.Treatment.patient_id == patient_id)
            payment_stmt = payment_stmt.where(models.Payment.patient_id == patient_id)
        revenue = await self._scalar(revenue_stmt)
        payments = await self._scalar(payment_stmt)
        return max(0.0, revenue - payments)
