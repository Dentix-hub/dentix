"""
Regression test for P01-01 & P01-03: Proving that unconfigured/default startup or subscription expiry
must NOT set tenant.is_active = False or cause total tenant lockout.
"""

from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.models.tenant import Tenant
from backend.workers.subscription_checker import check_expired_subscriptions


@pytest.mark.asyncio
async def test_subscription_worker_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SUBSCRIPTION_WORKER_ENABLED", raising=False)
    db = AsyncMock()
    count = await check_expired_subscriptions.fn(db)
    assert count == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_subscription_worker_enforce_mode_preserves_is_active(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")

    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    tenant = Tenant(
        id=999,
        name="Test Clinic",
        is_active=True,
        subscription_end_date=past_date,
        grace_period_until=past_date,
        subscription_status="active",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tenant]
    db.execute.return_value = mock_result

    count = await check_expired_subscriptions.fn(db)
    assert count == 1
    assert tenant.subscription_status == "expired"
    assert tenant.is_active is True, "CRITICAL: tenant.is_active must remain True to preserve clinical reads!"


@pytest.mark.asyncio
async def test_subscription_worker_observe_mode_does_not_mutate(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "observe")

    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    tenant = Tenant(
        id=999,
        name="Test Clinic",
        is_active=True,
        subscription_end_date=past_date,
        grace_period_until=past_date,
        subscription_status="active",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tenant]
    db.execute.return_value = mock_result

    count = await check_expired_subscriptions.fn(db)
    assert count == 1
    assert tenant.subscription_status == "active"
    assert tenant.is_active is True
    db.commit.assert_not_called()
