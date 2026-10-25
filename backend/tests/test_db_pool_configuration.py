import os
import importlib
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend import database


@pytest.fixture(autouse=True)
def _restore_database_module():
    """Ensure database module is restored with clean test environment after reloads."""
    orig_env = os.environ.copy()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(orig_env)
        importlib.reload(database)


def test_pooler_url_defaults(monkeypatch):
    """
    Supabase pooler (:6543) defaults:
    - pool_pre_ping must be False (circuit-breaker prevention)
    - pool_size = 3
    - max_overflow = 2
    - pool_timeout = 15.0
    - pool_recycle = 300
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-cool.supabase.co:6543/postgres")
    monkeypatch.delenv("SYSTEM_DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_POOL_PRE_PING", raising=False)
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_POOL_TIMEOUT", raising=False)

    importlib.reload(database)

    assert database.is_supabase_pooler is True
    assert database._pre_ping is False
    assert database.async_engine.pool._pre_ping is False
    assert database.sync_pool_args["pool_size"] == 3
    assert database.sync_pool_args["max_overflow"] == 2
    assert database.sync_pool_args["pool_timeout"] == 15.0
    assert database.sync_pool_args["pool_recycle"] == 300
    assert database.async_pool_args["pool_size"] == 3


def test_direct_postgresql_url_defaults(monkeypatch):
    """
    Direct PostgreSQL (:5432) defaults:
    - pool_pre_ping must be True (healthy fail-fast on severed sockets)
    - pool_size = 10
    - max_overflow = 5
    - pool_timeout = 20.0
    - pool_recycle = 1800
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-cool.supabase.co:5432/postgres")
    monkeypatch.delenv("SYSTEM_DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_POOL_PRE_PING", raising=False)
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_POOL_TIMEOUT", raising=False)

    importlib.reload(database)

    assert database.is_supabase_pooler is False
    assert database._pre_ping is True
    assert database.async_engine.pool._pre_ping is True
    assert database.sync_pool_args["pool_size"] == 10
    assert database.sync_pool_args["max_overflow"] == 5
    assert database.sync_pool_args["pool_timeout"] == 20.0
    assert database.sync_pool_args["pool_recycle"] == 1800


def test_pooler_pre_ping_explicit_env_override(monkeypatch):
    """DB_POOL_PRE_PING environment variable can explicitly override pooler pre_ping default."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-cool.supabase.co:6543/postgres")
    monkeypatch.setenv("DB_POOL_PRE_PING", "true")

    importlib.reload(database)

    assert database.is_supabase_pooler is True
    assert database._pre_ping is True
    assert database.async_engine.pool._pre_ping is True


def test_pool_size_and_overflow_env_overrides(monkeypatch):
    """DB_POOL_SIZE, DB_POOL_MAX_OVERFLOW, and DB_POOL_TIMEOUT env vars override defaults."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-cool.supabase.co:6543/postgres")
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_POOL_MAX_OVERFLOW", "4")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "45.0")

    importlib.reload(database)

    assert database.sync_pool_args["pool_size"] == 7
    assert database.sync_pool_args["max_overflow"] == 4
    assert database.sync_pool_args["pool_timeout"] == 45.0
    assert database.async_pool_args["pool_size"] == 7
    assert database.async_pool_args["max_overflow"] == 4


def test_system_async_engine_pre_ping_consistency(monkeypatch):
    """system_async_engine pre_ping is consistent with is_supabase_pooler logic."""
    # When SYSTEM_DATABASE_URL uses pooler port 6543, pre_ping must default to False
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-cool.supabase.co:6543/postgres")
    monkeypatch.setenv("SYSTEM_DATABASE_URL", "postgresql://sys:pass@ep-cool.supabase.co:6543/postgres")
    monkeypatch.delenv("DB_POOL_PRE_PING", raising=False)

    importlib.reload(database)

    assert database.system_async_engine is not None
    assert database.system_async_engine.pool._pre_ping is False

    # When SYSTEM_DATABASE_URL uses direct port 5432, pre_ping must default to True
    monkeypatch.setenv("SYSTEM_DATABASE_URL", "postgresql://sys:pass@ep-cool.supabase.co:5432/postgres")
    importlib.reload(database)

    assert database.system_async_engine is not None
    assert database.system_async_engine.pool._pre_ping is True


@pytest.mark.asyncio
async def test_ai_query_releases_db_connection_before_agent_process(monkeypatch):
    """
    Verify that AIService.process_query commits/releases its DB connection BEFORE
    awaiting self.agent.process, so slow external model calls do not hold a pool connection.
    """
    from backend.services.ai_service import AIService
    from backend import models

    mock_db = AsyncMock()
    # Mock quota check scalar
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    mock_user = MagicMock(spec=models.User)
    mock_user.id = 1
    mock_user.username = "test_user"
    mock_user.tenant_id = 10
    mock_user.tenant = MagicMock(spec=models.Tenant)
    mock_user.tenant.id = 10
    mock_user.tenant.subscription_plan = MagicMock()
    mock_user.tenant.subscription_plan.is_ai_enabled = True
    mock_user.tenant.subscription_plan.ai_daily_limit = 50

    service = AIService(db=mock_db, user=mock_user)

    agent_process_called = False

    async def fake_agent_process(*args, **kwargs):
        nonlocal agent_process_called
        agent_process_called = True
        # At the time agent.process is invoked, db.commit must ALREADY have been awaited!
        assert mock_db.commit.await_count >= 1, "db.commit must be awaited BEFORE agent.process"
        return {
            "tool": "greeting",
            "message": "مرحبا بك",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

    service.agent.process = AsyncMock(side_effect=fake_agent_process)

    # Execute query
    response = await service.process_query(text="مرحبا")

    assert agent_process_called is True
    assert response.success is True
    assert response.message == "مرحبا بك"
