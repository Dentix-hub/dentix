import os
from typing import Literal

API_V1_STR = "/api/v1"
APP_VERSION = "2026.8.0"


def get_cors_origins():
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",")]

    return [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]


def get_allow_origin_regex():
    if os.getenv("ENVIRONMENT") != "production":
        return r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+"
    return None


def get_subscription_enforcement_mode() -> Literal["off", "observe", "enforce"]:
    """
    Control subscription enforcement.
    Modes:
      - 'off': Default. No entitlement calculation changes access.
      - 'observe': Log metrics/counters on would-be blocks, but do not block.
      - 'enforce': Block new billable writes when subscription is expired.
    """
    mode = os.getenv("SUBSCRIPTION_ENFORCEMENT_MODE", "off").lower().strip()
    if mode not in {"off", "observe", "enforce"}:
        raise ValueError(
            f"Invalid SUBSCRIPTION_ENFORCEMENT_MODE='{mode}'. Allowed: off, observe, enforce."
        )
    return mode  # type: ignore


def is_subscription_worker_enabled() -> bool:
    """
    Control whether background subscription expiry checks run.
    Defaults to False.
    """
    val = os.getenv("SUBSCRIPTION_WORKER_ENABLED", "false").lower().strip()
    return val in {"true", "1", "yes"}


def get_rate_limit_mode() -> Literal["off", "observe", "enforce"]:
    """Control rate limiting mode: off, observe, enforce. Default off."""
    mode = os.getenv("RATE_LIMIT_MODE", "off").lower().strip()
    if mode not in {"off", "observe", "enforce"}:
        raise ValueError(f"Invalid RATE_LIMIT_MODE='{mode}'. Allowed: off, observe, enforce.")
    return mode  # type: ignore


def get_metrics_exposure_mode() -> Literal["off", "protected"]:
    """Control /metrics exposure mode: off, protected. Default off."""
    mode = os.getenv("METRICS_EXPOSURE_MODE", "off").lower().strip()
    if mode not in {"off", "protected"}:
        raise ValueError(f"Invalid METRICS_EXPOSURE_MODE='{mode}'. Allowed: off, protected.")
    return mode  # type: ignore


def is_alert_dispatch_enabled() -> bool:
    """Control alert dispatch webhook triggers. Default False."""
    val = os.getenv("ALERT_DISPATCH_ENABLED", "false").lower().strip()
    return val in {"true", "1", "yes"}


def is_error_aggregation_enabled() -> bool:
    """Control external error reporting/aggregation. Default False."""
    val = os.getenv("ERROR_AGGREGATION_ENABLED", "false").lower().strip()
    return val in {"true", "1", "yes"}


def is_backup_scheduler_enabled() -> bool:
    """Control automated backup scheduling. Default False."""
    val = os.getenv("BACKUP_SCHEDULER_ENABLED", "false").lower().strip()
    return val in {"true", "1", "yes"}


def _bounded_int_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"Invalid {name}; expected an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def get_backup_schedule_interval_seconds() -> int:
    """Interval for the disabled-by-default durable backup scheduler."""
    return _bounded_int_setting(
        "BACKUP_SCHEDULER_INTERVAL_SECONDS", 86_400, 60, 2_592_000
    )


def get_backup_missed_run_grace_seconds() -> int:
    """Delay beyond the normal interval that marks a run as missed."""
    return _bounded_int_setting(
        "BACKUP_MISSED_RUN_GRACE_SECONDS", 3_600, 0, 604_800
    )


def get_external_ai_phi_mode() -> Literal["deny", "deidentified", "contracted"]:
    """Control external AI transmission policy: deny, deidentified, contracted. Default deny."""
    mode = os.getenv("EXTERNAL_AI_PHI_MODE", "deny").lower().strip()
    if mode not in {"deny", "deidentified", "contracted"}:
        raise ValueError(
            f"Invalid EXTERNAL_AI_PHI_MODE='{mode}'. Allowed: deny, deidentified, contracted."
        )
    return mode  # type: ignore


def get_geoip_mode() -> Literal["off", "coarse", "full"]:
    """Control GeoIP lookup precision: off, coarse, full. Default off."""
    mode = os.getenv("GEOIP_MODE", "off").lower().strip()
    if mode not in {"off", "coarse", "full"}:
        raise ValueError(f"Invalid GEOIP_MODE='{mode}'. Allowed: off, coarse, full.")
    return mode  # type: ignore


def get_rag_mode() -> Literal["off", "isolated"]:
    """Control RAG index activation: off, isolated. Default off."""
    mode = os.getenv("RAG_MODE", "off").lower().strip()
    if mode not in {"off", "isolated"}:
        raise ValueError(f"Invalid RAG_MODE='{mode}'. Allowed: off, isolated.")
    return mode  # type: ignore


def is_ai_read_only() -> bool:
    """Check if AI is in Read-Only mode. Defaults to False."""
    return os.getenv("AI_READ_ONLY", "false").lower() == "true"


def is_ai_disabled() -> bool:
    """Kill Switch: Globally disable AI features."""
    return os.getenv("AI_GLOBAL_DISABLE", "false").lower() == "true"
