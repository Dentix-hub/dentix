from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session
from backend import models
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class SecurityService:
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

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
            if (
                blocked_entry.expires_at
                and blocked_entry.expires_at < datetime.now(timezone.utc)
            ):
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
        if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
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
            recent_failures = [
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "ip_address": row.ip_address,
                    "user_agent": row.user_agent,
                    "status": row.status,
                    "created_at": row.created_at,
                }
                for row in recent_failures_rows
            ]
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
