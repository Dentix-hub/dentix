"""Final Finance V2 accounting facade with employment-date-aware compensation.

Preserves the reconciled Finance V2 implementation while enforcing the final
financial truth rules that sit above legacy compatibility layers:
- compensation never accrues before hire date;
- per-appointment staff fees start on hire date;
- patient-owned historical events remain visible even when event tenant_id is NULL;
- patient-owned laboratory orders follow the same legacy compatibility rule.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from backend import models
from backend.services.accounting_service_pre_hire_proration import (
    AccountingService as PreviousAccountingService,
)
from backend.services.tenant_time_service import get_tenant_timezone
from backend.utils.tenant_time import resolve_timezone


class AccountingService(PreviousAccountingService):
    """Finance truth layer with tenant-safe, hire-date-aware compensation."""

    @staticmethod
    def _coerce_date(value):
        if value and isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        return value

    async def _period_fixed_amount_for_user(
        self,
        monthly_amount: float,
        start: datetime,
        end: datetime,
        hire_date,
    ) -> float:
        monthly = float(monthly_amount or 0.0)
        if monthly <= 0:
            return 0.0

        start_date, end_date = await self._local_dates_for_range(start, end)
        if end_date < start_date:
            return 0.0

        hire_date = self._coerce_date(hire_date)
        if hire_date:
            start_date = max(start_date, hire_date)
            if start_date > end_date:
                return 0.0

        total = 0.0
        cursor = start_date
        while cursor <= end_date:
            days_in_month = monthrange(cursor.year, cursor.month)[1]
            segment_end = min(
                date(cursor.year, cursor.month, days_in_month),
                end_date,
            )
            days_in_segment = (segment_end - cursor).days + 1
            total += monthly * (days_in_segment / days_in_month)
            cursor = segment_end + timedelta(days=1)
        return round(total, 2)

    async def _hire_dates(self, user_ids: List[int]) -> Dict[int, Any]:
        if not user_ids:
            return {}
        rows = (
            await self.db.execute(
                select(models.User.id, models.User.hire_date).where(
                    models.User.tenant_id == self.tenant_id,
                    models.User.id.in_(user_ids),
                )
            )
        ).all()
        return {user_id: hire_date for user_id, hire_date in rows}

    async def get_lab_costs_by_doctor(
        self,
        start: datetime,
        end: datetime,
        doctor_ids: List[int],
        patient_id: Optional[int] = None,
    ) -> Dict[int, float]:
        """Return patient-owned lab costs, including legacy NULL event tenant IDs."""
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(
                models.LabOrder.doctor_id,
                func.sum(models.LabOrder.cost).label("lab_cost"),
            )
            .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
            )
        )
        if doctor_ids:
            stmt = stmt.where(models.LabOrder.doctor_id.in_(doctor_ids))
        if patient_id:
            stmt = stmt.where(models.LabOrder.patient_id == patient_id)
        rows = (
            await self.db.execute(stmt.group_by(models.LabOrder.doctor_id))
        ).all()
        return {row[0]: float(row[1] or 0.0) for row in rows}

    async def get_total_lab_costs(
        self,
        start: datetime,
        end: datetime,
        patient_id: Optional[int] = None,
    ) -> float:
        """Return lab costs by patient ownership rather than event tenant marker."""
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(func.sum(models.LabOrder.cost))
            .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.LabOrder.patient_id == patient_id)
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_doctor_revenue_analytics(
        self,
        start: datetime,
        end: datetime,
        patient_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        rows = await super().get_doctor_revenue_analytics(
            start,
            end,
            patient_id=patient_id,
        )
        hire_dates = await self._hire_dates(
            [int(row["doctor_id"]) for row in rows if row.get("doctor_id") is not None]
        )
        for row in rows:
            doctor_id = row.get("doctor_id")
            fixed_period = await self._period_fixed_amount_for_user(
                float(row.get("fixed_salary") or 0.0),
                start,
                end,
                hire_dates.get(doctor_id),
            )
            row["fixed_salary_period"] = fixed_period
            row["total_due"] = round(
                float(row.get("commission_amount") or 0.0) + fixed_period,
                2,
            )
        return rows

    async def _appointments_after_hire_in_period(
        self,
        hire_date: date,
        end_date: date,
    ) -> int:
        start_local = datetime.combine(hire_date, datetime.min.time())
        end_exclusive = datetime.combine(
            end_date + timedelta(days=1),
            datetime.min.time(),
        )
        stmt = (
            select(func.count(models.Appointment.id))
            .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Appointment.is_deleted == False,  # noqa: E712
                models.Appointment.status != "Cancelled",
                models.Appointment.date_time >= start_local,
                models.Appointment.date_time < end_exclusive,
            )
        )
        return int((await self.db.execute(stmt)).scalar() or 0)

    async def calculate_staff_dues(
        self,
        start: datetime,
        end: datetime,
        total_appointments: int,
    ) -> tuple[List[Dict[str, Any]], float]:
        rows, _ = await super().calculate_staff_dues(
            start,
            end,
            total_appointments,
        )
        hire_dates = await self._hire_dates(
            [int(row["id"]) for row in rows if row.get("id") is not None]
        )
        period_start, period_end = await self._local_dates_for_range(start, end)

        for row in rows:
            hire_date = self._coerce_date(hire_dates.get(row.get("id")))
            fixed_period = await self._period_fixed_amount_for_user(
                float(row.get("fixed_salary") or 0.0),
                start,
                end,
                hire_date,
            )

            appointment_count = int(row.get("appointments_in_period") or 0)
            if hire_date:
                if hire_date > period_end:
                    appointment_count = 0
                elif hire_date > period_start:
                    appointment_count = await self._appointments_after_hire_in_period(
                        hire_date,
                        period_end,
                    )

            appointment_earnings = round(
                float(row.get("per_appointment_fee") or 0.0) * appointment_count,
                2,
            )
            row["appointments_in_period"] = appointment_count
            row["appointment_earnings"] = appointment_earnings
            row["fixed_salary_period"] = fixed_period
            row["total_due"] = round(fixed_period + appointment_earnings, 2)

        return rows, round(sum(float(row["total_due"]) for row in rows), 2)

    async def get_salary_status_for_month(self, month: str) -> Dict[str, Any]:
        """Ensure payroll months before employment have zero payable salary."""
        data = await super().get_salary_status_for_month(month)
        year, mon = map(int, month.split("-"))
        month_end = date(year, mon, monthrange(year, mon)[1])
        rows = data.get("employees", [])
        hire_dates = await self._hire_dates(
            [int(row["id"]) for row in rows if row.get("id") is not None]
        )

        for row in rows:
            hire_date = self._coerce_date(hire_dates.get(row.get("id")))
            if hire_date and hire_date > month_end:
                paid_amount = float(row.get("paid_amount") or 0.0)
                row["is_new_this_month"] = False
                row["days_worked"] = 0
                row["prorated_salary"] = 0.0
                row["payable_amount"] = 0.0
                row["remaining_amount"] = 0.0
                row["status"] = "paid" if paid_amount > 0 else "unpaid"
                row["is_paid"] = paid_amount > 0
        return data

    async def process_salary_payment(
        self,
        user_id: int,
        current_user: models.User,
        month: str,
        amount: float,
        is_partial: bool,
        days_worked: Optional[int],
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Reject salary payments for months before the employee was hired."""
        try:
            year, mon = map(int, month.split("-"))
            month_end = date(year, mon, monthrange(year, mon)[1])
        except Exception:
            return await super().process_salary_payment(
                user_id,
                current_user,
                month,
                amount,
                is_partial,
                days_worked,
                notes,
            )

        hire_date = (
            await self.db.execute(
                select(models.User.hire_date).where(
                    models.User.id == user_id,
                    models.User.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        hire_date = self._coerce_date(hire_date)
        if hire_date and hire_date > month_end:
            return {
                "error": "لا يوجد راتب مستحق لهذا الشهر لأن تاريخ التعيين لاحق له"
            }

        return await super().process_salary_payment(
            user_id,
            current_user,
            month,
            amount,
            is_partial,
            days_worked,
            notes,
        )

    async def get_doctor_details_data(
        self,
        doctor_id: int,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        data = await super().get_doctor_details_data(doctor_id, start, end)
        if not data:
            return data

        rows = await self.get_doctor_revenue_analytics(start, end)
        stat = next(
            (row for row in rows if row.get("doctor_id") == doctor_id),
            None,
        )
        if stat:
            for key in (
                "fixed_salary",
                "fixed_salary_period",
                "commission_amount",
                "total_due",
            ):
                data[key] = stat[key]
            data["lab_cost"] = stat["lab_cost"]
            data["total_lab_cost"] = stat["lab_cost"]
            data["net_revenue"] = stat["net_revenue"]
            data["commission_base"] = stat["commission_base"]

        start_utc, end_utc = await self._normalize_utc_range(start, end)
        lab_rows = (
            await self.db.execute(
                select(models.LabOrder, models.Patient.name)
                .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
                .where(
                    models.LabOrder.doctor_id == doctor_id,
                    models.LabOrder.order_date >= start_utc,
                    models.LabOrder.order_date <= end_utc,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                )
                .order_by(models.LabOrder.order_date.desc())
            )
        ).all()
        data["lab_orders"] = [
            {
                "id": lab.id,
                "date": lab.order_date,
                "work_type": lab.work_type,
                "cost": lab.cost,
                "patient_id": lab.patient_id,
                "patient_name": patient_name,
            }
            for lab, patient_name in lab_rows
        ]
        return data

    async def get_patient_financial_details(
        self,
        patient_id: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return patient details using Patient ownership as the tenant boundary."""
        patient = (
            await self.db.execute(
                select(models.Patient).where(
                    models.Patient.id == patient_id,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                )
            )
        ).scalar_one_or_none()
        if not patient:
            return None

        normalized_start = start
        normalized_end = end
        if start and end:
            normalized_start, normalized_end = await self._normalize_utc_range(
                start,
                end,
            )

        payment_stmt = select(models.Payment).where(
            models.Payment.patient_id == patient_id,
        )
        if normalized_start and normalized_end:
            payment_stmt = payment_stmt.where(
                models.Payment.date >= normalized_start,
                models.Payment.date <= normalized_end,
            )
        payments = (
            await self.db.execute(payment_stmt.order_by(models.Payment.date.desc()))
        ).scalars().all()

        payment_history = []
        total_paid = 0.0
        for payment in payments:
            amount = float(payment.amount or 0.0)
            total_paid += amount
            payment_history.append(
                {
                    "id": payment.id,
                    "date": str(payment.date),
                    "amount": amount,
                    "notes": payment.notes,
                }
            )

        treatment_stmt = select(models.Treatment).where(
            models.Treatment.patient_id == patient_id,
            models.Treatment.is_deleted == False,  # noqa: E712
        )
        if normalized_start and normalized_end:
            treatment_stmt = treatment_stmt.where(
                models.Treatment.date >= normalized_start,
                models.Treatment.date <= normalized_end,
            )
        treatments = (
            await self.db.execute(treatment_stmt.order_by(models.Treatment.date.desc()))
        ).scalars().all()

        total_invoiced = 0.0
        treatment_history = []
        for treatment in treatments:
            cost = float(treatment.cost or 0.0)
            discount = float(treatment.discount or 0.0)
            net = cost - discount
            total_invoiced += net
            treatment_history.append(
                {
                    "id": treatment.id,
                    "date": str(treatment.date),
                    "procedure": treatment.procedure,
                    "diagnosis": treatment.diagnosis,
                    "cost": cost,
                    "discount": discount,
                    "net": net,
                }
            )

        timezone_name = await get_tenant_timezone(self.db, self.tenant_id)
        tenant_now = (
            datetime.now(timezone.utc)
            .astimezone(resolve_timezone(timezone_name))
            .replace(tzinfo=None)
        )
        next_appointment = (
            await self.db.execute(
                select(models.Appointment)
                .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
                .where(
                    models.Appointment.patient_id == patient_id,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                    models.Appointment.date_time >= tenant_now,
                    models.Appointment.is_deleted == False,  # noqa: E712
                    models.Appointment.status != "Cancelled",
                )
                .order_by(models.Appointment.date_time.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

        return {
            "patient_id": patient_id,
            "file_number": patient.file_number or patient_id,
            "patient_name": patient.name,
            "patient_phone": patient.phone,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding_balance": max(0.0, total_invoiced - total_paid),
            "period_balance": total_invoiced - total_paid,
            "payment_history": payment_history,
            "treatment_history": treatment_history,
            "next_due_date": (
                str(next_appointment.date_time) if next_appointment else None
            ),
        }
