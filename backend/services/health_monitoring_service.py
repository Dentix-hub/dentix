import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from .security_service import SecurityService
from .internal_notification_service import InternalNotificationService

logger = logging.getLogger("smart_clinic")

class HealthMonitoringService:
    @staticmethod
    def calculate_health_score(db: Session):
        """
        Calculates the system health score (0-100).
        """
        score = 100
        alerts = []

        # 1. Critical Errors (Last 24h)
        yesterday = datetime.now() - timedelta(days=1)
        critical_errors = db.query(models.SystemError).filter(
            models.SystemError.created_at >= yesterday,
            models.SystemError.level == models.ErrorLevel.CRITICAL.value
        ).count()

        if critical_errors > 0:
            deduction = min(critical_errors * 10, 40)
            score -= deduction
            alerts.append({
                "severity": "high",
                "message": f"تم رصد {critical_errors} أخطاء برمجية حرجة خلال الـ 24 ساعة الماضية",
                "type": "error"
            })

        # 2. Security Failures (High volume of failures)
        security_stats = SecurityService.get_security_stats(db)
        recent_failures_count = len(security_stats.get("recent_failures", []))
        if recent_failures_count > 20:
            score -= 15
            alerts.append({
                "severity": "medium",
                "message": "نشاط دخول مشبوه: عدد محاولات الدخول الفاشلة مرتفع",
                "type": "security"
            })

        # 3. Backup Status
        # Assuming we check for the latest successful backup
        latest_backup = db.query(models.BackgroundJob).filter(
            models.BackgroundJob.job_name == "system_backup",
            models.BackgroundJob.status == "success"
        ).order_by(models.BackgroundJob.completed_at.desc()).first()

        if not latest_backup or (datetime.now(datetime.UTC) - latest_backup.completed_at).days > 1:
            score -= 20
            alerts.append({
                "severity": "critical",
                "message": "لم يتم إجراء نسخة احتياطية بنجاح خلال الـ 24 ساعة الماضية",
                "type": "backup"
            })

        return {
            "score": max(score, 0),
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def check_and_notify(db: Session):
        """
        Check health and notify admins if score is low.
        """
        health = HealthMonitoringService.calculate_health_score(db)
        if health["score"] < 70:
            title = f"تنبيه: تدهور حالة النظام ({health['score']}%)"
            body = "لقد انخفض مؤشر صحة النظام عن الحد المسموح. يرجى مراجعة لوحة تحكم الإدارة فوراً.\n\n"
            for alert in health["alerts"]:
                body += f"- {alert['message']}\n"

            InternalNotificationService.notify_super_admins(db, title, body)
            return True
        return False
