"""Concurrent PostgreSQL RLS isolation gate.

Runs through the production AsyncSessionLocal/AsyncRlsSession path using the
restricted NOBYPASSRLS CI role. The test deliberately creates more concurrent
sessions than the default SQLAlchemy pool capacity so physical connections are
reused across alternating tenant contexts.
"""

import asyncio

import pytest
from sqlalchemy import select, text

from backend import models
from backend.database import AsyncSessionLocal, RlsContext

TENANT_A = 99365
TENANT_B = 99366
PAYMENT_A = 993651
PAYMENT_B = 993661
PAYMENT_IDS = (PAYMENT_A, PAYMENT_B)


async def _probe_tenant(tenant_id: int, expected_payment_id: int, rounds: int = 4):
    async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
        for _ in range(rounds):
            settings = (
                await db.execute(
                    text(
                        "SELECT current_setting('rls.tenant_id', true), "
                        "current_setting('rls.bypass_rls', true)"
                    )
                )
            ).one()
            assert settings[0] == str(tenant_id)
            assert settings[1] not in {"true", "on", "1"}

            result = await db.execute(
                select(models.SubscriptionPayment.id)
                .where(models.SubscriptionPayment.id.in_(PAYMENT_IDS))
                .order_by(models.SubscriptionPayment.id)
            )
            assert list(result.scalars()) == [expected_payment_id]

            # Force scheduler interleaving while the tenant-scoped transaction
            # still owns its checked-out connection.
            await asyncio.sleep(0)

        await db.rollback()


@pytest.mark.asyncio
async def test_concurrent_tenant_contexts_do_not_leak_across_pool_reuse():
    # Direct PostgreSQL defaults to pool_size=10 + max_overflow=5. Using 36
    # concurrent sessions forces later probes to reuse physical connections
    # previously held by the opposite tenant.
    tasks = []
    for index in range(36):
        if index % 2 == 0:
            tasks.append(_probe_tenant(TENANT_A, PAYMENT_A))
        else:
            tasks.append(_probe_tenant(TENANT_B, PAYMENT_B))

    await asyncio.gather(*tasks)

    # Sequential A -> B -> A proves reused connections are re-primed even when
    # the previous transaction belonged to a different tenant.
    await _probe_tenant(TENANT_A, PAYMENT_A, rounds=2)
    await _probe_tenant(TENANT_B, PAYMENT_B, rounds=2)
    await _probe_tenant(TENANT_A, PAYMENT_A, rounds=2)


@pytest.mark.asyncio
async def test_missing_tenant_context_cannot_inherit_previous_pool_tenant():
    # Warm the pool with both tenant identities first.
    await _probe_tenant(TENANT_A, PAYMENT_A, rounds=1)
    await _probe_tenant(TENANT_B, PAYMENT_B, rounds=1)

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as db:
        result = await db.execute(
            select(models.SubscriptionPayment.id)
            .where(models.SubscriptionPayment.id.in_(PAYMENT_IDS))
            .order_by(models.SubscriptionPayment.id)
        )
        assert list(result.scalars()) == []
        await db.rollback()
