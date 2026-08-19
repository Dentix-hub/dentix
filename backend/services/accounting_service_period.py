"""Finance correctness facade over the legacy AccountingService.

Keeps the public API stable while fixing tenant-local date boundaries,
soft-deleted treatment leakage, payment-to-doctor attribution, strict report
periods, and fixed-monthly compensation being charged in full to short ranges.
"""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select

from backend import models
from backend.core.permissions import DOCTOR_ROLES
from backend.services.accounting_service_legacy import AccountingService as LegacyAccountingService
from backend.services.tenant_time_service import get_tenant_timezone
from backend.utils.tenant_time import resolve_timezone, tenant_day_utc_bounds_naive


class _BusinessBoundary(datetime):
    """UTC-naive boundary whose ``date()`` remains the tenant-local report date.

    The legacy activity method filters UTC timestamp columns and local ``Date``
    expense columns with the same datetime object. This adapter preserves both
    semantics while the legacy method remains API-compatible.
    """

    def __new__(cls, value: datetime, business_date: date):
        obj = datetime.__new__(
            cls,
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
        )
        obj._business_date = business_date
        return obj

    def date(self):
        return self._business_date


class AccountingService(LegacyAccountingService):
    """Correctness layer for Finance V2 without changing endpoint contracts."""

    def parse_date_range(self, start_date: str, end_date: str) -> tuple[datetime, datetime]:
        override = getattr(self, "_parse_override", None)
        if override and override[0] == start_date and override[1] == end_date:
            return override[2], override[3]
        return super().parse_date_range(start_date, end_date)

    @staticmethod
    def _looks_like_local_marker(start: datetime, end: datetime) -> bool:
        return (
            start.hour == 0 and start.minute == 0 and start.second == 0 and start.microsecond == 0
            and end.hour == 23 and end.minute == 59 and end.second == 59 and end.microsecond == 0
        )

    async def _normalize_utc_range(self, start: datetime, end: datetime) -> tuple[datetime, datetime]:
        """Convert parser-produced tenant-local dates into inclusive UTC-naive bounds."""
        if not self._looks_like_local_marker(start, end):
            return start, end
        timezone_name = await get_tenant_timezone(self.db, self.tenant_id)
        utc_start, _ = tenant_day_utc_bounds_naive(timezone_name, local_date=start.date())
        _, utc_end_exclusive = tenant_day_utc_bounds_naive(timezone_name, local_date=end.date())
        return utc_start, utc_end_exclusive - timedelta(microseconds=1)

    async def _local_dates_for_range(self, start: datetime, end: datetime) -> tuple[date, date]:
        if self._looks_like_local_marker(start, end):
            return start.date(), end.date()
        timezone_name = await get_tenant_timezone(self.db, self.tenant_id)
        tz = resolve_timezone(timezone_name)
        s = start.replace(tzinfo=timezone.utc).astimezone(tz).date()
        e = end.replace(tzinfo=timezone.utc).astimezone(tz).date()
        return s, e

    async def _period_fixed_amount(self, monthly_amount: float, start: datetime, end: datetime) -> float:
        monthly = float(monthly_amount or 0.0)
        if monthly <= 0:
            return 0.0
        start_date, end_date = await self._local_dates_for_range(start, end)
        if end_date < start_date:
            return 0.0
        total = 0.0
        cursor = start_date
        while cursor <= end_date:
            days = monthrange(cursor.year, cursor.month)[1]
            segment_end = min(date(cursor.year, cursor.month, days), end_date)
            total += monthly * (((segment_end - cursor).days + 1) / days)
            cursor = segment_end + timedelta(days=1)
        return round(total, 2)

    async def get_treatment_stats_by_doctor(
        self, start: datetime, end: datetime, doctor_ids: List[int], patient_id: Optional[int] = None
    ) -> Dict[int, Dict[str, Any]]:
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(
                models.Treatment.doctor_id,
                func.count(models.Treatment.id).label("treatment_count"),
                func.sum(models.Treatment.cost).label("gross_cost"),
                func.sum(models.Treatment.discount).label("total_discount"),
                func.sum(models.Treatment.cost - models.Treatment.discount).label("revenue"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if doctor_ids:
            stmt = stmt.where(models.Treatment.doctor_id.in_(doctor_ids))
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        rows = (await self.db.execute(stmt.group_by(models.Treatment.doctor_id))).all()
        return {
            row.doctor_id: {
                "treatment_count": int(row.treatment_count or 0),
                "gross_cost": float(row.gross_cost or 0.0),
                "total_discount": float(row.total_discount or 0.0),
                "revenue": float(row.revenue or 0.0),
            }
            for row in rows
        }

    async def get_lab_costs_by_doctor(
        self, start: datetime, end: datetime, doctor_ids: List[int], patient_id: Optional[int] = None
    ) -> Dict[int, float]:
        start, end = await self._normalize_utc_range(start, end)
        stmt = select(
            models.LabOrder.doctor_id,
            func.sum(models.LabOrder.cost).label("lab_cost"),
        ).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.order_date >= start,
            models.LabOrder.order_date <= end,
        )
        if doctor_ids:
            stmt = stmt.where(models.LabOrder.doctor_id.in_(doctor_ids))
        if patient_id:
            stmt = stmt.where(models.LabOrder.patient_id == patient_id)
        rows = (await self.db.execute(stmt.group_by(models.LabOrder.doctor_id))).all()
        return {row[0]: float(row[1] or 0.0) for row in rows}

    async def get_total_income(self, start: datetime, end: datetime, patient_id: Optional[int] = None) -> float:
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_total_collected(self, start: datetime, end: datetime, patient_id: Optional[int] = None) -> float:
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Payment.tenant_id == self.tenant_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.Payment.patient_id == patient_id)
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_total_expenses(self, start: datetime, end: datetime) -> float:
        start_date, end_date = await self._local_dates_for_range(start, end)
        stmt = select(func.sum(models.Expense.cost)).where(
            models.Expense.tenant_id == self.tenant_id,
            models.Expense.date >= start_date,
            models.Expense.date <= end_date,
        )
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_total_lab_costs(self, start: datetime, end: datetime, patient_id: Optional[int] = None) -> float:
        start, end = await self._normalize_utc_range(start, end)
        stmt = select(func.sum(models.LabOrder.cost)).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.order_date >= start,
            models.LabOrder.order_date <= end,
        )
        if patient_id:
            stmt = stmt.where(models.LabOrder.patient_id == patient_id)
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_doctor_revenue_analytics(
        self, start: datetime, end: datetime, patient_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Attribute every period payment exactly once to actual treatment providers."""
        original_start, original_end = start, end
        start, end = await self._normalize_utc_range(start, end)
        users = await self.get_relevant_users(DOCTOR_ROLES + ["admin", "super_admin"])
        user_ids = [u.id for u in users]
        stats_map = await self.get_treatment_stats_by_doctor(start, end, user_ids, patient_id)
        lab_map = await self.get_lab_costs_by_doctor(start, end, user_ids, patient_id)

        alloc_stmt = (
            select(
                models.Treatment.doctor_id,
                models.Treatment.patient_id,
                func.sum(models.Treatment.cost - models.Treatment.discount).label("net"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Treatment.doctor_id.in_(user_ids),
            )
        )
        if patient_id:
            alloc_stmt = alloc_stmt.where(models.Treatment.patient_id == patient_id)
        alloc_rows = (await self.db.execute(
            alloc_stmt.group_by(models.Treatment.doctor_id, models.Treatment.patient_id)
        )).all()

        doctor_patient_net: Dict[int, Dict[int, float]] = defaultdict(dict)
        patient_total_net: Dict[int, float] = defaultdict(float)
        for doctor_id, pat_id, net in alloc_rows:
            value = max(0.0, float(net or 0.0))
            doctor_patient_net[doctor_id][pat_id] = value
            patient_total_net[pat_id] += value

        pay_stmt = (
            select(models.Payment.doctor_id, models.Payment.patient_id, models.Payment.amount)
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Payment.tenant_id == self.tenant_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
        )
        if patient_id:
            pay_stmt = pay_stmt.where(models.Payment.patient_id == patient_id)
        payments = (await self.db.execute(pay_stmt)).all()

        direct: Dict[int, float] = defaultdict(float)
        unassigned: Dict[int, float] = defaultdict(float)
        for doctor_id, pat_id, amount in payments:
            value = float(amount or 0.0)
            reliable = (
                doctor_id in user_ids
                and doctor_patient_net.get(doctor_id, {}).get(pat_id, 0.0) > 0
            )
            if reliable:
                direct[doctor_id] += value
            else:
                unassigned[pat_id] += value

        allocated: Dict[int, float] = defaultdict(float)
        for pat_id, amount in unassigned.items():
            denominator = patient_total_net.get(pat_id, 0.0)
            if denominator <= 0:
                continue
            for doctor_id in user_ids:
                basis = doctor_patient_net.get(doctor_id, {}).get(pat_id, 0.0)
                if basis > 0:
                    allocated[doctor_id] += amount * (basis / denominator)

        result: List[Dict[str, Any]] = []
        for user in users:
            doctor_id = user.id
            stats = stats_map.get(doctor_id, {
                "treatment_count": 0,
                "gross_cost": 0.0,
                "total_discount": 0.0,
                "revenue": 0.0,
            })
            lab_cost = float(lab_map.get(doctor_id, 0.0))
            collected = round(direct.get(doctor_id, 0.0) + allocated.get(doctor_id, 0.0), 2)
            commission_percent = float(user.commission_percent or 0.0)
            monthly_fixed = float(user.fixed_salary or 0.0)
            fixed_period = await self._period_fixed_amount(monthly_fixed, original_start, original_end)
            commission_base = max(0.0, collected - lab_cost)
            commission_amount = round(commission_base * (commission_percent / 100.0), 2)
            result.append({
                "doctor_id": doctor_id,
                "doctor_name": user.username,
                "treatments": stats["treatment_count"],
                "gross_cost": stats["gross_cost"],
                "patient_discount": stats["total_discount"],
                "revenue": stats["revenue"],
                "collected": collected,
                "lab_cost": lab_cost,
                "net_revenue": stats["revenue"] - lab_cost,
                "commission_base": commission_base,
                "commission_percent": commission_percent,
                "commission_amount": commission_amount,
                "fixed_salary": monthly_fixed,
                "fixed_salary_period": fixed_period,
                "total_due": round(commission_amount + fixed_period, 2),
            })
        return result

    async def calculate_doctor_dues(
        self, start: datetime, end: datetime, patient_id: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], float]:
        rows = await self.get_doctor_revenue_analytics(start, end, patient_id)
        details = [{
            "id": r["doctor_id"], "name": r["doctor_name"], "revenue": r["revenue"],
            "collected": r["collected"], "lab_cost": r["lab_cost"],
            "net_revenue": r["net_revenue"], "commission_base": r["commission_base"],
            "commission_percent": r["commission_percent"], "commission_amount": r["commission_amount"],
            "fixed_salary": r["fixed_salary"], "fixed_salary_period": r["fixed_salary_period"],
            "total_due": r["total_due"],
        } for r in rows]
        return details, round(sum(float(r["total_due"]) for r in rows), 2)

    async def calculate_staff_dues(
        self, start: datetime, end: datetime, total_appointments: int
    ) -> tuple[List[Dict[str, Any]], float]:
        stmt = select(models.User).where(
            models.User.tenant_id == self.tenant_id,
            models.User.role.in_(["receptionist", "nurse", "assistant", "accountant"]),
        )
        staff = (await self.db.execute(stmt)).scalars().all()
        rows = []
        for user in staff:
            monthly = float(user.fixed_salary or 0.0)
            fixed_period = await self._period_fixed_amount(monthly, start, end)
            fee = float(user.per_appointment_fee or 0.0)
            appointment_earnings = fee * total_appointments
            rows.append({
                "id": user.id, "name": user.username, "role": user.role,
                "fixed_salary": monthly, "fixed_salary_period": fixed_period,
                "per_appointment_fee": fee, "appointments_in_period": total_appointments,
                "appointment_earnings": appointment_earnings,
                "total_due": round(fixed_period + appointment_earnings, 2),
            })
        return rows, round(sum(float(r["total_due"]) for r in rows), 2)

    async def get_doctor_details_data(self, doctor_id: int, start: datetime, end: datetime) -> Dict[str, Any]:
        original_start, original_end = start, end
        start, end = await self._normalize_utc_range(start, end)
        data = await super().get_doctor_details_data(doctor_id, start, end)
        if not data:
            return data
        stmt = (
            select(models.Treatment, models.Patient.name)
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.doctor_id == doctor_id,
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
                models.Treatment.date >= start,
                models.Treatment.date <= end,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
            )
            .order_by(models.Treatment.date.desc())
        )
        treatments = (await self.db.execute(stmt)).all()
        data["treatments"] = [{
            "id": t.id, "date": t.date, "procedure": t.procedure,
            "cost": t.cost, "discount": t.discount, "net": t.cost - t.discount,
            "patient_id": t.patient_id, "patient_name": name,
        } for t, name in treatments]
        analytics = await self.get_doctor_revenue_analytics(original_start, original_end)
        stat = next((row for row in analytics if row["doctor_id"] == doctor_id), None)
        if stat:
            for key in (
                "revenue", "collected", "lab_cost", "net_revenue", "commission_base",
                "commission_percent", "commission_amount", "fixed_salary",
                "fixed_salary_period", "total_due",
            ):
                data[key] = stat[key]
            data["total_revenue"] = stat["revenue"]
            data["total_collected"] = stat["collected"]
            data["total_lab_cost"] = stat["lab_cost"]
        return data

    async def get_patients_report(
        self, patient_id: Optional[int] = None, search: Optional[str] = None,
        outstanding_only: bool = False, start: Optional[datetime] = None,
        end: Optional[datetime] = None, skip: int = 0, limit: int = 50,
    ) -> Dict[str, Any]:
        if start and end:
            normalized_start, normalized_end = await self._normalize_utc_range(start, end)
            if not patient_id and not outstanding_only:
                activity = select(models.Patient.id).where(
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,
                    or_(
                        models.Patient.id.in_(
                            select(models.Treatment.patient_id).where(
                                models.Treatment.tenant_id == self.tenant_id,
                                models.Treatment.is_deleted == False,
                                models.Treatment.date >= normalized_start,
                                models.Treatment.date <= normalized_end,
                            )
                        ),
                        models.Patient.id.in_(
                            select(models.Payment.patient_id).where(
                                models.Payment.tenant_id == self.tenant_id,
                                models.Payment.date >= normalized_start,
                                models.Payment.date <= normalized_end,
                            )
                        ),
                    ),
                ).limit(1)
                if (await self.db.execute(activity)).scalar_one_or_none() is None:
                    return {
                        "total": 0,
                        "summary": {
                            "total_invoiced": 0.0, "total_paid": 0.0,
                            "period_balance": 0.0, "total_outstanding": 0.0,
                        },
                        "patients": [],
                    }
            start, end = normalized_start, normalized_end
        return await super().get_patients_report(
            patient_id=patient_id, search=search, outstanding_only=outstanding_only,
            start=start, end=end, skip=skip, limit=limit,
        )

    async def get_patient_financial_details(
        self, patient_id: int, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        if start and end:
            start, end = await self._normalize_utc_range(start, end)
        return await super().get_patient_financial_details(patient_id, start=start, end=end)

    async def get_financial_activity(self, *args, **kwargs) -> Dict[str, Any]:
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        if start_date is None and len(args) > 0:
            start_date = args[0]
        if end_date is None and len(args) > 1:
            end_date = args[1]
        if not start_date and not end_date:
            return await super().get_financial_activity(*args, **kwargs)
        if bool(start_date) != bool(end_date):
            raise ValueError("Both start_date and end_date are required when filtering by date")

        marker_start, marker_end = super().parse_date_range(start_date, end_date)
        utc_start, utc_end = await self._normalize_utc_range(marker_start, marker_end)
        self._parse_override = (
            start_date,
            end_date,
            _BusinessBoundary(utc_start, marker_start.date()),
            _BusinessBoundary(utc_end, marker_end.date()),
        )
        try:
            return await super().get_financial_activity(*args, **kwargs)
        finally:
            self._parse_override = None
