"""
Database configuration module for Smart Clinic Management System.

This module handles database connections, session management, and
configuration following separation of concerns and defensive coding
principles.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BACKEND_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path)

# --- DATABASE CONFIGURATION ---
# STRICT PRODUCTION ENFORCEMENT: raise error if missing
try:
    SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]
    # Diagnostic logging (Masked for security)
    try:
        host_part = SQLALCHEMY_DATABASE_URL.split("@")[-1].split("/")[0]
        # Extract Project ID (e.g. postgres.project_id:password)
        project_id = SQLALCHEMY_DATABASE_URL.split("@")[0].split(":")[-2].split(".")[-1]
        print(f"[DB_DIAGNOSTIC] Host: {host_part}")
        print(f"[DB_DIAGNOSTIC] Project ID: {project_id}")
    except Exception as e:
        print(f"[DB_DIAGNOSTIC] Could not parse DB URL for diagnosis: {e}")
except KeyError:
    raise RuntimeError(
        "DATABASE_URL environment variable is required and not set. "
        "For tests, set DATABASE_URL=sqlite:///:memory: explicitly."
    )

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

sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=_pre_ping,
    connect_args=connect_args,
    **sync_pool_args,
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL, pool_pre_ping=_pre_ping, echo=False, **async_pool_args
)

# Create session makers
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# Base for models
Base = declarative_base()

# Backward-compatible aliases (deprecated, use SyncSessionLocal)
SessionLocal = SyncSessionLocal
engine = sync_engine


# --- DEPENDENCIES ---
def get_db():
    """Dependency for synchronous database sessions."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Dependency for asynchronous database sessions."""
    async with AsyncSessionLocal() as session:
        yield session

# Register SQLAlchemy event listeners
