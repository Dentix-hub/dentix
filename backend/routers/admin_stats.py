"""
Admin Stats Router.

Handles admin dashboard statistics endpoints.
Split from admin_system.py (B3.1).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.core.response import success_response, StandardResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from backend import models, schemas
from backend.database import get_async_db
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
async def get_admin_dashboard_stats(
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get admin dashboard statistics (Cached 5 mins)."""
    return await _get_admin_stats_logic(db)


@cached(key_prefix="admin_dashboard_stats", expire=300)
async def _get_admin_stats_logic(db: AsyncSession):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Total non-archived tenants
    stmt = select(func.count(models.Tenant.id)).where(models.Tenant.is_deleted == False)  # noqa: E712
    total_tenants = (await db.execute(stmt)).scalar() or 0

    # Operational active tenants: active, not deleted, and subscription not expired
    stmt = select(func.count(models.Tenant.id)).where(
        models.Tenant.is_deleted == False,  # noqa: E712
        models.Tenant.is_active == True,  # noqa: E712
        (models.Tenant.subscription_end_date.is_(None)) | (models.Tenant.subscription_end_date >= now)
    )
    active_tenants = (await db.execute(stmt)).scalar() or 0

    # Expired tenants: not deleted, but subscription end date is in the past
    stmt = select(func.count(models.Tenant.id)).where(
        models.Tenant.is_deleted == False,  # noqa: E712
        models.Tenant.subscription_end_date.is_not(None),
        models.Tenant.subscription_end_date < now
    )
    expired_tenants = (await db.execute(stmt)).scalar() or 0

    # Total revenue from all payments
    stmt = select(func.sum(models.SubscriptionPayment.amount))
    total_revenue = (await db.execute(stmt)).scalar() or 0


    # Monthly revenue calculation (Last 12 months window with missing months zero-filled)
    month_keys = []
    current_year = now.year
    current_month = now.month
    for i in range(11, -1, -1):
        m = current_month - i
        y = current_year
        while m <= 0:
            m += 12
            y -= 1
        month_keys.append(f"{y:04d}-{m:02d}")

    start_date_12m = datetime(int(month_keys[0].split("-")[0]), int(month_keys[0].split("-")[1]), 1)

    monthly_revenue = {k: 0.0 for k in month_keys}
    stmt = (
        select(models.SubscriptionPayment)
        .where(models.SubscriptionPayment.payment_date >= start_date_12m)
        .order_by(models.SubscriptionPayment.payment_date.asc())
    )
    payments = (await db.execute(stmt)).scalars().all()
    for p in payments:
        if p.payment_date:
            month_key = p.payment_date.strftime("%Y-%m")
            if month_key in monthly_revenue:
                monthly_revenue[month_key] += float(p.amount or 0)


    # Clinic growth calculation (Last 12 months)
    clinic_growth = {k: 0 for k in month_keys}
    stmt = (
        select(models.Tenant)
        .where(
            models.Tenant.is_deleted == False,  # noqa: E712
            models.Tenant.created_at >= start_date_12m
        )
        .order_by(models.Tenant.created_at.asc())
    )
    tenants_raw = (await db.execute(stmt)).scalars().all()
    for t in tenants_raw:
        if t.created_at:
            month_key = t.created_at.strftime("%Y-%m")
            if month_key in clinic_growth:
                clinic_growth[month_key] += 1


    # Activity Feed Logic
    activity_feed = []

    # 1. Recent Tenants
    stmt = select(models.Tenant).options(selectinload(models.Tenant.subscription_plan)).order_by(models.Tenant.created_at.desc()).limit(5)
    recent_tenants = (await db.execute(stmt)).scalars().all()
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
    stmt = select(models.SubscriptionPayment).options(selectinload(models.SubscriptionPayment.tenant)).order_by(models.SubscriptionPayment.payment_date.desc()).limit(5)
    recent_payments_raw = (await db.execute(stmt)).scalars().all()
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
    stmt = select(models.SystemError).order_by(models.SystemError.created_at.desc()).limit(5)
    recent_errors = (await db.execute(stmt)).scalars().all()
    for e in recent_errors:
        activity_feed.append({
            "id": e.id,
            "type": "error",
            "title": f"خطأ في النظام: {e.level}",
            "description": e.message[:100] + "..." if len(e.message) > 100 else e.message,
            "timestamp": e.created_at,
            "status": "error",
            "link": "/admin/system/logs"
        })

    # Sort Activity Feed by timestamp descending
    activity_feed.sort(key=lambda x: x["timestamp"], reverse=True)
    activity_feed = activity_feed[:20]

    # Plan distribution
    plan_distribution = {}
    stmt = (
        select(models.SubscriptionPlan.name, func.count(models.Tenant.id))
        .join(models.Tenant, models.Tenant.plan_id == models.SubscriptionPlan.id)
        .group_by(models.SubscriptionPlan.name)
    )
    plans = (await db.execute(stmt)).all()
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
async def get_financial_reports(
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get detailed financial reports for admin.
    1. Revenue by plan.
    2. Overdue clinics.
    3. Revenue forecast (active unexpired subscriptions only).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Revenue by Plan
    stmt = (
        select(models.SubscriptionPlan.display_name_ar, func.sum(models.SubscriptionPayment.amount))
        .join(models.SubscriptionPayment, models.SubscriptionPayment.plan_id == models.SubscriptionPlan.id)
        .group_by(models.SubscriptionPlan.display_name_ar)
    )
    revenue_by_plan = (await db.execute(stmt)).all()
    revenue_plan_data = [{"name": r[0], "value": float(r[1] or 0)} for r in revenue_by_plan]

    # 2. Overdue Clinics (Expired and non-deleted)
    stmt = (
        select(models.Tenant)
        .options(selectinload(models.Tenant.subscription_plan))
        .where(
            models.Tenant.is_deleted == False,  # noqa: E712
            models.Tenant.subscription_end_date.is_not(None),
            models.Tenant.subscription_end_date < now
        )
        .order_by(models.Tenant.subscription_end_date.asc())
        .limit(50)
    )
    overdue_clinics_raw = (await db.execute(stmt)).scalars().all()
    overdue_clinics = [
        {
            "id": t.id,
            "name": t.name,
            "expiry_date": t.subscription_end_date,
            "days_overdue": max(0, (now - (t.subscription_end_date.replace(tzinfo=None) if t.subscription_end_date else now)).days),
            "plan_name": t.subscription_plan.display_name_ar if t.subscription_plan else "بدون خطة"
        }
        for t in overdue_clinics_raw
    ]

    # 3. Revenue Forecast (Estimated monthly revenue from active unexpired non-deleted subscriptions)
    stmt = (
        select(func.sum(models.SubscriptionPlan.price))
        .join(models.Tenant, models.Tenant.plan_id == models.SubscriptionPlan.id)
        .where(
            models.Tenant.is_deleted == False,  # noqa: E712
            models.Tenant.is_active == True,  # noqa: E712
            (models.Tenant.subscription_end_date.is_(None)) | (models.Tenant.subscription_end_date >= now)
        )
    )
    forecast_data = float((await db.execute(stmt)).scalar() or 0.0)

    # 4. Growth Trends (Monthly Revenue last 6 months)
    six_months_ago = now - timedelta(days=180)
    stmt = (
        select(models.SubscriptionPayment)
        .where(models.SubscriptionPayment.payment_date >= six_months_ago)
        .order_by(models.SubscriptionPayment.payment_date.asc())
    )
    six_months_payments = (await db.execute(stmt)).scalars().all()
    monthly_trends = {}
    for p in six_months_payments:
        if p.payment_date:
            m_key = p.payment_date.strftime("%Y-%m")
            monthly_trends[m_key] = monthly_trends.get(m_key, 0.0) + float(p.amount or 0)
    trends = [{"month": k, "revenue": v} for k, v in sorted(monthly_trends.items())]


    # 5. Churn Risks (Active non-deleted clinics with no activity in last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    # Using UserSession to check activity
    active_tenant_ids_stmt = (
        select(models.User.tenant_id)
        .join(models.UserSession, models.User.id == models.UserSession.user_id)
        .where(models.UserSession.last_active_at >= thirty_days_ago)
        .distinct()
    )
    active_tenant_ids_rows = (await db.execute(active_tenant_ids_stmt)).all()
    active_ids = [r[0] for r in active_tenant_ids_rows if r[0] is not None]

    stmt = (
        select(models.Tenant)
        .options(selectinload(models.Tenant.subscription_plan))
        .where(
            models.Tenant.is_deleted == False,  # noqa: E712
            models.Tenant.is_active == True,  # noqa: E712
            ~models.Tenant.id.in_(active_ids)
        )
        .limit(20)
    )
    churn_risks_raw = (await db.execute(stmt)).scalars().all()

    churn_risks = []
    for t in churn_risks_raw:
        last_active_stmt = (
            select(func.max(models.UserSession.last_active_at))
            .join(models.User, models.User.id == models.UserSession.user_id)
            .where(models.User.tenant_id == t.id)
        )
        last_active = (await db.execute(last_active_stmt)).scalar()
        churn_risks.append({
            "id": t.id,
            "name": t.name,
            "last_active": last_active,
            "plan_name": t.subscription_plan.display_name_ar if t.subscription_plan else "بدون خطة"
        })

    return success_response({
        "revenue_by_plan": revenue_plan_data,
        "overdue_clinics": overdue_clinics,
        "monthly_forecast": float(forecast_data),
        "growth_trends": trends,
        "churn_risks": churn_risks
    })


@router.get("/health/alerts")
async def get_system_health_alerts(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """
    Get system health status and alerts for the super admin dashboard.
    """
    from backend.services.health_monitoring_service import HealthMonitoringService
    return await HealthMonitoringService.calculate_health_score(db)


@router.post("/health/check")
async def trigger_system_health_check(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """
    Trigger a manual health check and send notifications if score is low.
    """
    from backend.services.health_monitoring_service import HealthMonitoringService
    notified = await HealthMonitoringService.check_and_notify(db)
    health = await HealthMonitoringService.calculate_health_score(db)

    return success_response({
        "health": health,
        "notification_sent": notified
    })


@router.post("/business/check")
async def trigger_business_health_check(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """
    Trigger a manual business health check (expiring subscriptions, churn risks).
    """
    from backend.services.business_alerts_service import BusinessAlertsService
    results = await BusinessAlertsService.run_all_checks(db)

    return success_response(results)
