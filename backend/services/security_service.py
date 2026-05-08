from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from backend import models
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class SecurityService:
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    def __init__(self, db: Session = None):
        self.db = db

    @staticmethod
    def check_ip_blocked(db: Session, ip_address: str):
        """Check if IP is blocked. Returns blockage details or None."""
        blocked_entry = (
            db.query(models.BlockedIP)
            .filter(models.BlockedIP.ip_address == ip_address)
            .first()
        )
        if blocked_entry:
            # Check expiry
            expires_at = blocked_entry.expires_at
            now = datetime.now(timezone.utc)
            if expires_at:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now:
                    # Expired, unblock
                    db.delete(blocked_entry)
                    db.commit()
                    return None
            return blocked_entry
        return None

    @staticmethod
    def record_login_attempt(
        db: Session,
        ip_address: str,
        username: str,
        success: bool,
        user: models.User = None,
    ):
        """Log login attempt and manage failed count/locking."""

        # 1. Log History
        history = models.LoginHistory(
            user_id=user.id if user else None,
            ip_address=ip_address,
            status="success" if success else "failed",
            created_at=datetime.now(timezone.utc),
        )
        db.add(history)

        if not user:
            # Unknown user, just log and return
            db.commit()
            return

        if success:
            # Reset counters on success
            if user.failed_login_attempts > 0:
                user.failed_login_attempts = 0
                user.account_locked_until = None
            db.commit()
        else:
            # Handle Failure
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.now(timezone.utc)

            # Check for Lockout
            if user.failed_login_attempts >= SecurityService.MAX_FAILED_ATTEMPTS:
                user.account_locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=SecurityService.LOCKOUT_DURATION_MINUTES
                )
                # Optional: Log a separate "blocked" status or event

            db.commit()

    @staticmethod
    def is_account_locked(user: models.User) -> bool:
        if user.account_locked_until:
            lockout = user.account_locked_until
            if lockout.tzinfo is None:
                lockout = lockout.replace(tzinfo=timezone.utc)
            if lockout > datetime.now(timezone.utc):
                return True
        return False

    @staticmethod
    def block_ip(
        db: Session,
        ip_address: str,
        reason: str,
        admin_username: str,
        minutes: int = None,
    ):
        existing = (
            db.query(models.BlockedIP)
            .filter(models.BlockedIP.ip_address == ip_address)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="IP already blocked")

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes) if minutes else None

        new_block = models.BlockedIP(
            ip_address=ip_address,
            reason=reason,
            blocked_by=admin_username,
            expires_at=expires_at,
        )
        db.add(new_block)
        db.commit()
        return new_block

    @staticmethod
    def unblock_ip(db: Session, ip_address: str):
        entry = (
            db.query(models.BlockedIP)
            .filter(models.BlockedIP.ip_address == ip_address)
            .first()
        )
        if not entry:
            raise HTTPException(status_code=404, detail="IP not found in blocklist")

        db.delete(entry)
        db.commit()

    @staticmethod
    def get_security_stats(db: Session):
        """Get overview stats for dashboard."""
        logger.debug("Accessing Security Stats...")
        try:
            blocked_ips = db.query(models.BlockedIP).count()
            logger.debug("BlockedIP Count: %d", blocked_ips)

            recent_failures_rows = (
                db.query(models.LoginHistory)
                .filter(models.LoginHistory.status == "failed")
                .order_by(models.LoginHistory.created_at.desc())
                .limit(50)
                .all()
            )
            recent_failures = []
            from .geoip_service import GeoIPService

            for row in recent_failures_rows:
                location = GeoIPService.get_location(row.ip_address)
                recent_failures.append({
                    "id": row.id,
                    "user_id": row.user_id,
                    "ip_address": row.ip_address,
                    "location": location,
                    "user_agent": row.user_agent,
                    "status": row.status,
                    "created_at": row.created_at,
                })
            logger.debug("Recent Failures: %d", len(recent_failures))

            locked_user_rows = (
                db.query(models.User)
                .filter(models.User.account_locked_until > datetime.now(timezone.utc))
                .order_by(models.User.account_locked_until.desc())
                .all()
            )
            locked_users = [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "failed_login_attempts": user.failed_login_attempts,
                    "account_locked_until": user.account_locked_until,
                }
                for user in locked_user_rows
            ]
            logger.debug("Locked Users: %d", len(locked_users))

            return {
                "blocked_ips_count": blocked_ips,
                "recent_failures": recent_failures,
                "locked_users": locked_users,
            }
        except Exception as e:
            logger.exception("CRITICAL ERROR in get_security_stats", exc_info=True)
            raise e

    @staticmethod
    def get_login_attempts_chart(db: Session, days: int = 7):
        """Get login attempts aggregated by day for charting."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Query for counts per day
        stats = (
            db.query(
                func.date(models.LoginHistory.created_at).label("date"),
                func.count(models.LoginHistory.id).label("total"),
                func.sum(case((models.LoginHistory.status == "success", 1), else_=0)).label("success"),
                func.sum(case((models.LoginHistory.status == "failed", 1), else_=0)).label("failed"),
            )
            .filter(models.LoginHistory.created_at >= start_date)
            .group_by(func.date(models.LoginHistory.created_at))
            .order_by("date")
            .all()
        )

        return [
            {
                "date": str(s.date),
                "total": s.total,
                "success": int(s.success or 0),
                "failed": int(s.failed or 0),
            }
            for s in stats
        ]

    @staticmethod
    def get_audit_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: dict = None
    ):
        """Get filtered audit logs."""
        query = db.query(models.AuditLog)

        if filters:
            if filters.get("tenant_id"):
                query = query.filter(models.AuditLog.tenant_id == filters["tenant_id"])
            if filters.get("user_id"):
                query = query.filter(models.AuditLog.performed_by_id == filters["user_id"])
            if filters.get("action"):
                # Sanitize input to prevent SQL injection via wildcard characters
                safe_action = filters['action'].replace('%', '\\%').replace('_', '\\_')
                query = query.filter(models.AuditLog.action.ilike(f"%{safe_action}%", escape='\\'))
            if filters.get("entity_type"):
                query = query.filter(models.AuditLog.entity_type == filters["entity_type"])
            if filters.get("start_date"):
                query = query.filter(models.AuditLog.created_at >= filters["start_date"])
            if filters.get("end_date"):
                query = query.filter(models.AuditLog.created_at <= filters["end_date"])

        total = query.count()
        audit_logs = query.order_by(models.AuditLog.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "logs": [
                {
                    "id": log.id,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "target_user_id": log.target_user_id,
                    "target_username": log.target_username,
                    "performed_by_id": log.performed_by_id,
                    "performed_by_username": log.performed_by_username,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "details": log.details,
                    "tenant_id": log.tenant_id,
                    "created_at": log.created_at,
                }
                for log in audit_logs
            ],
            "pages": (total + limit - 1) // limit if limit > 0 else 1,
            "current_page": (skip // limit) + 1 if limit > 0 else 1
        }

    def get_active_sessions(self, limit: int = 50):
        """Get list of active sessions for super admin review."""
        sessions = (
            self.db.query(models.UserSession)
            .filter(models.UserSession.is_active == True)
            .filter(models.UserSession.expires_at > datetime.now(timezone.utc))
            .order_by(models.UserSession.last_active_at.desc())
            .limit(limit)
            .all()
        )

        result = []
        from .geoip_service import GeoIPService
        for s in sessions:
            location = GeoIPService.get_location(s.ip_address)
            result.append({
                "id": s.id,
                "user_id": s.user_id,
                "username": s.user.username if s.user else "Unknown",
                "tenant": s.user.tenant.name if s.user and s.user.tenant else "System",
                "ip_address": s.ip_address,
                "location": location,
                "user_agent": s.user_agent,
                "last_active": s.last_active_at,
                "created_at": s.created_at
            })
        return result

    def terminate_session(self, session_id: int):
        """Terminate a specific session."""
        session = self.db.query(models.UserSession).filter(models.UserSession.id == session_id).first()
        if session:
            session.is_active = False
            # If this was the active session, clear it from user record to trigger kickout
            if session.user and session.device_info == getattr(session.user, "active_session_id", None):
                session.user.active_session_id = "revoked_by_admin_" + str(session.id)
            self.db.commit()
            return True
        return False
