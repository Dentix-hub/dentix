"""Correctness facade for billing service financial aggregates."""

from __future__ import annotations

from datetime import date, timezone
from typing import Optional

from sqlalchemy import func, select

from backend import models, schemas
from backend.core.permissions import DOCTOR_ROLES
from backend.crud import billing as billing_crud
from backend.crud import reporting as reporting_crud
from backend.services.billing_service_legacy import BillingService as LegacyBillingService
from backend.utils.tenant_time import tenant_day_utc_bounds_naive, utc_now_naive


class BillingService(LegacyBillingService):
    """Preserve BillingService API while enforcing active-treatment semantics."""

    async def ensure_commercial_writes_enabled(self) -> None:
        """Enforce commercial entitlement for financial/billing writes."""
        from fastapi import HTTPException
        from sqlalchemy.orm import selectinload
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
                    or "انتهت صلاحية الاشتراك أو الباقة لا تتضمن خاصية الفواتير. يرجى التجديد للتمكن من الإضافة أو التعديل."
                )
                raise HTTPException(
                    status_code=403,
                    detail=detail_msg,
                )

    async def create_payment(
        self,
        payment: schemas.PaymentCreate,
        doctor_id: int = None,
        commit: bool = True,
    ):
        await self.ensure_commercial_writes_enabled()
        if payment.amount <= 0:
            raise ValueError("Payment amount must be greater than zero")

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

        resolved_doctor_id = doctor_id if doctor_id is not None else payment.doctor_id
        if resolved_doctor_id is not None:
            # A provider may be a doctor or an owner/admin who also treats
            # patients, but never a receptionist/nurse/other non-provider and
            # never a user from another tenant.
            provider_stmt = select(models.User.id).where(
                models.User.id == resolved_doctor_id,
                models.User.tenant_id == self.tenant_id,
                models.User.role.in_(DOCTOR_ROLES),
            )
            provider_id = (await self.db.execute(provider_stmt)).scalar_one_or_none()
            if provider_id is None:
                raise ValueError("Doctor not found")
        else:
            doctor_stmt = (
                select(models.Treatment.doctor_id)
                .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
                .join(models.User, models.Treatment.doctor_id == models.User.id)
                .where(
                    models.Treatment.patient_id == payment.patient_id,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                    models.Treatment.is_deleted == False,  # noqa: E712
                    models.Treatment.doctor_id.isnot(None),
                    models.User.tenant_id == self.tenant_id,
                    models.User.role.in_(DOCTOR_ROLES),
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
