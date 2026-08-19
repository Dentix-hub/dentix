"""
Metrics API Endpoint for Smart Clinic.

Exposes application metrics for monitoring dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.core.permissions import Permission, require_permission
from backend.core.tenant_context import require_tenant_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone

from backend.core.monitoring import metrics
from backend.models import User
from backend import models
from backend.database import get_async_db
from backend.services.inventory_service import inventory_service
from backend.core.response import success_response

router = APIRouter(prefix="/metrics", tags=["Metrics"])


def _require_platform_metrics(current_user: User) -> None:
    """Global process telemetry is a platform-admin surface, not clinic analytics."""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.get("/stats")
async def get_metrics_stats(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get global application telemetry for platform administration."""
    _require_platform_metrics(current_user)
    return success_response(data=metrics.get_stats())


@router.get("/alerts")
async def get_active_alerts(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get current global monitoring alerts."""
    _require_platform_metrics(current_user)
    alerts = metrics.check_alerts()
    return success_response(data={"alerts": alerts, "count": len(alerts)})


@router.get("/business")
async def get_business_metrics(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get global in-process business counters for platform administration."""
    # MetricsCollector business counters are process-global and have no tenant
    # dimension. Exposing them to clinic users would leak cross-tenant counts and
    # payment totals, so this endpoint is intentionally platform-only.
    _require_platform_metrics(current_user)
    stats = metrics.get_stats()
    return success_response(data={
        "business_metrics": stats.get("business_metrics", {}),
        "timestamp": stats.get("timestamp"),
    })


@router.get("/profitability")
async def get_profitability(
    period: str = "30d",
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get tenant-scoped Net Profit Breakdown (Revenue - Expenses - Labs - Materials)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    tenant_id = require_tenant_id(current_user)

    now = datetime.now(timezone.utc)
    if period == "24h":
        start_date = now - timedelta(hours=24)
    elif period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=30)

    # Attribute payments through their tenant-owned patient. This preserves
    # legacy payments with tenant_id=NULL without treating all NULL payments as
    # globally visible to every clinic.
    revenue_result = await db.execute(
        select(func.sum(models.Payment.amount))
        .join(models.Patient, models.Payment.patient_id == models.Patient.id)
        .where(
            models.Payment.date >= start_date,
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    revenue = revenue_result.scalar() or 0.0

    expenses_result = await db.execute(
        select(func.sum(models.Expense.cost)).where(
            models.Expense.date >= start_date.date(),
            models.Expense.tenant_id == tenant_id,
        )
    )
    expenses = expenses_result.scalar() or 0.0

    lab_costs_result = await db.execute(
        select(func.sum(models.LabOrder.cost)).where(
            models.LabOrder.order_date >= start_date,
            models.LabOrder.tenant_id == tenant_id,
        )
    )
    lab_costs = lab_costs_result.scalar() or 0.0

    material_costs = await inventory_service.get_cogs_summary(
        start_date=start_date,
        end_date=now,
        tenant_id=tenant_id,
        db=db,
    )

    total_costs = expenses + lab_costs + material_costs
    net_profit = revenue - total_costs
    margin_percent = (net_profit / revenue * 100) if revenue > 0 else 0.0

    return success_response(data={
        "period": period,
        "revenue": round(revenue, 2),
        "breakdown": {
            "expenses": round(expenses, 2),
            "lab_costs": round(lab_costs, 2),
            "material_costs": round(material_costs, 2),
        },
        "total_costs": round(total_costs, 2),
        "net_profit": round(net_profit, 2),
        "margin_percent": round(margin_percent, 1),
    })


@router.get("/profitability/trend")
async def get_profitability_trend(
    period: str = "30d",
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Return the tenant-scoped Finance V2 daily Collected vs Manual Expenses trend."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    tenant_id = require_tenant_id(current_user)

    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    end_day = datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=days - 1)
    start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_day, datetime.max.time(), tzinfo=timezone.utc)

    payment_day = func.date(models.Payment.date)
    payment_rows = (
        await db.execute(
            select(
                payment_day.label("day"),
                func.coalesce(func.sum(models.Payment.amount), 0.0).label("amount"),
            )
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= start_dt,
                models.Payment.date <= end_dt,
            )
            .group_by(payment_day)
        )
    ).all()

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

    def day_key(value) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)[:10]

    collected_by_day = {day_key(day): float(amount or 0.0) for day, amount in payment_rows}
    expenses_by_day = {day_key(day): float(amount or 0.0) for day, amount in expense_rows}

    timeline = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
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

    return success_response(data={"period": period, "timeline": timeline})
