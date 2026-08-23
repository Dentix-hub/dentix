"""Server-owned Finance V2 analytical report and export helpers.

PR6 intentionally keeps report calculations on the server.  React consumers
render these values but do not recreate authoritative financial formulas.
"""

from __future__ import annotations

import csv
from datetime import timedelta
from io import StringIO
from typing import Any, Dict, Iterable, Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.finance_summary_service import FinanceSummaryService


CSV_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_text(value: Any) -> Any:
    """Neutralize spreadsheet formulas without converting numeric values to text."""
    if not isinstance(value, str):
        return value
    if value.startswith(CSV_DANGEROUS_PREFIXES):
        return f"'{value}"
    return value


def build_csv_document(
    *,
    columns: Sequence[tuple[str, str]],
    rows: Iterable[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> str:
    """Return a UTF-8 CSV document whose user-controlled text is formula-safe."""
    stream = StringIO(newline="")
    writer = csv.writer(stream)

    for key, value in (metadata or {}).items():
        writer.writerow([sanitize_csv_text(str(key)), sanitize_csv_text(value)])
    if metadata:
        writer.writerow([])

    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow(
            [sanitize_csv_text(row.get(field, "")) for field, _ in columns]
        )
    return stream.getvalue()


class FinanceReportService:
    """Analytical reports derived from the Finance Summary source of truth."""

    METRIC_PATHS = {
        "net_invoiced": ("income", "net_revenue"),
        "collected": ("income", "total_collected"),
        "manual_expenses": ("deductions", "expenses"),
        "lab_costs": ("deductions", "lab_costs"),
        "doctor_dues": ("deductions", "doctor_dues", "total"),
        "staff_dues": ("deductions", "staff_dues", "total"),
        "total_deductions": ("deductions", "total_deductions"),
        "net_operational_result": ("net_operational_result",),
    }

    def __init__(self, db: AsyncSession, tenant_id: int) -> None:
        self.summary = FinanceSummaryService(db, tenant_id)

    @staticmethod
    def _value(payload: Dict[str, Any], path: Sequence[str]) -> float:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict):
                return 0.0
            value = value.get(key)
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    async def get_period_comparison(
        self,
        *,
        start_date: str,
        end_date: str,
        compare_start_date: str | None = None,
        compare_end_date: str | None = None,
    ) -> Dict[str, Any]:
        """Compare one explicit tenant-local period to another equal-length range."""
        current_period = await self.summary.resolve_period(start_date, end_date)

        if bool(compare_start_date) != bool(compare_end_date):
            raise ValueError(
                "Both compare_start_date and compare_end_date are required together"
            )

        if compare_start_date and compare_end_date:
            comparison_period = await self.summary.resolve_period(
                compare_start_date,
                compare_end_date,
            )
        else:
            period_days = (
                current_period.local_end - current_period.local_start
            ).days + 1
            comparison_end = current_period.local_start - timedelta(days=1)
            comparison_start = comparison_end - timedelta(days=period_days - 1)
            comparison_period = await self.summary.resolve_period(
                comparison_start.isoformat(),
                comparison_end.isoformat(),
            )

        current = await self.summary.get_summary(
            start_date=current_period.local_start.isoformat(),
            end_date=current_period.local_end.isoformat(),
        )
        comparison = await self.summary.get_summary(
            start_date=comparison_period.local_start.isoformat(),
            end_date=comparison_period.local_end.isoformat(),
        )

        metrics = []
        for metric_id, path in self.METRIC_PATHS.items():
            current_value = self._value(current, path)
            comparison_value = self._value(comparison, path)
            delta = current_value - comparison_value
            delta_percent = (
                round((delta / abs(comparison_value)) * 100, 2)
                if comparison_value != 0
                else None
            )
            metrics.append(
                {
                    "metric": metric_id,
                    "current": round(current_value, 2),
                    "comparison": round(comparison_value, 2),
                    "delta": round(delta, 2),
                    "delta_percent": delta_percent,
                }
            )

        return {
            "definition_version": current.get("definition_version"),
            "currency": current.get("currency", "EGP"),
            "current_period": current_period.metadata(),
            "comparison_period": comparison_period.metadata(),
            "metrics": metrics,
            "metric_definitions": current.get("metric_definitions", {}),
        }
