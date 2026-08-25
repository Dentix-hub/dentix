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
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, text
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

def _prepare_async_database_url(database_url: str) -> tuple[str, dict]:
    """Normalize one sync URL for SQLAlchemy async without leaking credentials."""
    normalized = database_url.strip().strip("'").strip('"')
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql://", 1)

    ssl_match = re.search(r"sslmode=(\w+)", normalized)
    ssl_mode = ssl_match.group(1) if ssl_match else (
        os.getenv("DB_SSL_MODE", "require")
        if normalized.startswith("postgresql")
        else None
    )
    if ssl_mode:
        normalized = re.sub(r"[?&]sslmode=\w+", "", normalized)
        normalized = re.sub(r"\?$", "", normalized)

    async_connect_args: dict = {}
    if normalized.startswith("postgresql"):
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
        async_connect_args["statement_cache_size"] = 0
        if ssl_mode in ("require", "prefer", "allow"):
            import ssl

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            async_connect_args["ssl"] = context
        elif ssl_mode == "disable":
            async_connect_args["ssl"] = False
        elif ssl_mode in ("verify-ca", "verify-full"):
            async_connect_args["ssl"] = True
    elif normalized.startswith("sqlite"):
        normalized = normalized.replace("sqlite://", "sqlite+aiosqlite://", 1)
        async_connect_args["check_same_thread"] = False
    return normalized, async_connect_args


ASYNC_DATABASE_URL, connect_args_async = _prepare_async_database_url(
    SQLALCHEMY_DATABASE_URL
)

# Privileged cross-tenant work MUST use a physically separate PostgreSQL login
# carrying BYPASSRLS. The ordinary application URL is never a fallback on
# PostgreSQL because any SQL injection on that connection could otherwise turn
# an application-controlled GUC into a cross-tenant escape hatch.
_configured_system_database_url = os.getenv("SYSTEM_DATABASE_URL", "").strip()
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    _configured_system_database_url = (
        _configured_system_database_url or SQLALCHEMY_DATABASE_URL
    )

SYSTEM_ASYNC_DATABASE_URL: str | None = None
system_connect_args_async: dict = {}
if _configured_system_database_url:
    SYSTEM_ASYNC_DATABASE_URL, system_connect_args_async = _prepare_async_database_url(
        _configured_system_database_url
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


def rebind_session_tenant(session: AsyncSession, tenant_id: int | None) -> bool:
    """Bind an existing request session to a tenant (HIGH-RLS-01).

    Used by the audited authentication bootstrap: after the identity row is
    resolved, every subsequent statement on this request session — including
    writes to ``users`` — must run WITH a tenant binding so FORCE RLS keeps
    enforcing isolation. ``RlsContext`` is intentionally mutable and
    ``CustomAsyncRlsSession`` re-emits its SET LOCAL statement whenever the
    context changes; flipping ``_rls_dirty`` guarantees that happens even if
    no statement ran inside the bootstrap scope.
    """
    context = getattr(session, "_context", None)
    if not isinstance(context, RlsContext):
        return False
    context.tenant_id = tenant_id
    dirty = getattr(session, "_rls_dirty", None)
    if dirty is not None:
        session._rls_dirty = True
    return True


async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=_pre_ping,
    echo=False,
    connect_args=connect_args_async,
    **async_pool_args,
)

system_async_engine = None
if SYSTEM_ASYNC_DATABASE_URL:
    system_pool_args = {}
    if "sqlite" not in SYSTEM_ASYNC_DATABASE_URL:
        system_pool_args = {
            "pool_size": _get_int_setting("SYSTEM_DB_POOL_SIZE", 2, minimum=1),
            "max_overflow": _get_int_setting("SYSTEM_DB_POOL_MAX_OVERFLOW", 0),
            "pool_recycle": _get_int_setting("DB_POOL_RECYCLE", 1800, minimum=1),
            "pool_timeout": _get_float_setting("DB_POOL_TIMEOUT", 20.0, minimum=0.1),
        }
    system_async_engine = create_async_engine(
        SYSTEM_ASYNC_DATABASE_URL,
        pool_pre_ping=":6543" not in SYSTEM_ASYNC_DATABASE_URL,
        echo=False,
        connect_args=system_connect_args_async,
        **system_pool_args,
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


if system_async_engine is not None:
    event.listen(
        system_async_engine.sync_engine,
        "before_cursor_execute",
        before_cursor_execute,
        retval=True,
    )


class CustomAsyncRlsSession(AsyncRlsSession):
    @asynccontextmanager
    async def bypass_rls(self):
        """Compatibility shim backed by the isolated native BYPASSRLS role.

        The old implementation toggled an application-controlled PostgreSQL
        GUC on the ordinary connection. Keeping the method name avoids a broad
        call-site break while ensuring the yielded session is physically
        separate and cannot be reached through tenant-request SQL injection.
        """
        async with system_session_scope() as session:
            yield session

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

SystemAsyncSessionLocal = (
    async_sessionmaker(
        bind=system_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    if system_async_engine is not None
    else None
)

# Base for models
Base = declarative_base()
if "postgresql" in ASYNC_DATABASE_URL:
    register_rls(Base)


async def get_async_db():
    """Dependency for asynchronous database sessions."""
    tenant_id = get_current_tenant_id()
    if is_super_admin_bypass():
        async with system_session_scope() as session:
            yield session
        return

    context = RlsContext(tenant_id=tenant_id)
    async with AsyncSessionLocal(context=context) as session:
        yield session


@asynccontextmanager
async def system_session_scope():
    """Yield the isolated BYPASSRLS session used only for system operations."""
    if SystemAsyncSessionLocal is None:
        raise RuntimeError(
            "SYSTEM_DATABASE_URL is required for PostgreSQL system operations"
        )
    async with SystemAsyncSessionLocal() as session:
        yield session


async def verify_system_database_role() -> None:
    """Fail closed unless application/system PostgreSQL roles are isolated."""
    if "postgresql" not in ASYNC_DATABASE_URL:
        return
    if system_async_engine is None:
        raise RuntimeError(
            "SYSTEM_DATABASE_URL must use a separate PostgreSQL BYPASSRLS role"
        )

    role_query = text(
        "SELECT current_user, current_database() AS database_name, rolsuper, rolbypassrls "
        "FROM pg_roles WHERE rolname = current_user"
    )
    async with async_engine.connect() as connection:
        app_role = (await connection.execute(role_query)).one()
    if bool(app_role.rolsuper) or bool(app_role.rolbypassrls):
        raise RuntimeError(
            f"DATABASE_URL role '{app_role.current_user}' must be non-superuser NOBYPASSRLS"
        )

    async with system_async_engine.connect() as connection:
        system_role = (
            await connection.execute(
                role_query
            )
        ).one()
    if bool(system_role.rolsuper) or not bool(system_role.rolbypassrls):
        raise RuntimeError(
            f"SYSTEM_DATABASE_URL role '{system_role.current_user}' must be non-superuser BYPASSRLS"
        )
    if app_role.current_user == system_role.current_user:
        raise RuntimeError(
            "DATABASE_URL and SYSTEM_DATABASE_URL must use distinct PostgreSQL roles"
        )
    if app_role.database_name != system_role.database_name:
        raise RuntimeError(
            "DATABASE_URL and SYSTEM_DATABASE_URL must target the same PostgreSQL database"
        )


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
