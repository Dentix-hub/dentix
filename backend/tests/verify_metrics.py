"""Assertion-full tests for the /metrics exposure policy."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_metrics_default_off_returns_not_found(monkeypatch):
    monkeypatch.delenv("METRICS_EXPOSURE_MODE", raising=False)
    monkeypatch.delenv("METRICS_SCRAPER_TOKEN", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_protected_metrics_require_exact_bearer_token(monkeypatch):
    monkeypatch.setenv("METRICS_EXPOSURE_MODE", "protected")
    monkeypatch.setenv("METRICS_SCRAPER_TOKEN", "metrics-test-token")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/metrics")).status_code == 403
        assert (
            (
                await client.get(
                "/metrics",
                headers={"Authorization": "Bearer wrong-token"},
                )
            ).status_code
            == 403
        )
        response = await client.get(
            "/metrics",
            headers={"Authorization": "Bearer metrics-test-token"},
        )
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests" in response.text or "python_info" in response.text


@pytest.mark.asyncio
async def test_protected_metrics_fail_closed_without_server_token(monkeypatch):
    monkeypatch.setenv("METRICS_EXPOSURE_MODE", "protected")
    monkeypatch.delenv("METRICS_SCRAPER_TOKEN", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 503
