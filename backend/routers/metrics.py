"""Metrics router facade with tenant-local Finance trend semantics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from backend.models import User
from backend.services.tenant_time_service import get_tenant_timezone
from backend.utils.tenant_time import (
    resolve_timezone,
    tenant_day_utc_bounds_naive,
    tenant_local_date,
)

from . import metrics_legacy as _legacy

router = _legacy.router
router.routes[:] = [
    route
    for route in router.routes
    if not (
        getattr(route, "path", None) == "/metrics/profitability/trend"
        and "GET" in getattr(route, "methods", set())
    )
]


def _parse_local_date(value: str, field_name: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}; expected YYYY-MM-DD",
        ) from exc


@router.get("/profitability/trend")
async def get_profitability_trend(
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Return daily Collected vs Manual Expenses for the exact tenant-local range."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    tenant_id = require_tenant_id(current_user)
    timezone_name = await get_tenant_timezone(db, tenant_id)
    tenant_tz = resolve_timezone(timezone_name)

    if bool(start_date) != bool(end_date):
        raise HTTPException(
            status_code=400,
            detail="Both start_date and end_date are required when filtering by date",
        )

    if start_date and end_date:
        start_day = _parse_local_date(start_date, "start_date")
        end_day = _parse_local_date(end_date, "end_date")
        if end_day < start_day:
            raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    else:
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        end_day = tenant_local_date(timezone_name)
        start_day = end_day - timedelta(days=days - 1)

    utc_start, _ = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=start_day,
    )
    _, utc_end_exclusive = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=end_day,
    )

    payment_rows = (
        await db.execute(
            select(models.Payment.date, models.Payment.amount)
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= utc_start,
                models.Payment.date < utc_end_exclusive,
            )
        )
    ).all()

    collected_by_day: dict[str, float] = {}
    for timestamp, amount in payment_rows:
        if timestamp is None:
            continue
        aware_utc = (
            timestamp.replace(tzinfo=timezone.utc)
            if timestamp.tzinfo is None
            else timestamp.astimezone(timezone.utc)
        )
        key = aware_utc.astimezone(tenant_tz).date().isoformat()
        collected_by_day[key] = collected_by_day.get(key, 0.0) + float(amount or 0.0)

    expense_rows = (
        await db.execute(
            select(
                models.Expense.date.label("day"),
                func.coalesce(func.sum(models.Expense.cost), 0.0).label("amount"),
            )
            .where(
                models.Expense.tenant_id == tenant_id,
                models.Expense.date >= start_day,
                models.Expense.date <= end_day,
            )
            .group_by(models.Expense.date)
        )
    ).all()
    expenses_by_day = {
        day.isoformat(): float(amount or 0.0)
        for day, amount in expense_rows
        if day is not None
    }

    timeline = []
    day = start_day
    while day <= end_day:
        key = day.isoformat()
        collected = collected_by_day.get(key, 0.0)
        expenses = expenses_by_day.get(key, 0.0)
        timeline.append(
            {
                "date": key,
                "revenue": round(collected, 2),
                "expenses": round(expenses, 2),
                "net_profit": round(collected - expenses, 2),
            }
        )
        day += timedelta(days=1)

    return success_response(
        data={
            "period": period,
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "timeline": timeline,
        }
    )


for _name in dir(_legacy):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_legacy, _name)
