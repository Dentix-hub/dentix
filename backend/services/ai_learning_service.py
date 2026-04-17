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
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, case

from backend import models

logger = logging.getLogger(__name__)


class AILearningService:
    """Service to analyze AI performance and generate optimization suggestions."""

    def __init__(self, db: Session, tenant_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id

    def generate_suggestions(self, days: int = 30) -> List[Dict[str, str]]:
        """
        Analyzes historical data to suggest optimizations.
        Phase 4: AI Improvement Suggestions Engine.
        """
        suggestions = []
        start_time = datetime.utcnow() - timedelta(days=days)

        try:
            # 1. Analyze High Failure Rates (> 15% failure rate, min 5 requests)
            tool_stats_query = self.db.query(
                models.AILog.tool,
                func.count(models.AILog.id).label("total"),
                func.sum(case((models.AILog.status != "SUCCESS", 1), else_=0)).label("failures"),
            ).filter(models.AILog.timestamp >= start_time)

            if self.tenant_id:
                tool_stats_query = tool_stats_query.filter(models.AILog.tenant_id == self.tenant_id)

            tool_stats = tool_stats_query.group_by(models.AILog.tool).having(func.count(models.AILog.id) > 5).all()

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
            slow_tools_query = self.db.query(
                models.AILog.tool,
                func.avg(models.AILog.execution_time_ms).label("avg_time"),
            ).filter(models.AILog.timestamp >= start_time)

            if self.tenant_id:
                slow_tools_query = slow_tools_query.filter(models.AILog.tenant_id == self.tenant_id)

            slow_tools = slow_tools_query.group_by(models.AILog.tool).having(func.avg(models.AILog.execution_time_ms) > 4000).all()

            for tool, avg_time in slow_tools:
                suggestions.append({
                    "type": "WARNING",
                    "tool": tool or "unknown",
                    "message": f"Slow response time for '{tool}' (~{int((avg_time or 0) / 1000)}s).",
                    "action": "Consider simplifying the prompt or moving to async processing.",
                    "impact": "User Experience"
                })

            # 3. Analyze Low Confidence (Ambiguity)
            low_conf_query = self.db.query(
                models.AILog.tool,
                func.count(models.AILog.id).label("total"),
                func.sum(case((models.AILog.confidence < 0.6, 1), else_=0)).label("low_conf_count"),
            ).filter(models.AILog.timestamp >= start_time)

            if self.tenant_id:
                low_conf_query = low_conf_query.filter(models.AILog.tenant_id == self.tenant_id)

            low_conf_tools = low_conf_query.group_by(models.AILog.tool).having(func.count(models.AILog.id) > 10).all()

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

def get_ai_learning_service(db: Session, tenant_id: Optional[int] = None) -> AILearningService:
    return AILearningService(db, tenant_id)
