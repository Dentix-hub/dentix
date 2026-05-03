"""
Structured Logging Configuration for Smart Clinic.

Provides consistent, JSON-formatted logs for production and human-readable
logs for development.
"""

import logging
import sys
import os
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """JSON-style structured formatter for production logs."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "tenant_id"):
            log_data["tenant_id"] = record.tenant_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        return str(log_data)


class DevFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Add tenant context if available
        tenant_ctx = ""
        if hasattr(record, "tenant_id"):
            tenant_ctx = f" [T:{record.tenant_id}]"

        return f"{color}[{timestamp}] {record.levelname:8}{self.RESET}{tenant_ctx} {record.name}: {record.getMessage()}"


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the given module name.

    Usage:
        from backend.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Server started")
        logger.error("Failed to connect", extra={"tenant_id": 1})
    """
    logger = logging.getLogger(name)

    # Only configure if not already done
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if os.getenv("DEBUG") else logging.INFO)

        handler = logging.StreamHandler(sys.stdout)

        # Use structured formatting in production
        if os.getenv("ENVIRONMENT") == "production":
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(DevFormatter())

        logger.addHandler(handler)
        logger.propagate = False  # Prevent duplicate logs

    return logger


# Pre-configured loggers for common modules
app_logger = get_logger("smart_clinic")
admin_logger = get_logger("smart_clinic.admin")
billing_logger = get_logger("smart_clinic.billing")
auth_logger = get_logger("smart_clinic.auth")
