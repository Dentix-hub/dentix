"""Authoritative Finance V2 summary and write-boundary services.

This module implements the shared financial definitions documented in
``docs/FINANCE_METRIC_CONTRACT.md`` without changing the legacy
``/metrics/profitability`` formula. The compatibility endpoint can therefore
remain stable while Finance V2 consumers migrate to one server-owned source of
truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.money import as_decimal, quantize_money
from backend.services.accounting_service import AccountingService
from backend.services.tenant_time_service import get_tenant_timezone
from backend.utils.audit_logger import log_admin_action
from backend.utils.tenant_time import tenant_day_utc_bounds_naive, tenant_local_date


FINANCE_DEFINITION_VERSION = "finance-summary-v1"
FINANCE_CURRENCY = "EGP"


METRIC_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "gross_production": {
        "scope": "period",
        "formula": "SUM(treatment.cost)",
        "description": "Gross treatment production before patient discounts.",
    },
    "patient_discounts": {
        "scope": "period",
        "formula": "SUM(treatment.discount)",
        "description": "Patient discounts recorded on treatments in the selected period.",
    },
    "net_invoiced": {
        "scope": "period",
        "formula": "gross_production - patient_discounts",
        "description": "Net treatment charges created in the selected period.",
    },
    "collected": {
        "scope": "period",
        "formula": "SUM(payment.amount)",
        "description": "Patient cash collections recorded in the selected period.",
    },
    "current_patient_debt": {
        "scope": "all_time_as_of_now",
        "formula": "SUM(MAX(0, all_time_net_invoiced_by_patient - all_time_paid_by_patient))",
        "description": "Current positive patient receivables. It is intentionally not period-scoped.",
    },
    "period_balance": {
        "scope": "period",
        "formula": "net_invoiced - collected",
        "description": "Selected-period treatment charges less selected-period collections.",
    },
    "doctor_dues": {
        "scope": "period",
        "formula": "SUM(doctor_commission + fixed_salary_period)",
        "description": "Calculated provider entitlement for the selected period.",
    },
    "staff_dues": {
        "scope": "period",
        "formula": "SUM(fixed_salary_period + per_appointment_fee_component)",
        "description": "Calculated non-doctor staff entitlement for the selected period.",
    },
    "manual_expenses": {
        "scope": "period",
        "formula": "SUM(expense.cost)",
        "description": "Manual operating expenses recorded in the selected period.",
    },
    "lab_costs": {
        "scope": "period",
        "formula": "SUM(lab_order.cost)",
        "description": "Laboratory order costs recorded in the selected period.",
    },
    "total_deductions": {
        "scope": "period",
        "formula": "doctor_dues + staff_dues + manual_expenses + lab_costs",
        "description": "Operational deductions defined by the Finance metric contract.",
    },
    "net_operational_result": {
        "scope": "period",
        "formula": "collected - total_deductions",
        "description": "Cash collections less the contract-defined operational deductions.",
    },
}


@dataclass(frozen=True)
class ResolvedFinancePeriod:
    timezone: str
    local_start: date
    local_end: date
    utc_start: datetime
    utc_end_exclusive: datetime

    @property
    def accounting_start_marker(self) -> datetime:
        """Tenant-local marker consumed by the existing AccountingService."""
        return datetime.combine(self.local_start, time.min)

    @property
    def accounting_end_marker(self) -> datetime:
        """Tenant-local inclusive marker consumed by the existing service."""
        return datetime.combine(self.local_end, time(23, 59, 59))

    def metadata(self) -> Dict[str, str]:
        return {
            "kind": "period",
            "scope": "period",
            "start": self.local_start.isoformat(),
            "end": self.local_end.isoformat(),
            "timezone": self.timezone,
        }


class FinanceSummaryService:
    """One source of truth for shared Finance V2 headline metrics."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        *,
        now_utc: Optional[datetime] = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.now_utc = now_utc
        self.accounting = AccountingService(db, tenant_id)

    @staticmethod
    def _parse_date(value: str, field_name: str) -> date:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {field_name}; expected YYYY-MM-DD") from exc

    async def resolve_period(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ResolvedFinancePeriod:
        """Resolve an explicit range or the tenant-local current month."""
        if bool(start_date) != bool(end_date):
            raise ValueError(
                "Both start_date and end_date are required when filtering by date"
            )

        timezone_name = await get_tenant_timezone(self.db, self.tenant_id)
        if start_date and end_date:
            local_start = self._parse_date(start_date, "start_date")
            local_end = self._parse_date(end_date, "end_date")
            if local_end < local_start:
                raise ValueError("end_date must be on or after start_date")
        else:
            local_end = tenant_local_date(timezone_name, now_utc=self.now_utc)
            local_start = local_end.replace(day=1)

        utc_start, _ = tenant_day_utc_bounds_naive(
            timezone_name,
            local_date=local_start,
        )
        _, utc_end_exclusive = tenant_day_utc_bounds_naive(
            timezone_name,
            local_date=local_end,
        )
        return ResolvedFinancePeriod(
            timezone=timezone_name,
            local_start=local_start,
            local_end=local_end,
            utc_start=utc_start,
            utc_end_exclusive=utc_end_exclusive,
        )

    async def get_current_patient_debt(
        self,
        *,
        patient_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Decimal:
        """Return current all-time positive receivables independent of activity.

        Historical DENTIX financial rows may have a NULL event-level tenant_id.
        Tenant ownership for those rows is established through the Patient
        relationship, matching the existing Finance V2 compatibility contract.
        """
        treatments = (
            select(
                models.Treatment.patient_id.label("patient_id"),
                func.sum(models.Treatment.cost - models.Treatment.discount).label(
                    "invoiced"
                ),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
            )
            .group_by(models.Treatment.patient_id)
            .subquery()
        )
        payments = (
            select(
                models.Payment.patient_id.label("patient_id"),
                func.sum(models.Payment.amount).label("paid"),
            )
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .group_by(models.Payment.patient_id)
            .subquery()
        )

        invoiced = func.coalesce(treatments.c.invoiced, 0)
        paid = func.coalesce(payments.c.paid, 0)
        balance = invoiced - paid
        positive_balance = case((balance > 0, balance), else_=0)

        stmt = (
            select(func.coalesce(func.sum(positive_balance), 0))
            .select_from(models.Patient)
            .outerjoin(treatments, treatments.c.patient_id == models.Patient.id)
            .outerjoin(payments, payments.c.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        if patient_id is not None:
            stmt = stmt.where(models.Patient.id == patient_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    models.Patient.name.ilike(pattern),
                    models.Patient.phone.ilike(pattern),
                )
            )

        return quantize_money(as_decimal((await self.db.execute(stmt)).scalar()))

    async def _production_totals(
        self,
        period: ResolvedFinancePeriod,
        patient_id: Optional[int],
    ) -> tuple[Decimal, Decimal, int, int]:
        """Return period production using Patient ownership as tenant boundary."""
        stmt = (
            select(
                func.coalesce(func.sum(models.Treatment.cost), 0),
                func.coalesce(func.sum(models.Treatment.discount), 0),
                func.count(models.Treatment.id),
                func.count(models.Treatment.patient_id.distinct()),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
                models.Treatment.date >= period.utc_start,
                models.Treatment.date < period.utc_end_exclusive,
            )
        )
        if patient_id is not None:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        gross, discounts, treatment_count, unique_patients = (
            await self.db.execute(stmt)
        ).one()
        return (
            quantize_money(as_decimal(gross)),
            quantize_money(as_decimal(discounts)),
            int(treatment_count or 0),
            int(unique_patients or 0),
        )

    async def _collected_total(
        self,
        period: ResolvedFinancePeriod,
        patient_id: Optional[int],
    ) -> Decimal:
        """Return period collections, retaining patient-owned legacy NULL rows."""
        stmt = (
            select(func.coalesce(func.sum(models.Payment.amount), 0))
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= period.utc_start,
                models.Payment.date < period.utc_end_exclusive,
            )
        )
        if patient_id is not None:
            stmt = stmt.where(models.Payment.patient_id == patient_id)
        return quantize_money(as_decimal((await self.db.execute(stmt)).scalar()))

    async def _valid_appointment_count(
        self,
        period: ResolvedFinancePeriod,
        patient_id: Optional[int],
    ) -> int:
        local_start = datetime.combine(period.local_start, time.min)
        local_end_exclusive = datetime.combine(
            period.local_end + timedelta(days=1),
            time.min,
        )
        stmt = (
            select(func.count(models.Appointment.id))
            .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Appointment.is_deleted == False,  # noqa: E712
                models.Appointment.status != "Cancelled",
                models.Appointment.date_time >= local_start,
                models.Appointment.date_time < local_end_exclusive,
            )
        )
        if patient_id is not None:
            stmt = stmt.where(models.Appointment.patient_id == patient_id)
        return int((await self.db.execute(stmt)).scalar() or 0)

    async def get_summary(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        patient_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build the contract-defined shared Finance summary."""
        period = await self.resolve_period(start_date, end_date)
        start_marker = period.accounting_start_marker
        end_marker = period.accounting_end_marker

        gross_production, discounts, treatment_count, unique_patients = (
            await self._production_totals(period, patient_id)
        )
        net_invoiced = quantize_money(gross_production - discounts)
        collected = await self._collected_total(period, patient_id)
        valid_appointments = await self._valid_appointment_count(period, patient_id)

        doctor_details, doctor_due_raw = await self.accounting.calculate_doctor_dues(
            start_marker,
            end_marker,
            patient_id=patient_id,
        )
        staff_details, staff_due_raw = await self.accounting.calculate_staff_dues(
            start_marker,
            end_marker,
            valid_appointments,
        )
        doctor_due = quantize_money(as_decimal(doctor_due_raw))
        staff_due = quantize_money(as_decimal(staff_due_raw))

        if patient_id is None:
            expenses = quantize_money(
                as_decimal(
                    await self.accounting.get_total_expenses(start_marker, end_marker)
                )
            )
        else:
            # Clinic-wide manual expenses are not attributed to one patient.
            expenses = Decimal("0.00")

        lab_costs = quantize_money(
            as_decimal(
                await self.accounting.get_total_lab_costs(
                    start_marker,
                    end_marker,
                    patient_id=patient_id,
                )
            )
        )
        current_debt = await self.get_current_patient_debt(patient_id=patient_id)
        period_balance = quantize_money(net_invoiced - collected)
        total_deductions = quantize_money(
            doctor_due + staff_due + expenses + lab_costs
        )
        net_operational_result = quantize_money(collected - total_deductions)

        def money(value: Decimal | int | float) -> float:
            return float(quantize_money(as_decimal(value)))

        return {
            "definition_version": FINANCE_DEFINITION_VERSION,
            "currency": FINANCE_CURRENCY,
            "currency_source": "product_default",
            "period": period.metadata(),
            "metric_definitions": METRIC_DEFINITIONS,
            "legacy_aliases": {
                "net_profit": "net_operational_result",
                "income.total_revenue": "net_invoiced",
                "income.outstanding": "current_patient_debt",
            },
            "income": {
                "total_revenue": money(net_invoiced),
                "gross_revenue": money(gross_production),
                "total_discounts": money(discounts),
                "net_revenue": money(net_invoiced),
                "total_collected": money(collected),
                "outstanding": money(current_debt),
                "all_time_outstanding": money(current_debt),
                "period_balance": money(period_balance),
                "total_appointments": valid_appointments,
                "treatment_count": treatment_count,
                "unique_patients": unique_patients,
            },
            "deductions": {
                "doctor_dues": {
                    "total": money(doctor_due),
                    "details": doctor_details,
                },
                "staff_dues": {
                    "total": money(staff_due),
                    "details": staff_details,
                },
                "lab_costs": money(lab_costs),
                "expenses": money(expenses),
                "total_deductions": money(total_deductions),
            },
            "net_operational_result": money(net_operational_result),
            # Compatibility alias retained while older Finance consumers migrate.
            "net_profit": money(net_operational_result),
        }


class CompensationSettingsService:
    """Atomic compensation configuration writes."""

    ALLOWED_FIELDS = {
        "commission_percent",
        "fixed_salary",
        "per_appointment_fee",
        "hire_date",
    }

    def __init__(self, db: AsyncSession, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def patch_settings(
        self,
        user_id: int,
        current_user: models.User,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        unknown = set(updates) - self.ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"Unsupported compensation fields: {sorted(unknown)}")
        if not updates:
            raise ValueError("At least one compensation field is required")

        user = (
            await self.db.execute(
                select(models.User)
                .where(
                    models.User.id == user_id,
                    models.User.tenant_id == self.tenant_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if user is None:
            return None

        old_values: Dict[str, Any] = {}
        new_values: Dict[str, Any] = {}
        for field_name, value in updates.items():
            old_values[field_name] = getattr(user, field_name)
            setattr(user, field_name, value)
            new_values[field_name] = value

        log_admin_action(
            self.db,
            current_user,
            "update",
            "compensation_settings",
            target_user_id=user_id,
            old_value=old_values,
            new_value=new_values,
        )

        result = {
            "user_id": user.id,
            "commission_percent": float(as_decimal(user.commission_percent)),
            "fixed_salary": float(as_decimal(user.fixed_salary)),
            "per_appointment_fee": float(as_decimal(user.per_appointment_fee)),
            "hire_date": user.hire_date.isoformat() if user.hire_date else None,
            "updated_fields": sorted(updates.keys()),
        }

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return result
