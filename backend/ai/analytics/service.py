"""
AI Analytics Service
Centralizes logic for usage tracking, cost calculation, and admin dashboards.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from datetime import datetime, timedelta
from typing import Dict, Any, List


from backend import models
from backend.ai.config import MODEL_CARDS, DEFAULT_MODEL


class AIAnalyticsService:
    @staticmethod
    async def get_stats(
        db: AsyncSession, period: str = "month", tenant_id: int = 1
    ) -> Dict[str, Any]:
        """
        Get aggregated AI usage stats.
        Includes precise cost calculation based on model definition.
        """
        # 1. Determine Date Range
        now = datetime.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)

        # 2. Base Queries using select
        total_requests_stmt = select(func.count(models.AIUsageLog.id)).filter(
            models.AIUsageLog.created_at >= start_date
        )
        success_count_stmt = select(func.count(models.AIUsageLog.id)).filter(
            models.AIUsageLog.created_at >= start_date,
            models.AIUsageLog.status == "SUCCESS"
        )

        # Only filter by tenant if tenant_id is provided (not None)
        if tenant_id is not None:
            total_requests_stmt = total_requests_stmt.filter(models.AIUsageLog.tenant_id == tenant_id)
            success_count_stmt = success_count_stmt.filter(models.AIUsageLog.tenant_id == tenant_id)

        # Execute
        total_requests = (await db.execute(total_requests_stmt)).scalar() or 0
        success_count = (await db.execute(success_count_stmt)).scalar() or 0

        # Cost Calculation
        blended_cost_per_request = (
            (
                MODEL_CARDS[DEFAULT_MODEL]["input_cost"]
                + MODEL_CARDS[DEFAULT_MODEL]["output_cost"]
            )
            / 1000
            / 2
        )
        estimated_cost = total_requests * blended_cost_per_request

        # 5. Top Tools
        stmt_tool = (
            select(models.AIUsageLog.tool, func.count(models.AIUsageLog.id))
            .filter(models.AIUsageLog.created_at >= start_date)
            .group_by(models.AIUsageLog.tool)
            .order_by(desc(func.count(models.AIUsageLog.id)))
            .limit(5)
        )
        res_tool = await db.execute(stmt_tool)
        tool_stats = res_tool.all()

        # 6. Top Users
        stmt_user = (
            select(models.AIUsageLog.username, func.count(models.AIUsageLog.id))
            .filter(models.AIUsageLog.created_at >= start_date)
            .group_by(models.AIUsageLog.username)
            .order_by(desc(func.count(models.AIUsageLog.id)))
            .limit(5)
        )
        res_user = await db.execute(stmt_user)
        user_stats = res_user.all()

        # 7. Usage Trends (Last 30 days)
        trend_start = now - timedelta(days=30)
        stmt_trend = (
            select(
                func.date(models.AIUsageLog.created_at).label("day"),
                func.count(models.AIUsageLog.id)
            )
            .filter(models.AIUsageLog.created_at >= trend_start)
            .group_by(func.date(models.AIUsageLog.created_at))
            .order_by(func.date(models.AIUsageLog.created_at))
        )
        res_trend = await db.execute(stmt_trend)
        daily_trends = res_trend.all()

        return {
            "period": period,
            "total_requests": total_requests,
            "success_rate": round(success_count / total_requests * 100, 1)
            if total_requests
            else 100,
            "estimated_cost": round(estimated_cost, 4),
            "tool_usage": [
                {"name": t[0] or "Unknown", "value": t[1]} for t in tool_stats
            ],
            "top_users": [{"name": t[0], "count": t[1]} for t in user_stats],
            "usage_trends": [{"date": str(t[0]), "count": t[1]} for t in daily_trends],
        }

    @staticmethod
    async def get_logs(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        tenant_id: int = 1,
        filters: Dict[str, Any] = None,
    ) -> List[models.AIUsageLog]:
        """Get paginated logs with sorting and filters."""
        stmt = select(models.AIUsageLog)

        if tenant_id is not None:
            stmt = stmt.filter(models.AIUsageLog.tenant_id == tenant_id)

        if filters:
            if filters.get("tool"):
                stmt = stmt.filter(models.AIUsageLog.response_tool == filters["tool"])
            if filters.get("username"):
                stmt = stmt.filter(
                    models.AIUsageLog.username.ilike(f"%{filters['username']}%")
                )
            if filters.get("status") is not None:
                is_success = str(filters["status"]).lower() == "true"
                status_val = "SUCCESS" if is_success else "FAILURE"
                stmt = stmt.filter(models.AIUsageLog.status == status_val)
            if filters.get("start_date"):
                stmt = stmt.filter(
                    models.AIUsageLog.created_at >= filters["start_date"]
                )
            if filters.get("end_date"):
                stmt = stmt.filter(
                    models.AIUsageLog.created_at <= filters["end_date"]
                )

        stmt = stmt.order_by(desc(models.AIUsageLog.created_at)).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return res.scalars().all()
