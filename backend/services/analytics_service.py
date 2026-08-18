"""Tenant-local financial analytics facade for AI/admin reporting."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import desc, func, select

from backend import models
from backend.services.analytics_service_legacy import AnalyticsService as LegacyAnalyticsService
from backend.services.tenant_time_service import get_tenant_time_context
from backend.utils.tenant_time import resolve_timezone, tenant_day_utc_bounds_naive


class AnalyticsService(LegacyAnalyticsService):
    """Keep non-financial analytics intact while aligning money/date semantics."""

    async def _period_dates(self, period: str) -> tuple[date | None, date | None]:
        context = await get_tenant_time_context(self.db, self.tenant_id)
        today = context.business_date
        normalized = (period or "").lower()
        if normalized == "today":
            return today, today
        if normalized in {"week", "this_week"}:
            # Finance V2/MENA week starts on Saturday.
            days_since_saturday = (today.weekday() - 5) % 7
            return today - timedelta(days=days_since_saturday), today
        if normalized in {"month", "this_month"}:
            return today.replace(day=1), today
        if normalized in {"year", "this_year"}:
            return today.replace(month=1, day=1), today
        return None, None

    async def _date_bounds(self, start_day: date, end_day: date):
        context = await get_tenant_time_context(self.db, self.tenant_id)
        utc_start, _ = tenant_day_utc_bounds_naive(
            context.timezone_name,
            local_date=start_day,
        )
        _, utc_end = tenant_day_utc_bounds_naive(
            context.timezone_name,
            local_date=end_day,
        )
        local_start = datetime.combine(start_day, time.min)
        local_end = datetime.combine(end_day + timedelta(days=1), time.min)
        return context, utc_start, utc_end, local_start, local_end

    async def get_doctor_ranking(self, period: str, metric: str) -> Dict[str, Any]:
        """Rank providers by active net production or unique active patients."""
        start_day, end_day = await self._period_dates(period)
        stmt = (
            select(models.User.username)
            .join(models.Treatment, models.User.id == models.Treatment.doctor_id)
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.User.tenant_id == self.tenant_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
            )
        )
        if start_day and end_day:
            _, utc_start, utc_end, _, _ = await self._date_bounds(start_day, end_day)
            stmt = stmt.where(
                models.Treatment.date >= utc_start,
                models.Treatment.date < utc_end,
            )

        if metric == "revenue":
            stmt = stmt.add_columns(
                func.sum(models.Treatment.cost - models.Treatment.discount).label("score")
            )
        elif metric == "patients":
            stmt = stmt.add_columns(
                func.count(func.distinct(models.Treatment.patient_id)).label("score")
            )
        else:
            return {"period": period, "metric": metric, "ranking": []}

        rows = (
            await self.db.execute(
                stmt.group_by(models.User.id, models.User.username)
                .order_by(desc("score"))
            )
        ).all()
        return {
            "period": period,
            "metric": metric,
            "ranking": [
                {"name": row[0], "value": float(row[1] or 0)}
                for row in rows
            ],
        }

    async def get_top_procedures(self, period: str, limit: int = 5) -> Dict[str, Any]:
        """Get active procedures with authoritative net production."""
        start_day, end_day = await self._period_dates(period)
        stmt = (
            select(
                models.Treatment.procedure,
                func.count(models.Treatment.id).label("count"),
                func.sum(models.Treatment.cost - models.Treatment.discount).label("revenue"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
            )
        )
        if start_day and end_day:
            _, utc_start, utc_end, _, _ = await self._date_bounds(start_day, end_day)
            stmt = stmt.where(
                models.Treatment.date >= utc_start,
                models.Treatment.date < utc_end,
            )
        rows = (
            await self.db.execute(
                stmt.group_by(models.Treatment.procedure)
                .order_by(desc("count"))
                .limit(limit)
            )
        ).all()
        return {
            "period": period,
            "top_procedures": [
                {
                    "name": row[0],
                    "count": int(row[1] or 0),
                    "revenue": float(row[2] or 0),
                }
                for row in rows
                if row[0]
            ],
        }

    async def get_revenue_trend(self, period: str) -> Dict[str, Any]:
        """Bucket collected cash by tenant-local day/month."""
        context = await get_tenant_time_context(self.db, self.tenant_id)
        today = context.business_date
        normalized = (period or "").lower()
        if normalized == "year":
            start_day = today.replace(month=1, day=1)
            group_monthly = True
        elif normalized in {"week", "this_week"}:
            start_day, _ = await self._period_dates("week")
            group_monthly = False
        else:
            start_day = today.replace(day=1)
            group_monthly = False

        _, utc_start, utc_end, _, _ = await self._date_bounds(start_day, today)
        payment_rows = (
            await self.db.execute(
                select(models.Payment.date, models.Payment.amount)
                .join(models.Patient, models.Payment.patient_id == models.Patient.id)
                .where(
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                    models.Payment.date >= utc_start,
                    models.Payment.date < utc_end,
                )
            )
        ).all()

        tenant_tz = resolve_timezone(context.timezone_name)
        buckets: dict[str, float] = {}
        for timestamp, amount in payment_rows:
            if timestamp is None:
                continue
            aware_utc = (
                timestamp.replace(tzinfo=timezone.utc)
                if timestamp.tzinfo is None
                else timestamp.astimezone(timezone.utc)
            )
            local_day = aware_utc.astimezone(tenant_tz).date()
            key = local_day.strftime("%Y-%m") if group_monthly else local_day.isoformat()
            buckets[key] = buckets.get(key, 0.0) + float(amount or 0.0)

        return {
            "period": period,
            "trend": [
                {"date": key, "revenue": round(buckets[key], 2)}
                for key in sorted(buckets)
            ],
        }

    async def get_dashboard_summary(self, period: str) -> Dict[str, Any]:
        """Return tenant-local high-level AI dashboard stats."""
        start_day, end_day = await self._period_dates(period)
        if start_day is None or end_day is None:
            context = await get_tenant_time_context(self.db, self.tenant_id)
            end_day = context.business_date
            start_day = date(1970, 1, 1)
        _, utc_start, utc_end, local_start, local_end = await self._date_bounds(
            start_day,
            end_day,
        )

        total_patients = await self.db.scalar(
            select(func.count(models.Patient.id)).where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        ) or 0
        new_patients = await self.db.scalar(
            select(func.count(models.Patient.id)).where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Patient.created_at >= utc_start,
                models.Patient.created_at < utc_end,
            )
        ) or 0
        period_appointments = await self.db.scalar(
            select(func.count(models.Appointment.id))
            .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Appointment.is_deleted == False,  # noqa: E712
                models.Appointment.date_time >= local_start,
                models.Appointment.date_time < local_end,
            )
        ) or 0
        period_revenue = await self.db.scalar(
            select(func.sum(models.Payment.amount))
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= utc_start,
                models.Payment.date < utc_end,
            )
        ) or 0

        return {
            "period": period,
            "total_patients": int(total_patients),
            "new_patients": int(new_patients),
            "period_appointments": int(period_appointments),
            "period_revenue": float(period_revenue),
        }

    async def _named_comparison_period(self, name: str, today: date) -> tuple[date, date]:
        if name == "this_week":
            days_since_saturday = (today.weekday() - 5) % 7
            return today - timedelta(days=days_since_saturday), today
        if name == "last_week":
            days_since_saturday = (today.weekday() - 5) % 7
            this_start = today - timedelta(days=days_since_saturday)
            return this_start - timedelta(days=7), this_start - timedelta(days=1)
        if name == "this_month":
            return today.replace(day=1), today
        if name == "last_month":
            first_this = today.replace(day=1)
            last_prev = first_this - timedelta(days=1)
            return last_prev.replace(day=1), last_prev
        return today - timedelta(days=29), today

    async def compare_periods(
        self,
        period1: str,
        period2: str,
        metric: str,
    ) -> Dict[str, Any]:
        context = await get_tenant_time_context(self.db, self.tenant_id)
        start1, end1 = await self._named_comparison_period(period1, context.business_date)
        start2, end2 = await self._named_comparison_period(period2, context.business_date)

        async def calculate_metric(start_day: date, end_day: date):
            _, utc_start, utc_end, local_start, local_end = await self._date_bounds(
                start_day,
                end_day,
            )
            if metric == "revenue":
                stmt = (
                    select(func.sum(models.Payment.amount))
                    .join(models.Patient, models.Payment.patient_id == models.Patient.id)
                    .where(
                        models.Patient.tenant_id == self.tenant_id,
                        models.Patient.is_deleted == False,  # noqa: E712
                        models.Payment.date >= utc_start,
                        models.Payment.date < utc_end,
                    )
                )
            elif metric == "patients":
                stmt = select(func.count(models.Patient.id)).where(
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                    models.Patient.created_at >= utc_start,
                    models.Patient.created_at < utc_end,
                )
            else:
                stmt = (
                    select(func.count(models.Appointment.id))
                    .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
                    .where(
                        models.Patient.tenant_id == self.tenant_id,
                        models.Patient.is_deleted == False,  # noqa: E712
                        models.Appointment.is_deleted == False,  # noqa: E712
                        models.Appointment.date_time >= local_start,
                        models.Appointment.date_time < local_end,
                    )
                )
            return await self.db.scalar(stmt) or 0

        value1 = await calculate_metric(start1, end1)
        value2 = await calculate_metric(start2, end2)
        if value2 > 0:
            change_pct = ((value1 - value2) / value2) * 100
        elif value1 > 0:
            change_pct = 100.0
        else:
            change_pct = 0.0

        return {
            "metric": metric,
            "period1": {"name": period1, "value": float(value1)},
            "period2": {"name": period2, "value": float(value2)},
            "change_percent": change_pct,
        }
