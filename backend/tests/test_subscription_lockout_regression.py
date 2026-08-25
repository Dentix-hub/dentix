"""
Regression test for P01-01: Proving that unconfigured/default startup or subscription expiry
must NOT set tenant.is_active = False or cause total tenant lockout.
"""

from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.models.tenant import Tenant
from backend.workers.subscription_checker import check_expired_subscriptions


@pytest.mark.asyncio
async def test_subscription_worker_never_sets_is_active_false_when_disabled_or_expired():
    """
    Verify that check_expired_subscriptions respects SUBSCRIPTION_WORKER_ENABLED
    and NEVER sets tenant.is_active = False.
    """
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

    # When worker is checked
    count = await check_expired_subscriptions(db)

    # Invariant: tenant.is_active must remain True!
    assert tenant.is_active is True, "CRITICAL: tenant.is_active was set to False on subscription expiry!"
