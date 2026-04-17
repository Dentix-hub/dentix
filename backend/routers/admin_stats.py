"""
Admin Stats Router.

Handles admin dashboard statistics endpoints.
Split from admin_system.py (B3.1).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from backend import models, schemas
from backend.database import get_db
from backend.core.permissions import Role, Permission, require_permission
from backend.services.cache_service import cached

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/admin",
    tags=["Admin — Stats"],
    responses={404: {"description": "Not found"}},
)


def require_super_admin(
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# --- Dashboard Stats ---
@router.get("/stats", response_model=schemas.AdminDashboardStats)
def get_admin_dashboard_stats(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get admin dashboard statistics (Cached 5 mins)."""
    return _get_admin_stats_logic(db)


@cached(key_prefix="admin_dashboard_stats", expire=300)
def _get_admin_stats_logic(db: Session):
    total_tenants = db.query(models.Tenant).count()
    active_tenants = (
        db.query(models.Tenant).filter(models.Tenant.is_active).count()
    )
    expired_tenants = (
        db.query(models.Tenant)
        .filter(models.Tenant.subscription_end_date < datetime.now(timezone.utc))
        .count()
    )

    total_revenue = db.query(func.sum(models.SubscriptionPayment.amount)).scalar() or 0

    recent_payments = (
        db.query(models.SubscriptionPayment)
        .order_by(models.SubscriptionPayment.payment_date.desc())
        .limit(10)
        .all()
    )

    plan_distribution = {}
    plans = (
        db.query(models.Tenant.plan, func.count(models.Tenant.id))
        .group_by(models.Tenant.plan)
        .all()
    )
    for plan_name, count in plans:
        plan_distribution[plan_name or "trial"] = count

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "expired_tenants": expired_tenants,
        "total_revenue": float(total_revenue),
        "monthly_revenue": {},
        "plan_distribution": plan_distribution,
        "recent_payments": recent_payments,
    }
