"""
Tests for Phase P05: Client IP Resolution, Non-blocking GeoIP, and Rate Limiting.
"""

import pytest
import backend.core.limiter as limiter_module
from unittest.mock import MagicMock
from starlette.datastructures import Headers, Address
from backend.core.client_ip import get_real_client_ip, lookup_geoip_nonblocking
from backend.core.limiter import (
    clear_rate_limit_observations,
    limiter,
    record_rate_limit_observation,
)


def test_get_real_client_ip_fallbacks(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    # 1. CF-Connecting-IP
    req_cf = MagicMock()
    req_cf.headers = Headers({"CF-Connecting-IP": "203.0.113.195"})
    req_cf.client = Address("10.0.0.2", 443)
    assert get_real_client_ip(req_cf) == "203.0.113.195"

    # 2. X-Real-IP
    req_real = MagicMock()
    req_real.headers = Headers({"X-Real-IP": "198.51.100.22"})
    req_real.client = Address("10.0.0.2", 443)
    assert get_real_client_ip(req_real) == "198.51.100.22"

    # 3. Direct client host
    req_direct = MagicMock()
    req_direct.headers = Headers({})
    req_direct.client = Address("192.0.2.1", 12345)
    assert get_real_client_ip(req_direct) == "192.0.2.1"


def test_untrusted_peer_cannot_spoof_forwarded_headers(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    request = MagicMock()
    request.headers = Headers({"X-Forwarded-For": "8.8.8.8"})
    request.client = Address("192.0.2.44", 12345)

    assert get_real_client_ip(request) == "192.0.2.44"


@pytest.mark.asyncio
async def test_geoip_lookup_nonblocking_default_disabled(monkeypatch):
    monkeypatch.setenv("GEOIP_LOOKUP_ENABLED", "false")
    res = await lookup_geoip_nonblocking("8.8.8.8")
    assert res is None, "GeoIP lookup must return None immediately when disabled"


@pytest.mark.asyncio
async def test_geoip_lookup_internal_ip(monkeypatch):
    monkeypatch.setenv("GEOIP_LOOKUP_ENABLED", "true")
    res = await lookup_geoip_nonblocking("127.0.0.1")
    assert res is not None
    assert res["is_local"] is True


def test_limiter_key_func_integration(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    req = MagicMock()
    req.headers = Headers({"CF-Connecting-IP": "203.0.113.50"})
    req.client = Address("10.0.0.2", 443)
    key = limiter._key_func(req)
    assert key == "203.0.113.50"


def test_observe_mode_records_would_block_without_enforcement(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MODE", "observe")
    monkeypatch.setenv("RATE_LIMIT_OBSERVE_LIMIT", "2")
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    request = MagicMock()
    request.headers = Headers({})
    request.client = Address("192.0.2.50", 12345)
    clear_rate_limit_observations()

    assert record_rate_limit_observation(request, now=1.0) is False
    assert record_rate_limit_observation(request, now=2.0) is False
    assert record_rate_limit_observation(request, now=3.0) is True
    assert limiter.enabled is False


def test_observe_mode_window_expires(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MODE", "observe")
    monkeypatch.setenv("RATE_LIMIT_OBSERVE_LIMIT", "1")
    request = MagicMock()
    request.headers = Headers({})
    request.client = Address("192.0.2.51", 12345)
    clear_rate_limit_observations()

    assert record_rate_limit_observation(request, now=1.0) is False
    assert record_rate_limit_observation(request, now=62.0) is False


def test_observe_mode_evicts_stale_clients_at_capacity(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MODE", "observe")
    monkeypatch.setenv("RATE_LIMIT_OBSERVE_LIMIT", "10")
    monkeypatch.setattr(limiter_module, "_OBSERVE_MAX_KEYS", 2)
    clear_rate_limit_observations()

    def request_for(ip):
        request = MagicMock()
        request.headers = Headers({})
        request.client = Address(ip, 12345)
        return request

    assert record_rate_limit_observation(request_for("192.0.2.1"), now=1.0) is False
    assert record_rate_limit_observation(request_for("192.0.2.2"), now=1.0) is False
    # Both prior windows are expired, so a new client must be observed instead
    # of being permanently rejected after historical key churn.
    assert record_rate_limit_observation(request_for("192.0.2.3"), now=62.0) is False
