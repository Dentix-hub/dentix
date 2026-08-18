"""Final Finance V2 accounting facade with employment-date-aware compensation.

Preserves the reconciled Finance V2 implementation while ensuring period fixed
salary never accrues before a user's configured hire date. This keeps Overview,
doctor compensation, staff dues, and monthly payroll proration consistent.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from backend import models
from backend.services.accounting_service_pre_hire_proration import (
    AccountingService as PreviousAccountingService,
)


class AccountingService(PreviousAccountingService):
    """Finance truth layer with hire-date-aware period compensation."""

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

        if hire_date:
            if isinstance(hire_date, str):
                hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
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
        for row in rows:
            fixed_period = await self._period_fixed_amount_for_user(
                float(row.get("fixed_salary") or 0.0),
                start,
                end,
                hire_dates.get(row.get("id")),
            )
            row["fixed_salary_period"] = fixed_period
            row["total_due"] = round(
                fixed_period + float(row.get("appointment_earnings") or 0.0),
                2,
            )
        return rows, round(sum(float(row["total_due"]) for row in rows), 2)

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
        return data
