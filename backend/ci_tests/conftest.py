"""Fixtures for PostgreSQL-only CI tests."""

import pytest_asyncio

from backend.database import async_engine


@pytest_asyncio.fixture(autouse=True)
async def isolate_async_engine_pool_between_tests():
    """Avoid reusing asyncpg connections across pytest event loops."""
    yield
    await async_engine.dispose()
