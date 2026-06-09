"""
Structured Logging Configuration for Dentix.

Provides:
- JSON-formatted logs for production (machine-readable)
- Color-coded logs for development (human-readable)
- Automatic trace_id, tenant_id, user_id injection
- PHI scrubbing to prevent patient data in logs
"""

import json
import logging
import re
import sys
import os
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone


# === TRACE ID CONTEXT ===
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """Get the current request's trace_id."""
    return _trace_id_ctx.get()


def set_trace_id(trace_id: str = None) -> str:
    """Set trace_id for the current request. Auto-generates if not provided."""
    tid = trace_id or uuid.uuid4().hex[:12]
    _trace_id_ctx.set(tid)
    return tid


# === PHI SCRUBBER ===
# Patterns that might indicate PHI in log messages
_PHI_PATTERNS = [
    (re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'), '[SSN_REDACTED]'),  # SSN
    (re.compile(r'\b\d{14,16}\b'), '[CARD_REDACTED]'),  # Credit card
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),  # Email in messages
]


def _scrub_phi(message: str) -> str:
    """Remove potential PHI from log messages."""
    for pattern, replacement in _PHI_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


class StructuredFormatter(logging.Formatter):
    """JSON structured formatter for production logs.
    
    Output format per line:
    {"timestamp": "...", "level": "INFO", "logger": "...", "message": "...", ...}
    """

    def format(self, record):
        # Get tenant context
        tenant_id = None
        try:
            from backend.core.tenancy import get_current_tenant_id
            tenant_id = get_current_tenant_id()
        except Exception:
            pass

        log_data = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": _scrub_phi(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Inject context
        trace_id = get_trace_id()
        if trace_id:
            log_data["trace_id"] = trace_id
        if tenant_id:
            log_data["tenant_id"] = tenant_id

        # Add extra fields if present
        for field in ("tenant_id", "user_id", "request_id", "endpoint", "latency_ms", "status_code"):
            if hasattr(record, field) and getattr(record, field) is not None:
                log_data[field] = getattr(record, field)

        # Add exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable color-coded formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Context tags
        ctx_parts = []
        trace_id = get_trace_id()
        if trace_id:
            ctx_parts.append(f"R:{trace_id[:8]}")

        try:
            from backend.core.tenancy import get_current_tenant_id
            tid = get_current_tenant_id()
            if tid:
                ctx_parts.append(f"T:{tid}")
        except Exception:
            pass

        if hasattr(record, "tenant_id") and record.tenant_id:
            if f"T:{record.tenant_id}" not in ctx_parts:
                ctx_parts.append(f"T:{record.tenant_id}")

        ctx = f" [{' '.join(ctx_parts)}]" if ctx_parts else ""

        msg = _scrub_phi(record.getMessage())

        result = f"{color}[{timestamp}] {record.levelname:8}{self.RESET}{ctx} {record.name}: {msg}"

        if record.exc_info and record.exc_info[0] is not None:
            result += "\n" + self.formatException(record.exc_info)

        return result


def setup_logging():
    """
    Configure root logging for the entire application.
    Call once at application startup.
    """
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    log_level = logging.INFO if is_production else logging.DEBUG

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers
    root.handlers.clear()

    # Add stdout handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if is_production:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Ensure our app loggers are at the right level
    logging.getLogger("smart_clinic").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given module name.

    Usage:
        from backend.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Server started")
        logger.error("Failed", extra={"tenant_id": 1, "user_id": 5})
    """
    return logging.getLogger(name)


# Pre-configured loggers for common modules
app_logger = get_logger("smart_clinic")
admin_logger = get_logger("smart_clinic.admin")
billing_logger = get_logger("smart_clinic.billing")
auth_logger = get_logger("smart_clinic.auth")
security_logger = get_logger("smart_clinic.security")
