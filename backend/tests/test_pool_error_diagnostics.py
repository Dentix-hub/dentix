import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend import auth
from backend.database import (
    _POOL_CHECKOUT_STARTED_KEY,
    _POOL_TENANT_ID_KEY,
    _POOL_TRACE_ID_KEY,
    _record_pool_checkin,
    get_async_pool_status,
)
from backend.middleware.error_logging import ErrorLoggingMiddleware, _get_request_identity


def _request(*, token: str | None = None) -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request({"type": "http", "method": "GET", "path": "/test", "headers": headers})


def test_error_identity_prefers_verified_request_state():
    request = _request()
    request.state.current_user = SimpleNamespace(id=17, tenant_id=23)

    assert _get_request_identity(request) == (17, 23)


def test_error_identity_uses_verified_token_when_auth_query_fails():
    token = auth.create_access_token({"sub": "clinic-admin", "tenant_id": 41})

    assert _get_request_identity(_request(token=token)) == (None, 41)


def test_pool_status_is_safe_for_the_active_test_pool():
    status = get_async_pool_status()

    assert set(status) == {
        "pool_size",
        "max_overflow",
        "capacity",
        "checked_out",
        "checked_in",
        "overflow",
        "timeout_seconds",
    }


def test_long_checkout_emits_a_traceable_warning(monkeypatch):
    from backend import database

    record = SimpleNamespace(
        info={
            _POOL_CHECKOUT_STARTED_KEY: 10.0,
            _POOL_TRACE_ID_KEY: "trace-123",
            _POOL_TENANT_ID_KEY: 9,
        }
    )
    warning = MagicMock()
    monkeypatch.setattr(database.time, "monotonic", lambda: 20.0)
    monkeypatch.setattr(database, "_POOL_HOLD_WARN_SECONDS", 5.0)
    monkeypatch.setattr(database.logger, "warning", warning)

    _record_pool_checkin(None, record)

    warning.assert_called_once()
    assert warning.call_args.kwargs["extra"] == {"trace_id": "trace-123", "tenant_id": 9}
    assert record.info == {}


@pytest.mark.asyncio
async def test_error_logging_does_not_wait_for_an_exhausted_pool(monkeypatch):
    from backend.middleware import error_logging

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/patients",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 50000),
            "scheme": "http",
        }
    )

    async def fail_request(_request):
        raise RuntimeError("pool exhausted")

    async def blocked_persistence(**_kwargs):
        await asyncio.Event().wait()

    critical = MagicMock()
    monkeypatch.setattr(error_logging, "_persist_system_error", blocked_persistence)
    monkeypatch.setattr(error_logging, "ERROR_LOG_DB_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(error_logging.logger, "critical", critical)
    middleware = ErrorLoggingMiddleware(app=MagicMock(spec=BaseHTTPMiddleware))

    with pytest.raises(RuntimeError, match="pool exhausted"):
        await middleware.dispatch(request, fail_request)

    critical.assert_called_once()
    assert "Timed out" in critical.call_args.args[0]
