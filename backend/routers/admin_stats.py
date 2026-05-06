"""
Admin Stats Router.

Handles admin dashboard statistics endpoints.
Split from admin_system.py (B3.1).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.core.response import success_response, StandardResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

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
@router.get("/stats", response_model=StandardResponse[schemas.AdminDashboardStats])
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

    # Total revenue from all payments
    total_revenue = db.query(func.sum(models.SubscriptionPayment.amount)).scalar() or 0

    # Monthly revenue calculation (Last 12 months)
    monthly_revenue = {}
    payments = db.query(models.SubscriptionPayment).order_by(models.SubscriptionPayment.payment_date.asc()).all()
    for p in payments:
        if p.payment_date:
            month_key = p.payment_date.strftime("%Y-%m")
            monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + (p.amount or 0)

    # Clinic growth calculation
    clinic_growth = {}
    tenants_raw = db.query(models.Tenant).order_by(models.Tenant.created_at.asc()).all()
    for t in tenants_raw:
        if t.created_at:
            month_key = t.created_at.strftime("%Y-%m")
            clinic_growth[month_key] = clinic_growth.get(month_key, 0) + 1

    # Activity Feed Logic
    activity_feed = []

    # 1. Recent Tenants
    recent_tenants = db.query(models.Tenant).order_by(models.Tenant.created_at.desc()).limit(5).all()
    for t in recent_tenants:
        activity_feed.append({
            "id": t.id,
            "type": "tenant",
            "title": f"عيادة جديدة: {t.name}",
            "description": f"تم تسجيل عيادة جديدة بخطة {t.subscription_plan.name if t.subscription_plan else (t.plan or 'تجريبية')}",
            "timestamp": t.created_at,
            "status": "success",
            "link": f"/admin/tenants?id={t.id}"
        })

    # 2. Recent Payments
    recent_payments_raw = db.query(models.SubscriptionPayment).order_by(models.SubscriptionPayment.payment_date.desc()).limit(5).all()
    for p in recent_payments_raw:
        activity_feed.append({
            "id": p.id,
            "type": "payment",
            "title": f"دفعة جديدة: {p.amount} ج.م",
            "description": f"دفعة من عيادة {p.tenant.name if p.tenant else 'غير معروفة'}",
            "timestamp": p.payment_date,
            "status": "success",
            "link": "/admin/finance"
        })

    # 3. Recent Errors
    recent_errors = db.query(models.SystemError).order_by(models.SystemError.created_at.desc()).limit(5).all()
    for e in recent_errors:
        activity_feed.append({
            "id": e.id,
            "type": "error",
            "title": f"خطأ في النظام: {e.level}",
            "description": e.message[:100] + "..." if len(e.message) > 100 else e.message,
            "timestamp": e.created_at,
            "status": "error",
            "link": "/admin/system"
        })

    # Sort Activity Feed by timestamp descending
    activity_feed.sort(key=lambda x: x["timestamp"], reverse=True)
    activity_feed = activity_feed[:20]

    # Plan distribution
    plan_distribution = {}
    plans = (
        db.query(models.SubscriptionPlan.name, func.count(models.Tenant.id))
        .join(models.Tenant, models.Tenant.plan_id == models.SubscriptionPlan.id)
        .group_by(models.SubscriptionPlan.name)
        .all()
    )
    for plan_name, count in plans:
        plan_distribution[plan_name] = count

    return success_response({
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "expired_tenants": expired_tenants,
        "total_revenue": float(total_revenue),
        "monthly_revenue": monthly_revenue,
        "clinic_growth": clinic_growth,
        "plan_distribution": plan_distribution,
        "recent_payments": recent_payments_raw,
        "activity_feed": activity_feed
    })


@router.get("/finance/reports")
def get_financial_reports(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Get detailed financial reports for admin.
    1. Revenue by plan.
    2. Overdue clinics.
    3. Revenue forecast.
    """
    now = datetime.now(timezone.utc)

    # 1. Revenue by Plan
    revenue_by_plan = (
        db.query(models.SubscriptionPlan.display_name_ar, func.sum(models.SubscriptionPayment.amount))
        .join(models.SubscriptionPayment, models.SubscriptionPayment.plan_id == models.SubscriptionPlan.id)
        .group_by(models.SubscriptionPlan.display_name_ar)
        .all()
    )
    revenue_plan_data = [{"name": r[0], "value": float(r[1] or 0)} for r in revenue_by_plan]

    # 2. Overdue Clinics (Expired but not paid for renewal)
    overdue_clinics_raw = (
        db.query(models.Tenant)
        .filter(models.Tenant.subscription_end_date < now)
        .filter(models.Tenant.is_active == True)
        .order_by(models.Tenant.subscription_end_date.asc())
        .limit(50)
        .all()
    )
    overdue_clinics = [
        {
            "id": t.id,
            "name": t.name,
            "expiry_date": t.subscription_end_date,
            "days_overdue": (now - t.subscription_end_date.replace(tzinfo=timezone.utc) if t.subscription_end_date.tzinfo is None else now - t.subscription_end_date).days,
            "plan_name": t.subscription_plan.display_name_ar if t.subscription_plan else "بدون خطة"
        }
        for t in overdue_clinics_raw
    ]

    # 3. Revenue Forecast (Estimated monthly revenue from active subscriptions)
    # Simple logic: sum of (active tenant's plan price)
    forecast_data = (
        db.query(func.sum(models.SubscriptionPlan.price))
        .join(models.Tenant, models.Tenant.plan_id == models.SubscriptionPlan.id)
        .filter(models.Tenant.is_active == True)
        .scalar() or 0
    )

    # 4. Growth Trends (Monthly Revenue last 6 months)
    six_months_ago = now - timedelta(days=180)
    monthly_trends = (
        db.query(
            func.date_trunc('month', models.SubscriptionPayment.payment_date).label('month'),
            func.sum(models.SubscriptionPayment.amount)
        )
        .filter(models.SubscriptionPayment.payment_date >= six_months_ago)
        .group_by('month')
        .order_by('month')
        .all()
    )
    trends = [{"month": r[0].strftime("%Y-%m"), "revenue": float(r[1] or 0)} for r in monthly_trends]

    # 5. Churn Risks (Clinics with no activity in last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    # Using UserSession to check activity
    active_tenant_ids = (
        db.query(models.User.tenant_id)
        .join(models.UserSession, models.User.id == models.UserSession.user_id)
        .filter(models.UserSession.last_active_at >= thirty_days_ago)
        .distinct()
    )

    churn_risks_raw = (
        db.query(models.Tenant)
        .filter(models.Tenant.is_active == True)
        .filter(~models.Tenant.id.in_(active_tenant_ids))
        .limit(20)
        .all()
    )
    churn_risks = [
        {
            "id": t.id,
            "name": t.name,
            "last_active": (
                db.query(func.max(models.UserSession.last_active_at))
                .join(models.User, models.User.id == models.UserSession.user_id)
                .filter(models.User.tenant_id == t.id)
                .scalar()
            ),
            "plan_name": t.subscription_plan.display_name_ar if t.subscription_plan else "بدون خطة"
        }
        for t in churn_risks_raw
    ]

    return success_response({
        "revenue_by_plan": revenue_plan_data,
        "overdue_clinics": overdue_clinics,
        "monthly_forecast": float(forecast_data),
        "growth_trends": trends,
        "churn_risks": churn_risks
    })


@router.get("/health/alerts")
def get_system_health_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """
    Get system health status and alerts for the super admin dashboard.
    """
    from backend.services.health_monitoring_service import HealthMonitoringService
    return HealthMonitoringService.calculate_health_score(db)


@router.post("/health/check")
def trigger_system_health_check(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """
    Trigger a manual health check and send notifications if score is low.
    """
    from backend.services.health_monitoring_service import HealthMonitoringService
    notified = HealthMonitoringService.check_and_notify(db)
    health = HealthMonitoringService.calculate_health_score(db)

    return success_response({
        "health": health,
        "notification_sent": notified
    })


@router.post("/business/check")
def trigger_business_health_check(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """
    Trigger a manual business health check (expiring subscriptions, churn risks).
    """
    from backend.services.business_alerts_service import BusinessAlertsService
    results = BusinessAlertsService.run_all_checks(db)

    return success_response(results)
