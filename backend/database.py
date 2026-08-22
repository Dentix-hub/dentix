"""
Database configuration module for Smart Clinic Management System.

This module handles database connections, session management, and
configuration following separation of concerns and defensive coding
principles.
"""

import os
import logging
import re
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _get_int_setting(name: str, default: int, minimum: int = 0) -> int:
    """Read a bounded integer setting without making startup fragile."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("Ignoring invalid %s=%r; using %d", name, raw_value, default)
        return default
    if value < minimum:
        logger.warning(
            "Ignoring %s=%d below minimum %d; using %d",
            name,
            value,
            minimum,
            default,
        )
        return default
    return value


def _get_float_setting(name: str, default: float, minimum: float = 0.0) -> float:
    """Read a bounded float setting without making startup fragile."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        logger.warning("Ignoring invalid %s=%r; using %.2f", name, raw_value, default)
        return default
    if value < minimum:
        logger.warning(
            "Ignoring %s=%.2f below minimum %.2f; using %.2f",
            name,
            value,
            minimum,
            default,
        )
        return default
    return value

# Load environment variables
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BACKEND_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path)

# --- DATABASE CONFIGURATION ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    logger.critical("DATABASE_URL environment variable is missing!")
    logger.critical("Please add it to your environment variables or HuggingFace Secrets.")
    raise RuntimeError("DATABASE_URL is required but not set.")

# Diagnostic logging (Masked for security)
try:
    if "@" in SQLALCHEMY_DATABASE_URL:
        host_part = SQLALCHEMY_DATABASE_URL.split("@")[-1].split("/")[0]
        logger.info("Connecting to host: %s", host_part)
    else:
        logger.info("Connecting to local/sqlite database")
except Exception as e:
    logger.warning("Could not parse DB URL for diagnosis: %s", e)


# Normalize PostgreSQL URL format
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip().strip("'").strip('"')

# PgBouncer (Supabase pooler on port 6543): sslmode must be in URL, not connect_args
if ":6543" in SQLALCHEMY_DATABASE_URL and "?" not in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL += "?sslmode=require"

# Async URL configuration
ASYNC_DATABASE_URL = SQLALCHEMY_DATABASE_URL

# Extract ssl mode BEFORE URL conversion
_ssl_match = re.search(r'sslmode=(\w+)', ASYNC_DATABASE_URL)
_ssl_mode = _ssl_match.group(1) if _ssl_match else None

# Strip sslmode from DSN entirely — asyncpg uses connect_args not URL params
if _ssl_mode:
    ASYNC_DATABASE_URL = re.sub(r'[?&]sslmode=\w+', '', ASYNC_DATABASE_URL)
    ASYNC_DATABASE_URL = re.sub(r'\?$', '', ASYNC_DATABASE_URL)

if ASYNC_DATABASE_URL.startswith("postgresql"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
elif ASYNC_DATABASE_URL.startswith("sqlite"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace(
        "sqlite://", "sqlite+aiosqlite://", 1
    )

# Create engines
connect_args = {}
is_supabase_pooler = ":6543" in SQLALCHEMY_DATABASE_URL  # PgBouncer port

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    if not is_supabase_pooler:
        # Direct PostgreSQL: SSL and statement_timeout are safe
        connect_args["sslmode"] = os.getenv("DB_SSL_MODE", "require")
        stmt_timeout = os.getenv('DB_STATEMENT_TIMEOUT')
        if stmt_timeout:
            connect_args["options"] = f"-c statement_timeout={stmt_timeout}"
    else:
        # PgBouncer (Supabase pooler): sslmode goes in URL params, not connect_args
        # statement_timeout via options is incompatible with PgBouncer transaction mode
        pass
elif "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args["check_same_thread"] = False

# Define pool arguments (PostgreSQL only - SQLite uses different pooling)
sync_pool_args = {}
async_pool_args = {}

if "sqlite" not in SQLALCHEMY_DATABASE_URL:
    if is_supabase_pooler:
        # PgBouncer manages its own pool — use minimal SQLAlchemy pool
        # Large pool_size + PgBouncer = connection exhaustion / circuit breaker
        sync_pool_args = {
            "pool_size": _get_int_setting("DB_POOL_SIZE", 3, minimum=1),
            "max_overflow": _get_int_setting("DB_POOL_MAX_OVERFLOW", 2),
            "pool_recycle": _get_int_setting("DB_POOL_RECYCLE", 300, minimum=1),
            "pool_timeout": _get_float_setting("DB_POOL_TIMEOUT", 15.0, minimum=0.1),
        }
    else:
        # Direct PostgreSQL connection — can use larger pool
        sync_pool_args = {
            "pool_size": _get_int_setting("DB_POOL_SIZE", 10, minimum=1),
            "max_overflow": _get_int_setting("DB_POOL_MAX_OVERFLOW", 5),
            "pool_recycle": _get_int_setting("DB_POOL_RECYCLE", 1800, minimum=1),
            "pool_timeout": _get_float_setting("DB_POOL_TIMEOUT", 20.0, minimum=0.1),
        }
    async_pool_args = sync_pool_args.copy()

# PgBouncer (Supabase pooler) should NOT use pool_pre_ping —
# it causes spurious reconnects that trip the circuit breaker.
_pre_ping = not is_supabase_pooler

from pydantic import BaseModel
from rls.register_rls import register_rls
from rls.rls_session import AsyncRlsSession
from backend.core.tenancy import get_current_tenant_id, is_super_admin_bypass


class RlsContext(BaseModel):
    tenant_id: int | None


# Configure extra connection arguments for asyncpg/sqlite
connect_args_async = {}
if "postgresql" in ASYNC_DATABASE_URL:
    connect_args_async["statement_cache_size"] = 0
    # asyncpg expects ssl=True/False (bool), or an ssl.SSLContext object
    if _ssl_mode in ("require", "prefer", "allow"):
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args_async["ssl"] = ctx
    elif _ssl_mode == "disable":
        connect_args_async["ssl"] = False
    elif _ssl_mode in ("verify-ca", "verify-full"):
        connect_args_async["ssl"] = True
elif "sqlite" in ASYNC_DATABASE_URL:
    connect_args_async["check_same_thread"] = False

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=_pre_ping,
    echo=False,
    connect_args=connect_args_async,
    **async_pool_args,
)


def get_async_pool_status() -> dict[str, int | float | None]:
    """Return production-safe pool saturation metrics for diagnostics."""
    pool = async_engine.pool

    def _read_metric(name: str):
        metric = getattr(pool, name, None)
        if not callable(metric):
            return None
        try:
            return metric()
        except (AttributeError, NotImplementedError):
            return None

    pool_size = _read_metric("size")
    max_overflow = sync_pool_args.get("max_overflow")
    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "capacity": (
            pool_size + max_overflow
            if pool_size is not None and max_overflow is not None
            else None
        ),
        "checked_out": _read_metric("checkedout"),
        "checked_in": _read_metric("checkedin"),
        "overflow": _read_metric("overflow"),
        "timeout_seconds": sync_pool_args.get("pool_timeout"),
    }

# Persist instant-like timestamps as UTC-by-convention naive datetimes.
# SQLAlchemy callable defaults can be materialized only when a statement is
# compiled, and bulk INSERTs arrive here as nested list/tuple parameter sets.
# Normalize recursively so asyncpg never receives an aware datetime for a
# TIMESTAMP WITHOUT TIME ZONE column.
from sqlalchemy import event
import datetime


_POOL_CHECKOUT_STARTED_KEY = "dentix_checkout_started_at"
_POOL_TRACE_ID_KEY = "dentix_checkout_trace_id"
_POOL_TENANT_ID_KEY = "dentix_checkout_tenant_id"
_POOL_HOLD_WARN_SECONDS = _get_float_setting(
    "DB_CONNECTION_HOLD_WARN_SECONDS",
    5.0,
    minimum=0.1,
)


@event.listens_for(async_engine.sync_engine.pool, "checkout")
def _record_pool_checkout(dbapi_connection, connection_record, connection_proxy):
    """Attach request context so long-held connections can be traced safely."""
    del dbapi_connection, connection_proxy
    from backend.core.logging import get_trace_id
    from backend.core.tenancy import get_current_tenant_id

    connection_record.info[_POOL_CHECKOUT_STARTED_KEY] = time.monotonic()
    connection_record.info[_POOL_TRACE_ID_KEY] = get_trace_id()
    connection_record.info[_POOL_TENANT_ID_KEY] = get_current_tenant_id()


@event.listens_for(async_engine.sync_engine.pool, "checkin")
def _record_pool_checkin(dbapi_connection, connection_record):
    """Warn when a request retains a database connection for too long."""
    del dbapi_connection
    started_at = connection_record.info.pop(_POOL_CHECKOUT_STARTED_KEY, None)
    trace_id = connection_record.info.pop(_POOL_TRACE_ID_KEY, None)
    tenant_id = connection_record.info.pop(_POOL_TENANT_ID_KEY, None)
    if started_at is None:
        return

    held_seconds = time.monotonic() - started_at
    if held_seconds < _POOL_HOLD_WARN_SECONDS:
        return

    logger.warning(
        "Database connection held for %.2fs (threshold %.2fs); pool=%s",
        held_seconds,
        _POOL_HOLD_WARN_SECONDS,
        get_async_pool_status(),
        extra={"trace_id": trace_id, "tenant_id": tenant_id},
    )


def _normalize_db_bind_value(value):
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value
        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    if isinstance(value, dict):
        return {key: _normalize_db_bind_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_normalize_db_bind_value(item) for item in value)
    if isinstance(value, list):
        return [_normalize_db_bind_value(item) for item in value]
    return value


@event.listens_for(async_engine.sync_engine, "before_cursor_execute", retval=True)
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    return statement, _normalize_db_bind_value(parameters)


class CustomAsyncRlsSession(AsyncRlsSession):
    async def _execute_set_statements(self):
        bind = self.bind
        if bind and bind.dialect.name != "postgresql":
            self._rls_dirty = False
            return
        await super()._execute_set_statements()

    async def flush(self, objects=None):
        # AsyncRlsSession applies tenant/bypass settings before explicit SQL
        # execution, but SQLAlchemy can flush pending ORM writes without an
        # execute() call. Ensure PostgreSQL sees the correct RLS context before
        # any explicit flush.
        await self._execute_set_statements()
        await super().flush(objects=objects)

    async def commit(self):
        # commit() performs an internal flush. Prime the connection with the
        # current tenant or bypass setting first so add()+commit() is safe even
        # when no SELECT/execute occurred earlier in the transaction.
        await self._execute_set_statements()
        await super().commit()


# Create session makers
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=CustomAsyncRlsSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base for models
Base = declarative_base()
if "postgresql" in ASYNC_DATABASE_URL:
    register_rls(Base)


async def get_async_db():
    """Dependency for asynchronous database sessions."""
    tenant_id = get_current_tenant_id()
    context = RlsContext(tenant_id=tenant_id)
    async with AsyncSessionLocal(context=context) as session:
        if is_super_admin_bypass():
            async with session.bypass_rls() as bypassed_session:
                yield bypassed_session
        else:
            yield session


# Real synchronous engine for synchronous startup/maintenance code.
# async_engine.sync_engine is only an adapter around asyncpg and cannot be used
# by normal synchronous call sites without SQLAlchemy's greenlet bridge.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=_pre_ping,
    echo=False,
    connect_args=connect_args,
    **sync_pool_args,
)
event.listen(engine, "before_cursor_execute", before_cursor_execute, retval=True)
