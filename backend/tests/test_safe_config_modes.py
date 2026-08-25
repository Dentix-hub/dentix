"""
Unit tests for backend/core/config.py safe configuration modes.
"""

import pytest
from backend.core.config import (
    get_subscription_enforcement_mode,
    is_subscription_worker_enabled,
    get_rate_limit_mode,
    get_metrics_exposure_mode,
    is_alert_dispatch_enabled,
    is_error_aggregation_enabled,
    is_backup_scheduler_enabled,
    get_external_ai_phi_mode,
    get_geoip_mode,
    get_rag_mode,
)


def test_default_config_modes(monkeypatch):
    # Clear env vars
    for var in [
        "SUBSCRIPTION_ENFORCEMENT_MODE",
        "SUBSCRIPTION_WORKER_ENABLED",
        "RATE_LIMIT_MODE",
        "METRICS_EXPOSURE_MODE",
        "ALERT_DISPATCH_ENABLED",
        "ERROR_AGGREGATION_ENABLED",
        "BACKUP_SCHEDULER_ENABLED",
        "EXTERNAL_AI_PHI_MODE",
        "GEOIP_MODE",
        "RAG_MODE",
    ]:
        monkeypatch.delenv(var, raising=False)

    assert get_subscription_enforcement_mode() == "off"
    assert is_subscription_worker_enabled() is False
    assert get_rate_limit_mode() == "off"
    assert get_metrics_exposure_mode() == "off"
    assert is_alert_dispatch_enabled() is False
    assert is_error_aggregation_enabled() is False
    assert is_backup_scheduler_enabled() is False
    assert get_external_ai_phi_mode() == "deny"
    assert get_geoip_mode() == "off"
    assert get_rag_mode() == "off"


def test_valid_custom_modes(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")
    monkeypatch.setenv("SUBSCRIPTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")

    assert get_subscription_enforcement_mode() == "enforce"
    assert is_subscription_worker_enabled() is True
    assert get_external_ai_phi_mode() == "deidentified"


def test_invalid_modes_raise_value_error(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "invalid_mode")
    with pytest.raises(ValueError, match="Invalid SUBSCRIPTION_ENFORCEMENT_MODE"):
        get_subscription_enforcement_mode()

    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "bypass_phi")
    with pytest.raises(ValueError, match="Invalid EXTERNAL_AI_PHI_MODE"):
        get_external_ai_phi_mode()
