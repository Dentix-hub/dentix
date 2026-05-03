"""
Monitoring and Metrics for Smart Clinic.

This module provides:
- Prometheus metrics collection
- Business metrics tracking
- Performance monitoring
- Alert thresholds

Usage:
    from backend.core.monitoring import metrics

    # Record a metric
    metrics.record_request("/api/patients", "GET", 200, 0.05)

    # Get metrics
    stats = metrics.get_stats()
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from collections import defaultdict
from dataclasses import dataclass, field
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """Single request metric record."""

    path: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """
    Collects and aggregates application metrics.

    Thread-safe metrics collection for monitoring and alerting.
    """

    def __init__(self, retention_minutes: int = 60):
        self._lock = threading.Lock()
        self._retention = timedelta(minutes=retention_minutes)

        # Request metrics
        self._requests: list[RequestMetric] = []
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)

        # Business metrics
        self._business_metrics: Dict[str, int] = defaultdict(int)

        # Timing metrics
        self._durations: Dict[str, list[float]] = defaultdict(list)

    def record_request(
        self, path: str, method: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record an HTTP request metric."""
        with self._lock:
            duration_ms = duration_seconds * 1000

            metric = RequestMetric(
                path=path,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            self._requests.append(metric)

            # Update counts
            key = f"{method}:{path}"
            self._request_counts[key] += 1

            if status_code >= 400:
                self._error_counts[key] += 1

            # Track durations
            self._durations[key].append(duration_ms)

            # Cleanup old metrics
            self._cleanup()

    def record_business_event(self, event_type: str, count: int = 1) -> None:
        """Record a business metric event."""
        with self._lock:
            self._business_metrics[event_type] += count

    def _cleanup(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.now(timezone.utc) - self._retention
        self._requests = [r for r in self._requests if r.timestamp > cutoff]

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        with self._lock:
            now = datetime.now(timezone.utc)
            last_minute = now - timedelta(minutes=1)
            last_5_minutes = now - timedelta(minutes=5)

            recent_requests = [r for r in self._requests if r.timestamp > last_minute]
            recent_5min = [r for r in self._requests if r.timestamp > last_5_minutes]

            # Calculate rates
            rpm = len(recent_requests)
            errors_1min = len([r for r in recent_requests if r.status_code >= 400])
            error_rate = (errors_1min / rpm * 100) if rpm > 0 else 0

            # Calculate latencies
            durations = [r.duration_ms for r in recent_5min]
            if durations:
                avg_latency = sum(durations) / len(durations)
                sorted_durations = sorted(durations)
                p95_idx = int(len(sorted_durations) * 0.95)
                p95_latency = (
                    sorted_durations[p95_idx] if p95_idx < len(sorted_durations) else 0
                )
            else:
                avg_latency = 0
                p95_latency = 0

            return {
                "requests_per_minute": rpm,
                "error_rate_percent": round(error_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "total_requests": sum(self._request_counts.values()),
                "total_errors": sum(self._error_counts.values()),
                "business_metrics": dict(self._business_metrics),
                "top_endpoints": self._get_top_endpoints(5),
                "timestamp": now.isoformat(),
            }

    def _get_top_endpoints(self, limit: int) -> list:
        """Get top N endpoints by request count."""
        sorted_endpoints = sorted(
            self._request_counts.items(), key=lambda x: x[1], reverse=True
        )[:limit]

        return [{"endpoint": k, "count": v} for k, v in sorted_endpoints]

    def check_alerts(self) -> list[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        stats = self.get_stats()

        # Error rate alert
        if stats["error_rate_percent"] > 5:
            alerts.append(
                {
                    "level": "ERROR",
                    "message": f"High error rate: {stats['error_rate_percent']}%",
                    "metric": "error_rate",
                    "value": stats["error_rate_percent"],
                }
            )

        # Latency alert
        if stats["p95_latency_ms"] > 2000:
            alerts.append(
                {
                    "level": "WARNING",
                    "message": f"High P95 latency: {stats['p95_latency_ms']}ms",
                    "metric": "p95_latency",
                    "value": stats["p95_latency_ms"],
                }
            )

        return alerts


# Singleton instance
metrics = MetricsCollector()


# ============================================
# BUSINESS METRICS HELPERS
# ============================================


def track_patient_created():
    """Track patient creation event."""
    metrics.record_business_event("patient_created")


def track_appointment_scheduled():
    """Track appointment scheduling event."""
    metrics.record_business_event("appointment_scheduled")


def track_payment_received(amount: float):
    """Track payment received."""
    metrics.record_business_event("payment_received")
    metrics.record_business_event("payment_amount", int(amount))


def track_ai_query():
    """Track AI assistant query."""
    metrics.record_business_event("ai_query")
