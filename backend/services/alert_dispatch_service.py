"""Privacy-safe, signed, bounded outbound operational alert dispatcher."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from urllib.parse import urlparse

import httpx

from backend.core.config import is_alert_dispatch_enabled


class AlertDispatchConfigurationError(RuntimeError):
    pass


async def dispatch_operational_alert(
    *,
    event: str,
    severity: str,
    trace_id: str | None,
    status_code: int = 500,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Send metadata only; exception/request content is intentionally excluded."""
    if not is_alert_dispatch_enabled():
        return False
    endpoint = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    secret = os.getenv("ALERT_WEBHOOK_SECRET", "").encode()
    parsed = urlparse(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise AlertDispatchConfigurationError("Alert webhook must be credential-free HTTPS")
    if len(secret) < 32:
        raise AlertDispatchConfigurationError("Alert webhook secret must be at least 32 bytes")

    payload = {
        "event": event[:80],
        "severity": severity,
        "status_code": int(status_code),
        "trace_id": (trace_id or "")[:64],
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.0))
    try:
        response = await http_client.post(
            endpoint,
            content=body,
            headers={
                "content-type": "application/json",
                "x-dentix-signature": f"sha256={signature}",
            },
        )
        response.raise_for_status()
        return True
    finally:
        if owns_client:
            await http_client.aclose()
