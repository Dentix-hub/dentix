"""Performance Diagnostics & Server-Timing Instrumentation (PR4).

Behind env flag PERF_DIAGNOSTICS=1 (default OFF).
Measures:
1. DB statements count and total DB time per request via SQLAlchemy cursor events.
2. Pool checkout wait time via pool.connect timing.
3. Server-Timing header (db;dur=..., dbq;desc="n queries", pool;dur=..., total;dur=...).
4. Logs requests over 1s with diagnostics. No query text or parameters in logs (PHI protection).
5. Logs effective pool settings once at startup.
"""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Any, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("smart_clinic.perf")


def is_perf_enabled() -> bool:
    """Check if performance diagnostics are active. Defaults to False."""
    return os.getenv("PERF_DIAGNOSTICS", "0").lower() in ("1", "true", "yes")


# Per-request performance context
_perf_context: ContextVar[dict[str, Any] | None] = ContextVar("perf_context", default=None)


def log_effective_pool_settings() -> None:
    """Log effective pool settings once at startup without sensitive secrets."""
    try:
        from backend.database import (
            SQLALCHEMY_DATABASE_URL,
            is_supabase_pooler,
            sync_pool_args,
        )

        is_sqlite = "sqlite" in SQLALCHEMY_DATABASE_URL.lower()
        pool_size = sync_pool_args.get("pool_size", "N/A (sqlite)" if is_sqlite else "N/A")
        max_overflow = sync_pool_args.get("max_overflow", "N/A (sqlite)" if is_sqlite else "N/A")
        pool_timeout = sync_pool_args.get("pool_timeout", "N/A (sqlite)" if is_sqlite else "N/A")

        logger.info(
            "[DB_POOL_CONFIG] Effective pool settings: pool_size=%s max_overflow=%s pool_timeout=%s supabase_pooler_active=%s (sqlite=%s)",
            pool_size,
            max_overflow,
            pool_timeout,
            is_supabase_pooler,
            is_sqlite,
        )
    except Exception as exc:
        logger.warning("[DB_POOL_CONFIG] Could not log effective pool settings: %s", exc)


def setup_sqlalchemy_perf_events(*engines: Any) -> None:
    """Attach SQLAlchemy event listeners to measure query durations and pool checkout."""
    if not is_perf_enabled():
        return

    from sqlalchemy import event

    for async_engine in engines:
        if async_engine is None:
            continue
        sync_engine = getattr(async_engine, "sync_engine", async_engine)
        pool = getattr(sync_engine, "pool", None)

        # 1. Query Execution Timing
        @event.listens_for(sync_engine, "before_cursor_execute")
        def _before_cursor(conn, cursor, statement, parameters, context, executemany):
            if not is_perf_enabled():
                return
            ctx = _perf_context.get()
            if ctx is not None:
                context._perf_query_start_ns = time.perf_counter_ns()

        @event.listens_for(sync_engine, "after_cursor_execute")
        def _after_cursor(conn, cursor, statement, parameters, context, executemany):
            if not is_perf_enabled():
                return
            ctx = _perf_context.get()
            if ctx is not None:
                start_ns = getattr(context, "_perf_query_start_ns", None)
                if start_ns is not None:
                    ctx["db_time_ns"] += (time.perf_counter_ns() - start_ns)
                ctx["db_count"] += 1

        # 2. Pool Checkout Wait Timing
        if pool and not getattr(pool, "_perf_wrapped", False):
            orig_connect = pool.connect

            def make_timed_connect(orig_fn: Callable) -> Callable:
                def timed_connect(*args: Any, **kwargs: Any) -> Any:
                    t0 = time.perf_counter_ns()
                    conn = orig_fn(*args, **kwargs)
                    wait_ns = time.perf_counter_ns() - t0
                    ctx = _perf_context.get()
                    if ctx is not None:
                        ctx["pool_wait_ns"] += wait_ns
                    return conn
                return timed_connect

            pool.connect = make_timed_connect(orig_connect)
            pool._perf_wrapped = True

    logger.info("[PERF_DIAGNOSTICS] SQLAlchemy cursor events and pool instrumentation attached.")


class PerfDiagnosticsMiddleware(BaseHTTPMiddleware):
    """Measures DB statement counts, DB time, pool wait, and sets Server-Timing header."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if not is_perf_enabled():
            return await call_next(request)

        ctx = {
            "db_count": 0,
            "db_time_ns": 0,
            "pool_wait_ns": 0,
        }
        token = _perf_context.set(ctx)
        start_ns = time.perf_counter_ns()

        try:
            response = await call_next(request)
        finally:
            total_duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            _perf_context.reset(token)

        db_duration_ms = ctx["db_time_ns"] / 1_000_000.0
        pool_wait_ms = ctx["pool_wait_ns"] / 1_000_000.0
        db_count = ctx["db_count"]

        # Server-Timing: db;dur=..., dbq;desc="n queries", pool;dur=..., total;dur=...
        timing_value = (
            f'db;dur={db_duration_ms:.2f}, '
            f'dbq;desc="{db_count} queries", '
            f'pool;dur={pool_wait_ms:.2f}, '
            f'total;dur={total_duration_ms:.2f}'
        )

        # Existing Server-Timing header preservation
        existing_timing = response.headers.get("Server-Timing")
        if existing_timing:
            response.headers["Server-Timing"] = f"{existing_timing}, {timing_value}"
        else:
            response.headers["Server-Timing"] = timing_value

        # Log requests over 1s (No query text or parameters logged - PHI safe)
        if total_duration_ms > 1000.0:
            logger.warning(
                "[PERF_DIAGNOSTICS] Slow request (>1s): method=%s path=%s total=%.2fms db=%.2fms (%d queries) pool=%.2fms",
                request.method,
                request.url.path,
                total_duration_ms,
                db_duration_ms,
                db_count,
                pool_wait_ms,
            )

        return response
