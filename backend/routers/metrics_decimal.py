"""Decimal-safe profitability route layered over the current metrics router."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from importlib import import_module

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.money import as_decimal, quantize_money
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from backend.models import User
from backend.services.inventory_decimal_service import inventory_service_decimal

_base = import_module("backend.routers.metrics")

router = _base.router
router.routes[:] = [
    route
    for route in router.routes
    if not (
        getattr(route, "path", None) == "/metrics/profitability"
        and "GET" in getattr(route, "methods", set())
    )
]

# Preserve compatibility symbols used by security/regression tests and callers.
_require_platform_metrics = _base._require_platform_metrics
inventory_service = inventory_service_decimal


def _money_json(value) -> float:
    return float(quantize_money(as_decimal(value)))


def build_profitability_payload(
    period: str,
    revenue,
    expenses,
    lab_costs,
    material_costs,
) -> dict:
    revenue_d = as_decimal(revenue)
    expenses_d = as_decimal(expenses)
    lab_costs_d = as_decimal(lab_costs)
    material_costs_d = as_decimal(material_costs)
    total_costs = expenses_d + lab_costs_d + material_costs_d
    net_profit = revenue_d - total_costs
    margin_percent = (
        net_profit / revenue_d * Decimal("100")
        if revenue_d > 0
        else Decimal("0")
    )
    return {
        "period": period,
        "revenue": _money_json(revenue_d),
        "breakdown": {
            "expenses": _money_json(expenses_d),
            "lab_costs": _money_json(lab_costs_d),
            "material_costs": _money_json(material_costs_d),
        },
        "total_costs": _money_json(total_costs),
        "net_profit": _money_json(net_profit),
        "margin_percent": float(margin_percent.quantize(Decimal("0.1"))),
    }


@router.get("/profitability")
async def get_profitability(
    period: str = "30d",
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    tenant_id = require_tenant_id(current_user)
    now = datetime.now(timezone.utc)
    if period == "24h":
        start_date = now - timedelta(hours=24)
    elif period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=30)

    revenue = as_decimal(
        (
            await db.execute(
                select(func.sum(models.Payment.amount))
                .join(models.Patient, models.Payment.patient_id == models.Patient.id)
                .where(
                    models.Payment.date >= start_date,
                    models.Patient.tenant_id == tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                )
            )
        ).scalar()
    )
    expenses = as_decimal(
        (
            await db.execute(
                select(func.sum(models.Expense.cost)).where(
                    models.Expense.date >= start_date.date(),
                    models.Expense.tenant_id == tenant_id,
                )
            )
        ).scalar()
    )
    lab_costs = as_decimal(
        (
            await db.execute(
                select(func.sum(models.LabOrder.cost)).where(
                    models.LabOrder.order_date >= start_date,
                    models.LabOrder.tenant_id == tenant_id,
                )
            )
        ).scalar()
    )
    material_costs = await inventory_service.get_cogs_summary(
        start_date=start_date,
        end_date=now,
        tenant_id=tenant_id,
        db=db,
    )
    return success_response(
        data=build_profitability_payload(
            period,
            revenue,
            expenses,
            lab_costs,
            material_costs,
        )
    )


for _name in dir(_base):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_base, _name)
