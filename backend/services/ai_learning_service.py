"""
AI Learning & Feedback Service

Centralizes the logic for analyzing AI logs to detect:
1. High Failure Rates
2. Latency Bottlenecks
3. Low Confidence Queries (Ambiguity)

Extracts insights to suggest improvements to prompts, tools, or UI.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, case, select

from backend import models

logger = logging.getLogger(__name__)


class AILearningService:
    """Service to analyze AI performance and generate optimization suggestions."""

    def __init__(self, db: AsyncSession, tenant_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id

    async def generate_suggestions(self, days: int = 30) -> List[Dict[str, str]]:
        """
        Analyzes historical data to suggest optimizations.
        Phase 4: AI Improvement Suggestions Engine.
        """
        suggestions = []
        start_time = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            # 1. Analyze High Failure Rates (> 15% failure rate, min 5 requests)
            stmt_tool_stats = (
                select(
                    models.AILog.tool,
                    func.count(models.AILog.id).label("total"),
                    func.sum(case((models.AILog.status != "SUCCESS", 1), else_=0)).label("failures"),
                )
                .filter(models.AILog.timestamp >= start_time)
            )

            if self.tenant_id:
                stmt_tool_stats = stmt_tool_stats.filter(models.AILog.tenant_id == self.tenant_id)

            stmt_tool_stats = stmt_tool_stats.group_by(models.AILog.tool).having(func.count(models.AILog.id) > 5)
            result_tool_stats = await self.db.execute(stmt_tool_stats)
            tool_stats = result_tool_stats.all()

            for tool, total, failures in tool_stats:
                fail_rate = (failures / total) * 100
                if fail_rate > 15:
                    suggestions.append({
                        "type": "CRITICAL",
                        "tool": tool or "unknown",
                        "message": f"High failure rate detected for '{tool}' ({int(fail_rate)}%).",
                        "action": "Check input schema validation or prompt examples.",
                        "impact": "Reliability"
                    })

            # 2. Analyze Latency Bottlenecks (> 4000ms average execution time)
            stmt_slow_tools = (
                select(
                    models.AILog.tool,
                    func.avg(models.AILog.execution_time_ms).label("avg_time"),
                )
                .filter(models.AILog.timestamp >= start_time)
            )

            if self.tenant_id:
                stmt_slow_tools = stmt_slow_tools.filter(models.AILog.tenant_id == self.tenant_id)

            stmt_slow_tools = stmt_slow_tools.group_by(models.AILog.tool).having(func.avg(models.AILog.execution_time_ms) > 4000)
            result_slow_tools = await self.db.execute(stmt_slow_tools)
            slow_tools = result_slow_tools.all()

            for tool, avg_time in slow_tools:
                suggestions.append({
                    "type": "WARNING",
                    "tool": tool or "unknown",
                    "message": f"Slow response time for '{tool}' (~{int((avg_time or 0) / 1000)}s).",
                    "action": "Consider simplifying the prompt or moving to async processing.",
                    "impact": "User Experience"
                })

            # 3. Analyze Low Confidence (Ambiguity)
            stmt_low_conf = (
                select(
                    models.AILog.tool,
                    func.count(models.AILog.id).label("total"),
                    func.sum(case((models.AILog.confidence < 0.6, 1), else_=0)).label("low_conf_count"),
                )
                .filter(models.AILog.timestamp >= start_time)
            )

            if self.tenant_id:
                stmt_low_conf = stmt_low_conf.filter(models.AILog.tenant_id == self.tenant_id)

            stmt_low_conf = stmt_low_conf.group_by(models.AILog.tool).having(func.count(models.AILog.id) > 10)
            result_low_conf = await self.db.execute(stmt_low_conf)
            low_conf_tools = result_low_conf.all()

            for tool, total, low_conf in low_conf_tools:
                low_conf_val = low_conf if low_conf else 0
                low_rate = (low_conf_val / total) * 100 if total > 0 else 0
                if low_rate > 20:
                    suggestions.append({
                        "type": "OPTIMIZATION",
                        "tool": tool or "unknown",
                        "message": f"AI is uncertain about '{tool}' ({int(low_rate)}% Low Confidence).",
                        "action": "Add more Few-Shot examples to the system prompt.",
                        "impact": "Accuracy"
                    })

            # 4. Global Suggestion (if everything is fine)
            if not suggestions:
                suggestions.append({
                    "type": "INFO",
                    "tool": "System",
                    "message": "System is performing well. No critical issues detected.",
                    "action": "Monitor usage trends for future scaling.",
                    "impact": "Maintenance"
                })

            return suggestions

        except Exception as e:
            logger.error(f"Error generating AI suggestions: {e}", exc_info=True)
            return [{
                "type": "ERROR",
                "tool": "System",
                "message": "Failed to analyze AI logs for suggestions.",
                "action": "Inspect system logs to resolve DB/Analytics query errors.",
                "impact": "Monitoring"
            }]


def get_ai_learning_service(db: AsyncSession, tenant_id: Optional[int] = None) -> AILearningService:
    return AILearningService(db, tenant_id)
