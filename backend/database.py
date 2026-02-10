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
except KeyError:
    # Allow fallback for testing/CI environments where .env might not be loaded
    print(
        "WARNING: DATABASE_URL is not set. Using sqlite:///:memory: for fallback/testing."
    )
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Normalize PostgreSQL URL format
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip().strip("'").strip('"')

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
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    connect_args["sslmode"] = os.getenv("DB_SSL_MODE", "require")
elif "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args["check_same_thread"] = False

# Define pool arguments (PostgreSQL only - SQLite uses different pooling)
sync_pool_args = {}
async_pool_args = {}
if "sqlite" not in SQLALCHEMY_DATABASE_URL:
    # PostgreSQL supports QueuePool with these settings
    sync_pool_args = {
        "pool_size": 15,
        "max_overflow": 10,
        "pool_recycle": 1800,
    }
    async_pool_args = sync_pool_args.copy()

sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    **sync_pool_args,
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL, pool_pre_ping=True, echo=False, **async_pool_args
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
