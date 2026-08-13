"""
Database configuration module for Smart Clinic Management System.

This module handles database connections, session management, and
configuration following separation of concerns and defensive coding
principles.
"""

import os
import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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


SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip().strip("'").strip('"')


def _replace_database_scheme(database_url: str, scheme: str) -> str:
    """Replace only the URL scheme while preserving every slash and path byte."""
    _current_scheme, separator, remainder = database_url.partition(":")
    if not separator:
        return database_url
    return f"{scheme}:{remainder}"


# Keep the sync and async SQLAlchemy drivers explicit. Replacing a substring
# is unsafe because ``sqlite://`` also occurs inside ``sqlite+aiosqlite://``.
_sync_url_parts = urlsplit(SQLALCHEMY_DATABASE_URL)
_base_database_scheme = _sync_url_parts.scheme.split("+", 1)[0]
if _base_database_scheme == "postgres":
    _base_database_scheme = "postgresql"
if _base_database_scheme in {"postgresql", "sqlite"}:
    SQLALCHEMY_DATABASE_URL = _replace_database_scheme(
        SQLALCHEMY_DATABASE_URL,
        _base_database_scheme,
    )


def _resolve_postgres_ssl_mode(database_url: str, configured_mode: str | None) -> str:
    """Resolve SSL without breaking local PostgreSQL services such as CI."""
    # An explicit deployment policy must override legacy sslmode values that
    # may still be embedded in DATABASE_URL.
    if configured_mode:
        return configured_mode
    ssl_match = re.search(r"(?:[?&])sslmode=([\w-]+)", database_url)
    if ssl_match:
        return ssl_match.group(1)

    try:
        hostname = (urlsplit(database_url).hostname or "").lower()
    except ValueError:
        hostname = ""

    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return "disable"
    return "require"


def _set_postgres_query_parameter(
    database_url: str,
    parameter: str,
    value: str,
) -> str:
    """Set a PostgreSQL DSN query parameter without corrupting other options."""
    if "postgresql" not in database_url:
        return database_url

    parsed = urlsplit(database_url)
    updated_query: list[tuple[str, str]] = []
    replaced = False
    for key, current_value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() == parameter.lower():
            if not replaced:
                updated_query.append((key, value))
                replaced = True
            continue
        updated_query.append((key, current_value))
    if not replaced:
        updated_query.append((parameter, value))

    return urlunsplit(parsed._replace(query=urlencode(updated_query)))


def _apply_postgres_ssl_mode(database_url: str, ssl_mode: str) -> str:
    """Apply the resolved policy to the sync PostgreSQL DSN."""
    return _set_postgres_query_parameter(database_url, "sslmode", ssl_mode)


def _strip_postgres_ssl_parameters(database_url: str) -> str:
    """Remove libpq-only SSL options before passing the DSN to asyncpg."""
    if "postgresql" not in database_url:
        return database_url

    parsed = urlsplit(database_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in {"sslmode", "sslrootcert"}
    ]
    return urlunsplit(parsed._replace(query=urlencode(query)))


_ssl_mode = _resolve_postgres_ssl_mode(
    SQLALCHEMY_DATABASE_URL,
    os.getenv("DB_SSL_MODE"),
)
_ssl_ca_cert = os.getenv("DB_SSL_CA_CERT")

# Keep the sync DSN aligned with the resolved deployment policy. This is
# required for PgBouncer, where sslmode must be carried in the URL.
SQLALCHEMY_DATABASE_URL = _apply_postgres_ssl_mode(
    SQLALCHEMY_DATABASE_URL,
    _ssl_mode,
)
if _ssl_ca_cert:
    SQLALCHEMY_DATABASE_URL = _set_postgres_query_parameter(
        SQLALCHEMY_DATABASE_URL,
        "sslrootcert",
        _ssl_ca_cert,
    )

# Async URL configuration
ASYNC_DATABASE_URL = SQLALCHEMY_DATABASE_URL

_environment = os.getenv("ENVIRONMENT", "development").lower()
if "postgresql" in SQLALCHEMY_DATABASE_URL and _environment in {
    "production",
    "prod",
}:
    if _ssl_mode != "verify-full":
        raise RuntimeError(
            "Production PostgreSQL requires DB_SSL_MODE=verify-full "
            "to validate the server certificate and hostname."
        )
    if not _ssl_ca_cert or not os.path.isfile(_ssl_ca_cert):
        raise RuntimeError(
            "Production PostgreSQL requires DB_SSL_CA_CERT to point to "
            "the trusted database CA certificate."
        )

# Strip sslmode from DSN entirely — asyncpg uses connect_args not URL params
if _ssl_mode:
    ASYNC_DATABASE_URL = _strip_postgres_ssl_parameters(ASYNC_DATABASE_URL)

_async_url_parts = urlsplit(ASYNC_DATABASE_URL)
_async_base_scheme = _async_url_parts.scheme.split("+", 1)[0]
if _async_base_scheme == "postgres":
    _async_base_scheme = "postgresql"
if _async_base_scheme == "postgresql":
    ASYNC_DATABASE_URL = _replace_database_scheme(
        ASYNC_DATABASE_URL,
        "postgresql+asyncpg",
    )
elif _async_base_scheme == "sqlite":
    ASYNC_DATABASE_URL = _replace_database_scheme(
        ASYNC_DATABASE_URL,
        "sqlite+aiosqlite",
    )

# Create engines
connect_args = {}
is_supabase_pooler = ":6543" in SQLALCHEMY_DATABASE_URL  # PgBouncer port

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    if not is_supabase_pooler:
        # Direct PostgreSQL: SSL and statement_timeout are safe
        connect_args["sslmode"] = _ssl_mode
        if _ssl_ca_cert:
            connect_args["sslrootcert"] = _ssl_ca_cert
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
            "pool_size": 3,
            "max_overflow": 2,
            "pool_recycle": 300,
            "pool_timeout": 15,
        }
    else:
        # Direct PostgreSQL connection — can use larger pool
        sync_pool_args = {
            "pool_size": 10,
            "max_overflow": 5,
            "pool_recycle": 1800,
            "pool_timeout": 20,
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
        import ssl
        ctx = ssl.create_default_context(cafile=_ssl_ca_cert)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = _ssl_mode == "verify-full"
        connect_args_async["ssl"] = ctx
elif "sqlite" in ASYNC_DATABASE_URL:
    connect_args_async["check_same_thread"] = False

async_engine = create_async_engine(
    ASYNC_DATABASE_URL, pool_pre_ping=_pre_ping, echo=False, connect_args=connect_args_async, **async_pool_args
)

# Strip timezone info from datetimes before sending to database
from sqlalchemy import event
import datetime

@event.listens_for(async_engine.sync_engine, "before_cursor_execute", retval=True)
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if parameters:
        if isinstance(parameters, dict):
            for key, val in parameters.items():
                if isinstance(val, datetime.datetime) and val.tzinfo is not None:
                    parameters[key] = val.replace(tzinfo=None)
        elif isinstance(parameters, list):
            for i, val in enumerate(parameters):
                if isinstance(val, datetime.datetime) and val.tzinfo is not None:
                    parameters[i] = val.replace(tzinfo=None)
        elif isinstance(parameters, tuple):
            new_params = []
            for val in parameters:
                if isinstance(val, datetime.datetime) and val.tzinfo is not None:
                    new_params.append(val.replace(tzinfo=None))
                else:
                    new_params.append(val)
            parameters = tuple(new_params)
    return statement, parameters

class CustomAsyncRlsSession(AsyncRlsSession):
    async def _execute_set_statements(self):
        bind = self.bind
        if bind and bind.dialect.name != "postgresql":
            self._rls_dirty = False
            return
        await super()._execute_set_statements()

# Create session makers
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=CustomAsyncRlsSession, expire_on_commit=False, autoflush=False
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

# Register SQLAlchemy event listeners


from sqlalchemy import create_engine

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, pool_pre_ping=_pre_ping, echo=False, connect_args=connect_args, **sync_pool_args
)
