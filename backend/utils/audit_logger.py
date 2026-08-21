from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import json
from .. import models
from backend.core.logging import get_logger

logger = get_logger("smart_clinic")


def log_security_event(
    event_type: str,
    details: str,
    user_id: int = None,
    tenant_id: int = None,
    ip_address: str = None,
    user_agent: str = None,
    severity: str = "WARNING",
    db: Session | AsyncSession = None,
):
    """
    Log security-related events to system log and DB.
    Examples: Failed Login, Suspicious IP, Permission Denied.
    """
    msg = f"SECURITY_EVENT [{event_type}] User: {user_id}, IP: {ip_address} | {details}"

    if severity == "CRITICAL":
        logger.critical(msg)
    elif severity == "ERROR":
        logger.error(msg)
    else:
        logger.warning(msg)

    if db:
        try:
            event = models.SecurityEvent(
                event_type=event_type,
                description=details,
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=ip_address,
                user_agent=user_agent,
                severity=severity,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(event)
            # Commit depends on the caller or we can do it if it's a standalone log
        except Exception as e:
            logger.error(f"Failed to write security event to DB: {str(e)}")


def log_system_error(error_type: str, error: Exception, context: str = ""):
    """Log system exceptions with stack trace."""
    logger.error(
        f"SYSTEM_ERROR [{error_type}] {context} | Error: {str(error)}", exc_info=True
    )


def log_admin_action(
    db: Session | AsyncSession,
    admin_user: models.User,
    action: str,  # create, update, delete, archive, restore
    entity_type: str,  # tenant, user, plan, payment
    entity_id: int = None,
    details: str = None,
    old_value: dict = None,
    new_value: dict = None,
    target_user_id: int = None,
    tenant_id: int = None,
):
    """
    Create an audit log entry in the database AND log to system logs.
    """
    try:
        # 1. System Log
        logger.info(
            f"ADMIN_ACTION [{action}] Entity: {entity_type} ID: {entity_id} by {admin_user.username}"
        )

        # 2. Database Entry
        log_entry = models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            tenant_id=tenant_id or (admin_user.tenant_id if admin_user else None),
            performed_by_id=admin_user.id if admin_user else None,
            performed_by_username=admin_user.username if admin_user else "system",
            details=details,
            created_at=datetime.now(timezone.utc),
        )

        if old_value:
            log_entry.old_value = json.dumps(old_value, default=str, ensure_ascii=False)

        if new_value:
            log_entry.new_value = json.dumps(new_value, default=str, ensure_ascii=False)

        db.add(log_entry)
        # We don't commit here to allow the caller to group it with the main transaction

    except Exception as e:
        log_system_error(
            "AUDIT_LOG_FAILURE", e, f"Failed to log action {action} for {entity_type}"
        )
