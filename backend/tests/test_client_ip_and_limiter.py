"""
Tests for Phase P05: Client IP Resolution, Non-blocking GeoIP, and Rate Limiting.
"""

import pytest
from unittest.mock import MagicMock
from starlette.datastructures import Headers, Address
from backend.core.client_ip import get_real_client_ip, lookup_geoip_nonblocking
from backend.core.limiter import limiter, RATE_LIMITING_ENABLED


def test_get_real_client_ip_fallbacks():
    # 1. CF-Connecting-IP
    req_cf = MagicMock()
    req_cf.headers = Headers({"CF-Connecting-IP": "203.0.113.195"})
    assert get_real_client_ip(req_cf) == "203.0.113.195"

    # 2. X-Real-IP
    req_real = MagicMock()
    req_real.headers = Headers({"X-Real-IP": "198.51.100.22"})
    assert get_real_client_ip(req_real) == "198.51.100.22"

    # 3. Direct client host
    req_direct = MagicMock()
    req_direct.headers = Headers({})
    req_direct.client = Address("192.0.2.1", 12345)
    assert get_real_client_ip(req_direct) == "192.0.2.1"


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


def test_limiter_key_func_integration():
    req = MagicMock()
    req.headers = Headers({"CF-Connecting-IP": "203.0.113.50"})
    key = limiter._key_func(req)
    assert key == "203.0.113.50"
