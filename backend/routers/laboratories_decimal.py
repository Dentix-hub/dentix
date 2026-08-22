"""Decimal-safe laboratory statistics layered over the current lab router."""

from decimal import Decimal

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.money import as_decimal, quantize_money
from backend.core.permissions import Permission, require_permission
from backend.database import get_async_db

from . import laboratories as _base

router = _base.router
router.routes[:] = [
    route
    for route in router.routes
    if not (
        getattr(route, "path", None) == "/laboratories/{lab_id}/stats"
        and "GET" in getattr(route, "methods", set())
    )
]


def _money_json(value) -> float:
    return float(quantize_money(as_decimal(value)))


def build_lab_stats_payload(
    *,
    lab_id: int,
    lab_name: str,
    total_orders: int,
    pending_orders: int,
    completed_orders: int,
    total_cost,
    total_revenue,
    total_paid,
) -> dict:
    """Build lab totals using Decimal even when one aggregate is empty."""
    total_cost_d = as_decimal(total_cost)
    total_revenue_d = as_decimal(total_revenue)
    total_paid_d = as_decimal(total_paid)
    balance = total_cost_d - total_paid_d
    return {
        "lab_id": lab_id,
        "lab_name": lab_name,
        "total_orders": int(total_orders),
        "pending_orders": int(pending_orders),
        "completed_orders": int(completed_orders),
        "total_cost": _money_json(total_cost_d),
        "total_revenue": _money_json(total_revenue_d),
        "total_paid": _money_json(total_paid_d),
        "balance": _money_json(balance),
    }


@router.get("/laboratories/{lab_id}/stats")
async def get_lab_stats(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    base_query_stmt = select(models.LabOrder).where(
        models.LabOrder.laboratory_id == lab_id,
        models.LabOrder.tenant_id == current_user.tenant_id,
    )
    total_orders = await db.scalar(
        select(func.count()).select_from(base_query_stmt.subquery())
    ) or 0
    pending_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "pending").subquery()
        )
    ) or 0
    completed_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "completed").subquery()
        )
    ) or 0
    total_cost = as_decimal(
        await db.scalar(
            select(func.sum(models.LabOrder.cost)).where(
                models.LabOrder.laboratory_id == lab_id,
                models.LabOrder.tenant_id == current_user.tenant_id,
            )
        )
    )
    total_revenue = as_decimal(
        await db.scalar(
            select(func.sum(models.LabOrder.price_to_patient)).where(
                models.LabOrder.laboratory_id == lab_id,
                models.LabOrder.tenant_id == current_user.tenant_id,
            )
        )
    )
    total_paid = as_decimal(
        await db.scalar(
            select(func.sum(models.LabPayment.amount)).where(
                models.LabPayment.laboratory_id == lab_id,
                models.LabPayment.tenant_id == current_user.tenant_id,
            )
        )
    )

    return build_lab_stats_payload(
        lab_id=lab_id,
        lab_name=lab.name,
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        total_cost=total_cost,
        total_revenue=total_revenue,
        total_paid=total_paid,
    )


for _name in dir(_base):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_base, _name)
