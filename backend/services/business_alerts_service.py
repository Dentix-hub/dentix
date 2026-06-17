from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .. import models
from .internal_notification_service import InternalNotificationService

logger = logging.getLogger("smart_clinic")

class BusinessAlertsService:
    @staticmethod
    async def check_expiring_subscriptions(db: AsyncSession):
        """
        Find clinics with subscriptions expiring in 7, 3, or 1 days and notify admins.
        """
        now = datetime.now(timezone.utc)
        thresholds = [7, 3, 1]
        alerts_sent = 0

        for days in thresholds:
            # Calculate range for the entire day (target_date)
            target_date = (now + timedelta(days=days)).date()
            start_range = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
            end_range = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)

            stmt = select(models.Tenant).where(
                models.Tenant.subscription_end_date >= start_range,
                models.Tenant.subscription_end_date <= end_range,
                models.Tenant.is_active == True  # noqa: E712
            )
            tenants = (await db.execute(stmt)).scalars().all()

            for t in tenants:
                title = f"تنبيه اشتراك: عيادة {t.name}"
                body = f"اشتراك عيادة {t.name} ينتهي خلال {days} أيام ({t.subscription_end_date.strftime('%Y-%m-%d')}). يرجى التواصل معهم للتجديد."
                await InternalNotificationService.notify_super_admins(db, title, body)
                alerts_sent += 1
                logger.info(f"Subscription alert sent for {t.name} (expiring in {days} days)")

        return alerts_sent

    @staticmethod
    async def check_churn_risks(db: AsyncSession):
        """
        Find clinics inactive for 30+ days and notify admins.
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        alerts_sent = 0

        # Get list of tenant IDs that have been active in the last 30 days
        stmt = (
            select(models.User.tenant_id)
            .join(models.UserSession, models.User.id == models.UserSession.user_id)
            .where(models.UserSession.last_active_at >= thirty_days_ago)
            .distinct()
        )
        active_tenant_ids_rows = (await db.execute(stmt)).all()
        active_ids = [r[0] for r in active_tenant_ids_rows if r[0] is not None]

        # Find active tenants that are NOT in the active sessions list
        stmt = select(models.Tenant).where(
            models.Tenant.is_active == True,  # noqa: E712
            ~models.Tenant.id.in_(active_ids)
        )
        inactive_tenants = (await db.execute(stmt)).scalars().all()

        for t in inactive_tenants:
            # Check last active date for the body message
            stmt = (
                select(func.max(models.UserSession.last_active_at))
                .join(models.User, models.User.id == models.UserSession.user_id)
                .where(models.User.tenant_id == t.id)
            )
            last_active = (await db.execute(stmt)).scalar()

            last_active_str = last_active.strftime('%Y-%m-%d') if last_active else "أبداً"

            title = f"تحذير Churn: عيادة {t.name}"
            body = f"عيادة {t.name} لم تقم بأي نشاط منذ أكثر من 30 يوماً (آخر نشاط: {last_active_str}). قد تكون العيادة بصدد التوقف عن استخدام النظام."
            await InternalNotificationService.notify_super_admins(db, title, body)
            alerts_sent += 1
            logger.info(f"Churn risk alert sent for {t.name} (inactive since {last_active_str})")

        return alerts_sent

    @staticmethod
    async def run_all_checks(db: AsyncSession):
        """
        Run all business health checks and return summary.
        """
        logger.info("Running daily business health checks...")
        try:
            expiring = await BusinessAlertsService.check_expiring_subscriptions(db)
            churn = await BusinessAlertsService.check_churn_risks(db)
            return {
                "status": "success",
                "expiring_alerts": expiring,
                "churn_alerts": churn,
                "timestamp": datetime.now(timezone.utc)
            }
        except Exception as e:
            logger.error(f"Error running business health checks: {e}")
            return {"status": "error", "message": str(e)}
