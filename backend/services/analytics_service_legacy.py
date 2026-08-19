from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from datetime import date, timedelta, datetime
from typing import Dict, Any, List
from .. import models


class AnalyticsService:
    """
    Business Logic for Analytics & Reporting.
    Optimized for heavy reads.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_doctor_ranking(self, period: str, metric: str) -> Dict[str, Any]:
        """Rank doctors by revenue or patient volume."""
        date_filter = self._get_date_filter(period, models.Treatment.date)

        if metric == "revenue":
            # Rank by Income (Sum of Treatment Cost)
            stmt = (
                select(
                    models.User.username, func.sum(models.Treatment.cost).label("score")
                )
                .join(models.User, models.User.id == models.Treatment.doctor_id)
                .where(models.Treatment.tenant_id == self.tenant_id)
                .where(date_filter)
                .group_by(models.User.username)
                .order_by(desc("score"))
            )

        elif metric == "patients":
            # Rank by Unique Patients
            stmt = (
                select(
                    models.User.username,
                    func.count(func.distinct(models.Treatment.patient_id)).label(
                        "score"
                    ),
                )
                .join(models.User, models.User.id == models.Treatment.doctor_id)
                .where(models.Treatment.tenant_id == self.tenant_id)
                .where(date_filter)
                .group_by(models.User.username)
                .order_by(desc("score"))
            )

        res = await self.db.execute(stmt)
        results = res.all()
        return {
            "period": period,
            "metric": metric,
            "ranking": [{"name": r[0], "value": r[1] or 0} for r in results],
        }

    async def get_top_procedures(self, period: str, limit: int = 5) -> Dict[str, Any]:
        """Get most popular procedures."""
        date_filter = self._get_date_filter(period, models.Treatment.date)

        stmt = (
            select(
                models.Treatment.procedure,
                func.count(models.Treatment.id).label("count"),
                func.sum(models.Treatment.cost).label("revenue"),
            )
            .where(models.Treatment.tenant_id == self.tenant_id)
            .where(date_filter)
            .group_by(models.Treatment.procedure)
            .order_by(desc("count"))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        results = res.all()

        return {
            "period": period,
            "top_procedures": [
                {"name": r[0], "count": r[1], "revenue": r[2] or 0}
                for r in results
                if r[0]
            ],
        }

    async def get_revenue_trend(self, period: str) -> Dict[str, Any]:
        """Get revenue grouped by time (Day/Month)."""
        # Determine grouping
        if period == "year":
            group_col = func.strftime("%Y-%m", models.Payment.date)
            date_filter = models.Payment.date >= (date.today() - timedelta(days=365))
        else:  # Month/Week -> Daily trend
            group_col = func.date(models.Payment.date)
            date_filter = models.Payment.date >= (date.today() - timedelta(days=30))

        stmt = (
            select(
                group_col.label("time_unit"),
                func.sum(models.Payment.amount).label("revenue"),
            )
            .where(models.Payment.tenant_id == self.tenant_id)
            .where(date_filter)
            .group_by(group_col)
            .order_by(group_col)
        )
        res = await self.db.execute(stmt)
        results = res.all()

        return {
            "period": period,
            "trend": [{"date": r[0], "revenue": r[1] or 0} for r in results],
        }

    def _get_date_filter(self, period: str, col):
        """Helper to generate date filters."""
        today = datetime.now().date()
        if period == "today":
            return func.date(col) == today
        elif period == "week":
            return col >= (today - timedelta(days=7))
        elif period == "month":
            return col >= (today - timedelta(days=30))
        elif period == "year":
            return col >= (today - timedelta(days=365))
        return True  # All time

    async def get_dashboard_summary(self, period: str) -> Dict[str, Any]:
        """Get high-level dashboard stats."""
        date_filter_app = self._get_date_filter(period, models.Appointment.date_time)
        date_filter_pay = self._get_date_filter(period, models.Payment.date)
        date_filter_patient = self._get_date_filter(period, models.Patient.created_at)

        # 1. Total Patients
        stmt_tot = select(func.count(models.Patient.id)).where(models.Patient.tenant_id == self.tenant_id)
        total_patients = await self.db.scalar(stmt_tot) or 0

        # 2. New Patients
        stmt_new = select(func.count(models.Patient.id)).where(
            models.Patient.tenant_id == self.tenant_id,
            date_filter_patient
        )
        new_patients = await self.db.scalar(stmt_new) or 0

        # 3. Appointments
        stmt_app = (
            select(func.count(models.Appointment.id))
            .join(models.Patient)
            .where(models.Patient.tenant_id == self.tenant_id, date_filter_app)
        )
        period_appointments = await self.db.scalar(stmt_app) or 0

        # 4. Revenue
        stmt_rev = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient)
            .where(models.Patient.tenant_id == self.tenant_id, date_filter_pay)
        )
        period_revenue = await self.db.scalar(stmt_rev) or 0

        return {
            "period": period,
            "total_patients": total_patients,
            "new_patients": new_patients,
            "period_appointments": period_appointments,
            "period_revenue": float(period_revenue),
        }

    async def get_clinic_summary(self) -> Dict[str, Any]:
        """Get clinic info and counts."""
        stmt_tenant = select(models.Tenant).where(models.Tenant.id == self.tenant_id)
        tenant = (await self.db.execute(stmt_tenant)).scalar_one_or_none()
        if not tenant:
            return None

        stmt_users = select(func.count(models.User.id)).where(models.User.tenant_id == self.tenant_id)
        users_count = await self.db.scalar(stmt_users) or 0

        stmt_patients = select(func.count(models.Patient.id)).where(models.Patient.tenant_id == self.tenant_id)
        patients_count = await self.db.scalar(stmt_patients) or 0

        return {
            "name": tenant.name,
            "logo": tenant.logo,
            "users_count": users_count,
            "patients_count": patients_count,
            "subscription_status": tenant.subscription_status,
            "created_at": str(tenant.created_at),
        }

    async def get_ai_stats(self, period: str) -> Dict[str, Any]:
        """Get AI usage statistics."""
        stmt = select(models.AIUsageLog).where(
            models.AIUsageLog.tenant_id == self.tenant_id
        )

        # Date Filter
        if period == "week":
            start_date = datetime.now() - timedelta(days=7)
            stmt = stmt.where(models.AIUsageLog.created_at >= start_date)
        elif period == "month":
            start_date = datetime.now() - timedelta(days=30)
            stmt = stmt.where(models.AIUsageLog.created_at >= start_date)
        elif period == "today":
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            stmt = stmt.where(models.AIUsageLog.created_at >= today_start)

        res = await self.db.execute(stmt)
        logs = res.scalars().all()

        total_requests = len(logs)
        success_count = sum(1 for log in logs if log.success)
        avg_latency = (
            sum(log.response_time_ms for log in logs) / total_requests
            if total_requests > 0
            else 0
        )

        # Top tools
        tool_counts = {}
        for log in logs:
            if log.response_tool:
                tool_counts[log.response_tool] = (
                    tool_counts.get(log.response_tool, 0) + 1
                )

        top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "period": period,
            "total": total_requests,
            "success": success_count,
            "avg_latency": avg_latency,
            "top_tools": [{"name": k, "count": v} for k, v in top_tools],
        }

    async def compare_periods(
        self, period1: str, period2: str, metric: str
    ) -> Dict[str, Any]:
        """Compare two periods."""

        def get_range(p_name):
            t = date.today()
            if p_name == "this_week":
                return t - timedelta(days=7), t
            if p_name == "last_week":
                return t - timedelta(days=14), t - timedelta(days=7)
            if p_name == "this_month":
                return t - timedelta(days=30), t
            if p_name == "last_month":
                return t - timedelta(days=60), t - timedelta(days=30)
            # Default fallback
            return t - timedelta(days=30), t

        start1, end1 = get_range(period1)
        start2, end2 = get_range(period2)

        async def calculate_metric(s, e):
            if metric == "revenue":
                stmt = (
                    select(func.sum(models.Payment.amount))
                    .join(models.Patient)
                    .where(
                        models.Patient.tenant_id == self.tenant_id,
                        models.Payment.date >= datetime.combine(s, datetime.min.time()),
                        models.Payment.date < datetime.combine(e, datetime.min.time()),
                    )
                )
                return await self.db.scalar(stmt) or 0
            elif metric == "patients":
                stmt = (
                    select(func.count(models.Patient.id))
                    .where(
                        models.Patient.tenant_id == self.tenant_id,
                        models.Patient.created_at
                        >= datetime.combine(s, datetime.min.time()),
                        models.Patient.created_at
                        < datetime.combine(e, datetime.min.time()),
                    )
                )
                return await self.db.scalar(stmt) or 0
            else:  # appointments
                stmt = (
                    select(func.count(models.Appointment.id))
                    .join(models.Patient)
                    .where(
                        models.Patient.tenant_id == self.tenant_id,
                        models.Appointment.date_time
                        >= datetime.combine(s, datetime.min.time()),
                        models.Appointment.date_time
                        < datetime.combine(e, datetime.min.time()),
                    )
                )
                return await self.db.scalar(stmt) or 0

        val1 = await calculate_metric(start1, end1)
        val2 = await calculate_metric(start2, end2)

        change_pct = 0
        if val2 > 0:
            change_pct = ((val1 - val2) / val2) * 100
        elif val1 > 0:
            change_pct = 100

        return {
            "metric": metric,
            "period1": {"name": period1, "value": float(val1)},
            "period2": {"name": period2, "value": float(val2)},
            "change_percent": change_pct,
        }
