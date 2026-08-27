"""
AI Analytics Service
Centralizes logic for usage tracking, cost calculation, and admin dashboards.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from fastapi import HTTPException

from backend import models
from backend.ai.config import MODEL_CARDS, DEFAULT_MODEL

VALID_PERIODS = {"today", "week", "month"}


class AIAnalyticsService:
    @staticmethod
    async def get_stats(
        db: AsyncSession, period: str = "month", tenant_id: int = None
    ) -> Dict[str, Any]:
        """
        Get aggregated AI usage stats.
        Includes precise cost calculation based on recorded cost or model definition.
        """
        if period not in VALID_PERIODS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period '{period}'. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
            )

        # 1. Determine Date Range
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
            models.AIUsageLog.status == "SUCCESS",
        )
        cost_sum_stmt = select(func.sum(models.AIUsageLog.cost)).filter(
            models.AIUsageLog.created_at >= start_date
        )

        # Only filter by tenant if tenant_id is provided (not None)
        if tenant_id is not None:
            total_requests_stmt = total_requests_stmt.filter(models.AIUsageLog.tenant_id == tenant_id)
            success_count_stmt = success_count_stmt.filter(models.AIUsageLog.tenant_id == tenant_id)
            cost_sum_stmt = cost_sum_stmt.filter(models.AIUsageLog.tenant_id == tenant_id)

        # Execute
        total_requests = (await db.execute(total_requests_stmt)).scalar() or 0
        success_count = (await db.execute(success_count_stmt)).scalar() or 0
        recorded_cost = (await db.execute(cost_sum_stmt)).scalar()

        # Cost Calculation: Prefer recorded cost sum if available, else estimate
        if recorded_cost is not None and float(recorded_cost) > 0:
            final_cost = float(recorded_cost)
        else:
            blended_cost_per_request = (
                (
                    MODEL_CARDS[DEFAULT_MODEL]["input_cost"]
                    + MODEL_CARDS[DEFAULT_MODEL]["output_cost"]
                )
                / 1000
                / 2
            )
            final_cost = total_requests * blended_cost_per_request

        # 5. Top Tools
        stmt_tool = (
            select(models.AIUsageLog.tool, func.count(models.AIUsageLog.id))
            .filter(models.AIUsageLog.created_at >= start_date)
        )
        if tenant_id is not None:
            stmt_tool = stmt_tool.filter(models.AIUsageLog.tenant_id == tenant_id)
        stmt_tool = (
            stmt_tool.group_by(models.AIUsageLog.tool)
            .order_by(desc(func.count(models.AIUsageLog.id)))
            .limit(5)
        )
        res_tool = await db.execute(stmt_tool)
        tool_stats = res_tool.all()

        # 6. Top Users
        stmt_user = (
            select(models.AIUsageLog.username, func.count(models.AIUsageLog.id))
            .filter(models.AIUsageLog.created_at >= start_date)
        )
        if tenant_id is not None:
            stmt_user = stmt_user.filter(models.AIUsageLog.tenant_id == tenant_id)
        stmt_user = (
            stmt_user.group_by(models.AIUsageLog.username)
            .order_by(desc(func.count(models.AIUsageLog.id)))
            .limit(5)
        )
        res_user = await db.execute(stmt_user)
        user_stats = res_user.all()

        # 7. Usage Trends (obeys requested period bounds)
        stmt_trend = (
            select(
                func.date(models.AIUsageLog.created_at).label("day"),
                func.count(models.AIUsageLog.id),
            )
            .filter(models.AIUsageLog.created_at >= start_date)
        )
        if tenant_id is not None:
            stmt_trend = stmt_trend.filter(models.AIUsageLog.tenant_id == tenant_id)
        stmt_trend = (
            stmt_trend.group_by(func.date(models.AIUsageLog.created_at))
            .order_by(func.date(models.AIUsageLog.created_at))
        )
        res_trend = await db.execute(stmt_trend)
        daily_trends = res_trend.all()

        return {
            "period": period,
            "total_requests": total_requests,
            "success_rate": round(success_count / total_requests * 100, 1)
            if total_requests > 0
            else None,
            "estimated_cost": round(final_cost, 4),
            "tool_usage": [
                {"name": t[0] or "Unknown", "value": t[1]} for t in tool_stats
            ],
            "top_users": [{"name": t[0] or "Unknown", "count": t[1]} for t in user_stats],
            "usage_trends": [{"date": str(t[0]), "count": t[1]} for t in daily_trends],
        }

    @staticmethod
    async def get_logs(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        tenant_id: int = None,
        filters: Dict[str, Any] = None,
    ) -> List[models.AIUsageLog]:
        """Get paginated logs with sorting and filters."""
        stmt = select(models.AIUsageLog)

        if tenant_id is not None:
            stmt = stmt.filter(models.AIUsageLog.tenant_id == tenant_id)

        if filters:
            if filters.get("tool"):
                stmt = stmt.filter(models.AIUsageLog.tool == filters["tool"])
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
        return list(res.scalars().all())
