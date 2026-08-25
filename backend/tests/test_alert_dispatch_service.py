import hashlib
import hmac
import json

import httpx
import pytest

from backend.services.alert_dispatch_service import (
    AlertDispatchConfigurationError,
    dispatch_operational_alert,
)


@pytest.mark.asyncio
async def test_alert_dispatch_default_off_makes_no_request(monkeypatch):
    monkeypatch.delenv("ALERT_DISPATCH_ENABLED", raising=False)
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert not await dispatch_operational_alert(
            event="error", severity="error", trace_id="trace", client=client
        )
    assert calls == []


@pytest.mark.asyncio
async def test_alert_dispatch_is_metadata_only_and_hmac_signed(monkeypatch):
    secret = "s" * 32
    monkeypatch.setenv("ALERT_DISPATCH_ENABLED", "true")
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://alerts.example.test/dentix")
    monkeypatch.setenv("ALERT_WEBHOOK_SECRET", secret)
    captured = {}

    async def handler(request):
        captured["body"] = await request.aread()
        captured["signature"] = request.headers["x-dentix-signature"]
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await dispatch_operational_alert(
            event="unhandled_request_error",
            severity="error",
            trace_id="trace-1",
            client=client,
        )

    payload = json.loads(captured["body"])
    assert set(payload) == {"event", "severity", "status_code", "trace_id"}
    assert captured["signature"] == "sha256=" + hmac.new(
        secret.encode(), captured["body"], hashlib.sha256
    ).hexdigest()


@pytest.mark.asyncio
async def test_alert_dispatch_rejects_url_query_credentials(monkeypatch):
    monkeypatch.setenv("ALERT_DISPATCH_ENABLED", "true")
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://alerts.example.test/hook?token=secret")
    monkeypatch.setenv("ALERT_WEBHOOK_SECRET", "s" * 32)

    with pytest.raises(AlertDispatchConfigurationError):
        await dispatch_operational_alert(
            event="error", severity="error", trace_id="trace"
        )
