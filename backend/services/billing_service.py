"""Correctness facade for billing service financial aggregates."""

from __future__ import annotations

from datetime import date, timezone
from typing import Optional

from sqlalchemy import func, select

from backend import models, schemas
from backend.crud import billing as billing_crud
from backend.crud import reporting as reporting_crud
from backend.services.billing_service_legacy import BillingService as LegacyBillingService
from backend.utils.tenant_time import tenant_day_utc_bounds_naive, utc_now_naive


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
            models.Patient.is_deleted == False,  # noqa: E712
        )
        patient = (await self.db.execute(patient_stmt)).scalars().first()
        if not patient:
            raise ValueError("Patient not found")

        # Payment.date is optional in the API. Materialize it here instead of
        # relying on a SQLAlchemy column default after PaymentCreate has already
        # supplied an explicit None. Persist instant-like timestamps as UTC-naive
        # per the established DENTIX database convention.
        payment_date = payment.date
        if payment_date is None:
            payment_date = utc_now_naive()
        elif payment_date.tzinfo is not None:
            payment_date = payment_date.astimezone(timezone.utc).replace(tzinfo=None)
        payment = payment.model_copy(update={"date": payment_date})

        resolved_doctor_id = doctor_id or payment.doctor_id
        if resolved_doctor_id is None:
            doctor_stmt = (
                select(models.Treatment.doctor_id)
                .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
                .where(
                    models.Treatment.patient_id == payment.patient_id,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                    models.Treatment.is_deleted == False,  # noqa: E712
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
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
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
                models.Treatment.is_deleted == False,  # noqa: E712
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
                models.Treatment.is_deleted == False,  # noqa: E712
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

    async def _calculate_monthly_revenue(self) -> float:
        context = await self._get_time_context()
        first_day = date(context.business_date.year, context.business_date.month, 1)
        utc_start, _ = tenant_day_utc_bounds_naive(
            context.timezone_name,
            local_date=first_day,
        )
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
                models.Treatment.date >= utc_start,
                models.Treatment.date < context.utc_end,
            )
        )
        return await self._scalar(self._apply_patient_scope(stmt))

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
                models.Treatment.is_deleted == False,  # noqa: E712
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
            revenue_stmt = revenue_stmt.where(models.Treatment.patient_id == patient_id)
            payment_stmt = payment_stmt.where(models.Payment.patient_id == patient_id)
        revenue = await self._scalar(revenue_stmt)
        payments = await self._scalar(payment_stmt)
        return max(0.0, revenue - payments)
