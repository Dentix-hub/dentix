"""
Unit tests for Item 7: Error Logging Quality.
Ensures:
1. Every HTTP 400/401/404 warning includes a short reason or error code in the message.
2. Sensitive data (passwords, tokens, credentials) is never leaked in the reason.
3. The stack trace column is always populated for every ERROR row (never empty).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request

from backend.middleware.error_logging import (
    _extract_short_reason,
    persist_handled_response_error,
    _persist_system_error,
)
from backend.models.system import ErrorLevel


def _make_request(
    path: str = "/api/v1/patients",
    method: str = "POST",
    error_detail=None,
    error_code=None,
    stack_trace=None,
    user_id: int = 1,
    tenant_id: int = 1,
) -> Request:
    req = Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 50000),
            "scheme": "http",
        }
    )
    req.state.error_log_identity = (user_id, tenant_id)
    if error_detail is not None:
        req.state.error_detail = error_detail
    if error_code is not None:
        req.state.error_code = error_code
    if stack_trace is not None:
        req.state.stack_trace = stack_trace
    return req


def test_extract_short_reason_from_detail_string():
    req = _make_request(error_detail="Patient not found")
    assert _extract_short_reason(req, 404) == "Patient not found"


def test_extract_short_reason_from_error_code():
    req = _make_request(error_code="CLINICAL_LINK_CODE_MISMATCH")
    assert _extract_short_reason(req, 422) == "CLINICAL_LINK_CODE_MISMATCH"


def test_extract_short_reason_from_dict_detail():
    req = _make_request(error_detail={"code": "INVALID_STATE", "message": "Cannot perform transition"})
    assert _extract_short_reason(req, 400) == "INVALID_STATE"


def test_extract_short_reason_scrubs_passwords_and_tokens():
    req = _make_request(error_detail="Invalid password=SuperSecret123 with token eyJhbGciOi...")
    reason = _extract_short_reason(req, 401)
    assert "SuperSecret123" not in reason
    assert "[REDACTED]" in reason or "[REDACTED_JWT]" in reason


def test_extract_short_reason_fallback():
    req = _make_request()
    assert _extract_short_reason(req, 400) == "bad_request"
    assert _extract_short_reason(req, 401) == "unauthorized"
    assert _extract_short_reason(req, 404) == "not_found"


@pytest.mark.asyncio
async def test_persist_handled_response_warning_includes_short_reason(monkeypatch):
    persisted_kwargs = {}

    async def fake_persist(**kwargs):
        persisted_kwargs.update(kwargs)

    monkeypatch.setattr("backend.middleware.error_logging._persist_system_error", fake_persist)

    req = _make_request(error_detail="Patient not found")
    await persist_handled_response_error(req, 404)

    assert persisted_kwargs["level"] == ErrorLevel.WARNING
    assert "HTTP 404 (Patient not found) response" in persisted_kwargs["error_msg"]


@pytest.mark.asyncio
async def test_persist_handled_response_error_populates_stack_trace_on_500(monkeypatch):
    persisted_kwargs = {}

    async def fake_persist(**kwargs):
        persisted_kwargs.update(kwargs)

    monkeypatch.setattr("backend.middleware.error_logging._persist_system_error", fake_persist)

    # 500 with stack_trace on request.state
    req = _make_request(
        error_detail="Division by zero",
        stack_trace="Traceback (most recent call last):\n  File 'app.py', line 10\nZeroDivisionError: division by zero",
    )
    await persist_handled_response_error(req, 500)

    assert persisted_kwargs["level"] == ErrorLevel.ERROR
    assert "HTTP 500" in persisted_kwargs["error_msg"]
    assert persisted_kwargs["stack_trace"] != ""
    assert "ZeroDivisionError" in persisted_kwargs["stack_trace"]


@pytest.mark.asyncio
async def test_persist_system_error_guarantees_nonempty_stack_trace_for_error_level(monkeypatch):
    """When stack_trace is empty for level ERROR and no exception is active, store 'no traceback available'."""
    added_errors = []

    class FakeSessionScope:
        async def __aenter__(self):
            sess = MagicMock()
            sess.add = lambda item: added_errors.append(item)
            sess.commit = AsyncMock()
            return sess
        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr("backend.middleware.error_logging.system_session_scope", lambda: FakeSessionScope())

    req = _make_request()
    await _persist_system_error(
        request=req,
        error_msg="Database timeout",
        stack_trace="",  # intentionally empty
        user_id=1,
        tenant_id=1,
        level=ErrorLevel.ERROR,
    )

    assert len(added_errors) == 1
    error_row = added_errors[0]
    assert error_row.level == ErrorLevel.ERROR
    assert error_row.stack_trace == "no traceback available"


@pytest.mark.asyncio
async def test_persist_handled_response_error_no_traceback_fallback(monkeypatch):
    """When a 500 response has no traceback on state or in sys.exc_info, record 'no traceback available'."""
    persisted_kwargs = {}

    async def fake_persist(**kwargs):
        persisted_kwargs.update(kwargs)

    monkeypatch.setattr("backend.middleware.error_logging._persist_system_error", fake_persist)

    # 500 with NO stack trace on state and no active exception
    req = _make_request()
    await persist_handled_response_error(req, 500)

    assert persisted_kwargs["level"] == ErrorLevel.ERROR
    assert persisted_kwargs["stack_trace"] == "no traceback available"
