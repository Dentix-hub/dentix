"""Tests for PR4 Performance Diagnostics & Server-Timing Instrumentation."""

import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from backend.core.perf_diagnostics import (
    is_perf_enabled,
    log_effective_pool_settings,
    setup_sqlalchemy_perf_events,
    PerfDiagnosticsMiddleware,
    _perf_context,
)


def test_perf_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("PERF_DIAGNOSTICS", raising=False)
    assert not is_perf_enabled()
    monkeypatch.setenv("PERF_DIAGNOSTICS", "0")
    assert not is_perf_enabled()
    monkeypatch.setenv("PERF_DIAGNOSTICS", "false")
    assert not is_perf_enabled()


def test_perf_flag_enabled(monkeypatch):
    monkeypatch.setenv("PERF_DIAGNOSTICS", "1")
    assert is_perf_enabled()
    monkeypatch.setenv("PERF_DIAGNOSTICS", "true")
    assert is_perf_enabled()


def test_server_timing_header_absent_when_disabled(monkeypatch):
    monkeypatch.setenv("PERF_DIAGNOSTICS", "0")

    app = FastAPI()
    app.add_middleware(PerfDiagnosticsMiddleware)

    @app.get("/test")
    def get_test():
        return {"ok": True}

    client = TestClient(app)
    res = client.get("/test")
    assert res.status_code == 200
    assert "Server-Timing" not in res.headers


def test_server_timing_header_present_when_enabled(monkeypatch):
    monkeypatch.setenv("PERF_DIAGNOSTICS", "1")

    app = FastAPI()
    app.add_middleware(PerfDiagnosticsMiddleware)

    @app.get("/test")
    def get_test():
        ctx = _perf_context.get()
        if ctx is not None:
            ctx["db_count"] += 3
            ctx["db_time_ns"] += 12_500_000  # 12.5 ms
            ctx["pool_wait_ns"] += 1_200_000  # 1.2 ms
        return {"ok": True}

    client = TestClient(app)
    res = client.get("/test")
    assert res.status_code == 200
    assert "Server-Timing" in res.headers
    timing = res.headers["Server-Timing"]
    assert 'db;dur=12.50' in timing
    assert 'dbq;desc="3 queries"' in timing
    assert 'pool;dur=1.20' in timing
    assert 'total;dur=' in timing


def test_log_effective_pool_settings_does_not_crash():
    # Should safely log without throwing
    log_effective_pool_settings()


def test_slow_request_logger_triggers_without_phi(monkeypatch):
    monkeypatch.setenv("PERF_DIAGNOSTICS", "1")

    app = FastAPI()
    app.add_middleware(PerfDiagnosticsMiddleware)

    @app.get("/slow")
    def get_slow():
        return {"ok": True}

    with patch("backend.core.perf_diagnostics.time.perf_counter_ns") as mock_time, \
         patch("backend.core.perf_diagnostics.logger.warning") as mock_warn:
        # Start at 0, finish at 1.5s (1_500_000_000 ns)
        mock_time.side_effect = [0, 1_500_000_000]
        client = TestClient(app)
        res = client.get("/slow")
        assert res.status_code == 200
        assert mock_warn.called
        log_msg = mock_warn.call_args[0][0]
        # Ensure log format string only contains timing and count metadata, no queries
        assert "Slow request (>1s)" in log_msg
        assert "method=%s path=%s total=%.2fms db=%.2fms (%d queries) pool=%.2fms" in log_msg
