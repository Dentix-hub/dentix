
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging
import sys
import os
from .. import models

# --- Configure System Logger ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output to console (for Docker/HF logs)
        logging.FileHandler("app.log", encoding='utf-8')  # Output to file
    ]
)
logger = logging.getLogger("smart_clinic")

def log_security_event(event_type: str, details: str, user_id: int = None, ip_address: str = None, severity: str = "WARNING"):
    """
    Log security-related events to system log and potentially DB or external tool.
    Examples: Failed Login, Suspicious IP, Permission Denied.
    """
    msg = f"SECURITY_EVENT [{event_type}] User: {user_id}, IP: {ip_address} | {details}"
    
    if severity == "CRITICAL":
        logger.critical(msg)
    elif severity == "ERROR":
        logger.error(msg)
    else:
        logger.warning(msg)

def log_system_error(error_type: str, error: Exception, context: str = ""):
    """Log system exceptions with stack trace."""
    logger.error(f"SYSTEM_ERROR [{error_type}] {context} | Error: {str(error)}", exc_info=True)

def log_admin_action(
    db: Session,
    admin_user: models.User,
    action: str,  # create, update, delete, archive, restore
    entity_type: str, # tenant, user, plan, payment
    entity_id: int = None,
    details: str = None,
    old_value: dict = None,
    new_value: dict = None,
    target_user_id: int = None
):
    """
    Create an audit log entry in the database AND log to system logs.
    """
    try:
        # 1. System Log
        logger.info(f"ADMIN_ACTION [{action}] Entity: {entity_type} ID: {entity_id} by {admin_user.username}")

        # 2. Database Entry
        log_entry = models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            performed_by_id=admin_user.id,
            performed_by_username=admin_user.username,
            details=details,
            created_at=datetime.utcnow()
        )

        if old_value:
            log_entry.old_value = json.dumps(old_value, default=str, ensure_ascii=False)
        
        if new_value:
            log_entry.new_value = json.dumps(new_value, default=str, ensure_ascii=False)

        db.add(log_entry)
        # We don't commit here to allow the caller to group it with the main transaction
        
    except Exception as e:
        log_system_error("AUDIT_LOG_FAILURE", e, f"Failed to log action {action} for {entity_type}")
