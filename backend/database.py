"""
Database configuration module for Smart Clinic Management System.

This module handles database connections, session management, and
configuration following separation of concerns and defensive coding
principles.
"""

import os
import logging
import re
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
        connect_args_async["ssl"] = True
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


# Sync engine alias for dev/staging startup operations only
# (metadata.create_all, drop_all, Alembic). Production path never uses this.
engine = async_engine.sync_engine
