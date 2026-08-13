"""
Metrics API Endpoint for Smart Clinic.
Exposes application metrics for monitoring dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.core.permissions import Permission, require_permission
from typing import Dict, Any
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


@router.get("/stats")
async def get_metrics_stats(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get application metrics and statistics.

    Requires authentication (admin or super_admin role).
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return success_response(data=metrics.get_stats())


@router.get("/alerts")
async def get_active_alerts(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get current active alerts.

    Returns any threshold violations.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    alerts = metrics.check_alerts()
    return success_response(data={"alerts": alerts, "count": len(alerts)})


@router.get("/business")
async def get_business_metrics(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get business-specific metrics.

    Returns patient counts, appointment stats, etc.
    """
    if current_user.role not in ["admin", "super_admin", "doctor"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

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
    """
    Get Net Profit Breakdown (Revenue - Expenses - Labs - Materials).
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Calculate Dates
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

    # 1. Revenue (Payments)
    # Include both current tenant and NULL tenant_id (legacy data compatibility)
    revenue_result = await db.execute(
        select(func.sum(models.Payment.amount))
        .filter(
            models.Payment.date >= start_date,
            (models.Payment.tenant_id == current_user.tenant_id) | (models.Payment.tenant_id.is_(None)),
        )
    )
    revenue = revenue_result.scalar() or 0.0

    # 2. Expenses (OpEx)
    expenses_result = await db.execute(
        select(func.sum(models.Expense.cost))
        .filter(
            models.Expense.date >= start_date.date(),
            models.Expense.tenant_id == current_user.tenant_id,
        )
    )
    expenses = expenses_result.scalar() or 0.0

    # 3. Labs (COGS 1) - Based on Order Date (Committed Cost)
    lab_costs_result = await db.execute(
        select(func.sum(models.LabOrder.cost))
        .filter(
            models.LabOrder.order_date >= start_date,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    )
    lab_costs = lab_costs_result.scalar() or 0.0

    # 4. Material (COGS 2)
    material_costs = await inventory_service.get_cogs_summary(
        start_date=start_date, end_date=now, tenant_id=current_user.tenant_id, db=db
    )

    # Previous period calculation for comparison
    period_days = 30
    if period == "24h":
        period_days = 1
    elif period == "7d":
        period_days = 7
    elif period == "30d":
        period_days = 30
    elif period == "90d":
        period_days = 90

    prev_start_date = start_date - timedelta(days=period_days)
    prev_end_date = start_date

    prev_revenue_res = await db.execute(
        select(func.sum(models.Payment.amount))
        .filter(
            models.Payment.date >= prev_start_date,
            models.Payment.date < prev_end_date,
            (models.Payment.tenant_id == current_user.tenant_id) | (models.Payment.tenant_id.is_(None)),
        )
    )
    prev_revenue = prev_revenue_res.scalar() or 0.0

    prev_exp_res = await db.execute(
        select(func.sum(models.Expense.cost))
        .filter(
            models.Expense.date >= prev_start_date.date(),
            models.Expense.date < prev_end_date.date(),
            models.Expense.tenant_id == current_user.tenant_id,
        )
    )
    prev_expenses = prev_exp_res.scalar() or 0.0

    prev_lab_res = await db.execute(
        select(func.sum(models.LabOrder.cost))
        .filter(
            models.LabOrder.order_date >= prev_start_date,
            models.LabOrder.order_date < prev_end_date,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    )
    prev_lab_costs = prev_lab_res.scalar() or 0.0

    prev_material_costs = await inventory_service.get_cogs_summary(
        start_date=prev_start_date, end_date=prev_end_date, tenant_id=current_user.tenant_id, db=db
    )
    prev_total_costs = prev_expenses + prev_lab_costs + prev_material_costs
    prev_net_profit = prev_revenue - prev_total_costs

    # Net Profit
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
        "previous_period": {
            "revenue": round(prev_revenue, 2),
            "expenses": round(prev_expenses, 2),
            "lab_costs": round(prev_lab_costs, 2),
            "material_costs": round(prev_material_costs, 2),
            "total_costs": round(prev_total_costs, 2),
            "net_profit": round(prev_net_profit, 2),
        }
    })


@router.get("/profitability/trend")
async def get_profitability_trend(
    period: str = "30d",
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get daily trend breakdown of revenue, expenses, and net profit over time.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    now = datetime.now(timezone.utc)
    days_count = 30
    if period == "7d":
        days_count = 7
    elif period == "30d":
        days_count = 30
    elif period == "90d":
        days_count = 90
    elif period == "24h":
        days_count = 1

    start_date = now - timedelta(days=days_count)

    # Daily payments
    payments_res = await db.execute(
        select(
            func.date(models.Payment.date).label("pay_date"),
            func.sum(models.Payment.amount).label("daily_rev")
        )
        .filter(
            models.Payment.date >= start_date,
            (models.Payment.tenant_id == current_user.tenant_id) | (models.Payment.tenant_id.is_(None)),
        )
        .group_by(func.date(models.Payment.date))
    )
    payments_map = {str(row.pay_date): float(row.daily_rev or 0) for row in payments_res.all()}

    # Daily expenses
    expenses_res = await db.execute(
        select(
            models.Expense.date.label("exp_date"),
            func.sum(models.Expense.cost).label("daily_exp")
        )
        .filter(
            models.Expense.date >= start_date.date(),
            models.Expense.tenant_id == current_user.tenant_id,
        )
        .group_by(models.Expense.date)
    )
    expenses_map = {str(row.exp_date): float(row.daily_exp or 0) for row in expenses_res.all()}

    # Build timeline points
    timeline = []
    for i in range(days_count + 1):
        day_dt = (start_date + timedelta(days=i)).date()
        day_str = str(day_dt)
        rev = payments_map.get(day_str, 0.0)
        exp = expenses_map.get(day_str, 0.0)
        net = rev - exp
        timeline.append({
            "date": day_str,
            "revenue": round(rev, 2),
            "expenses": round(exp, 2),
            "net_profit": round(net, 2)
        })

    return success_response(data={"period": period, "timeline": timeline})
