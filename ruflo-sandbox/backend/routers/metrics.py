"""
Metrics API Endpoint for Smart Clinic.

Exposes application metrics for monitoring dashboards.
"""

from fastapi import APIRouter, Depends
from backend.core.permissions import Permission, require_permission
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from backend.core.monitoring import metrics
from backend.models import User
from backend import models
from backend.database import get_db
from backend.services.inventory_service import inventory_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/stats")
async def get_metrics_stats(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
) -> Dict[str, Any]:
    """
    Get application metrics and statistics.

    Requires authentication (admin or super_admin role).
    """
    if current_user.role not in ["admin", "super_admin"]:
        return {"error": "Insufficient permissions"}

    return metrics.get_stats()


@router.get("/alerts")
async def get_active_alerts(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
) -> Dict[str, Any]:
    """
    Get current active alerts.

    Returns any threshold violations.
    """
    if current_user.role not in ["admin", "super_admin"]:
        return {"error": "Insufficient permissions"}

    alerts = metrics.check_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/business")
async def get_business_metrics(
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
) -> Dict[str, Any]:
    """
    Get business-specific metrics.

    Returns patient counts, appointment stats, etc.
    """
    if current_user.role not in ["admin", "super_admin", "doctor"]:
        return {"error": "Insufficient permissions"}

    stats = metrics.get_stats()
    return {
        "business_metrics": stats.get("business_metrics", {}),
        "timestamp": stats.get("timestamp"),
    }


@router.get("/profitability")
def get_profitability(
    period: str = "30d",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get Net Profit Breakdown (Revenue - Expenses - Labs - Materials).
    """
    if current_user.role not in ["admin", "super_admin"]:
        return {"error": "Insufficient permissions"}

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
    revenue = (
        db.query(func.sum(models.Payment.amount))
        .filter(
            models.Payment.date >= start_date,
            models.Payment.tenant_id == current_user.tenant_id,
        )
        .scalar()
        or 0.0
    )

    # 2. Expenses (OpEx)
    expenses = (
        db.query(func.sum(models.Expense.cost))
        .filter(
            models.Expense.date >= start_date.date(),
            models.Expense.tenant_id == current_user.tenant_id,
        )
        .scalar()
        or 0.0
    )

    # 3. Labs (COGS 1) - Based on Order Date (Committed Cost)
    lab_costs = (
        db.query(func.sum(models.LabOrder.cost))
        .filter(
            models.LabOrder.order_date >= start_date,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        .scalar()
        or 0.0
    )

    # 4. Material (COGS 2)
    material_costs = inventory_service.get_cogs_summary(
        start_date=start_date, end_date=now, tenant_id=current_user.tenant_id, db=db
    )

    # Net Profit
    total_costs = expenses + lab_costs + material_costs
    net_profit = revenue - total_costs
    margin_percent = (net_profit / revenue * 100) if revenue > 0 else 0.0

    return {
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
    }
