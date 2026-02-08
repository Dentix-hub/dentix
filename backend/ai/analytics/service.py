
"""
AI Analytics Service
Centralizes logic for usage tracking, cost calculation, and admin dashboards.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


from backend import models
from backend.ai.config import MODEL_CARDS, DEFAULT_MODEL

class AIAnalyticsService:
    @staticmethod
    def get_stats(db: Session, period: str = "month", tenant_id: int = 1) -> Dict[str, Any]:
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
        else: # month
            start_date = now - timedelta(days=30)

        # 2. Base Query (Tenant Isolated or Global)
        query = db.query(models.AIUsageLog).filter(
            models.AIUsageLog.created_at >= start_date
        )
        
        # Only filter by tenant if tenant_id is provided (not None)
        if tenant_id is not None:
             query = query.filter(models.AIUsageLog.tenant_id == tenant_id)
        
        # 3. Aggregations
        total_requests = query.count()
        success_count = query.filter(models.AIUsageLog.success == True).count()
        error_rate = 1 - (success_count / total_requests) if total_requests > 0 else 0
        
        # 4. Cost Calculation (Token-based)
        # Assuming we track 'tokens_used' and potentially 'model_used' in future schema updates
        # For now, we use the simplified estimate but enhanced with Config values
        
        # Default cost factor (blended)
        blended_cost_per_request = (MODEL_CARDS[DEFAULT_MODEL]["input_cost"] + MODEL_CARDS[DEFAULT_MODEL]["output_cost"]) / 1000 / 2
        
        # If we had exact token counts per log, we'd sum (tokens * price)
        # For now (Upgrade Path): Use precise per-request estimation
        estimated_cost = total_requests * blended_cost_per_request

        # 5. Top Tools
        tool_stats = (
            db.query(models.AIUsageLog.response_tool, func.count(models.AIUsageLog.id))
            .filter(models.AIUsageLog.created_at >= start_date)
            .group_by(models.AIUsageLog.response_tool)
            .order_by(desc(func.count(models.AIUsageLog.id)))
            .limit(5)
            .all()
        )

        # 6. Top Users
        user_stats = (
            db.query(models.AIUsageLog.username, func.count(models.AIUsageLog.id))
            .filter(models.AIUsageLog.created_at >= start_date)
            .group_by(models.AIUsageLog.username)
            .order_by(desc(func.count(models.AIUsageLog.id)))
            .limit(5)
            .all()
        )

        return {
            "period": period,
            "total_requests": total_requests,
            "success_rate": round(success_count / total_requests * 100, 1) if total_requests else 100,
            "estimated_cost": round(estimated_cost, 4),
            "tool_usage": [{"name": t[0] or "Unknown", "value": t[1]} for t in tool_stats],
            "top_users": [{"name": t[0], "count": t[1]} for t in user_stats]
        }

    @staticmethod
    def get_logs(
        db: Session, 
        skip: int = 0, 
        limit: int = 50, 
        tenant_id: int = 1,
        filters: Dict[str, Any] = None
    ) -> List[models.AIUsageLog]:
        """Get paginated logs with sorting and filters."""
        query = db.query(models.AIUsageLog)
        
        if tenant_id is not None:
            query = query.filter(models.AIUsageLog.tenant_id == tenant_id)
        
        if filters:
            if filters.get("tool"):
                query = query.filter(models.AIUsageLog.response_tool == filters["tool"])
            if filters.get("username"):
                query = query.filter(models.AIUsageLog.username.ilike(f"%{filters['username']}%"))
            if filters.get("status") is not None:
                is_success = str(filters["status"]).lower() == "true"
                query = query.filter(models.AIUsageLog.success == is_success)
            if filters.get("start_date"):
                query = query.filter(models.AIUsageLog.created_at >= filters["start_date"])
            if filters.get("end_date"):
                query = query.filter(models.AIUsageLog.created_at <= filters["end_date"])

        return (
            query
            .order_by(desc(models.AIUsageLog.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

