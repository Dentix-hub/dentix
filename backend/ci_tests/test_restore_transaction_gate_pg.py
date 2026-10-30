"""PostgreSQL transaction gate covers real business writes across tenants."""
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext

NAMESPACE = 1146377304


@pytest.mark.asyncio
async def test_exclusive_restore_blocks_same_tenant_writes_but_not_other_tenants():
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            a, b = models.Tenant(name='Gate test A'), models.Tenant(name='Gate test B')
            db.add_all([a, b])
            await db.commit()
            tenant_a, tenant_b = a.id, b.id
    token = set_current_tenant_id(tenant_a)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_a)) as restore:
            await restore.execute(text('SELECT pg_advisory_xact_lock(:namespace, :tenant)'), {'namespace': NAMESPACE, 'tenant': tenant_a})
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_a)) as writer:
                await writer.execute(text("SET LOCAL lock_timeout = '200ms'"))
                writer.add(models.Expense(tenant_id=tenant_a, item_name='A synthetic', category='Other', cost=Decimal('1')))
                with pytest.raises(DBAPIError):
                    await writer.flush()
                await writer.rollback()
            clear_tenant_context(tenant_token=token)
            token = set_current_tenant_id(tenant_b)
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_b)) as writer:
                writer.add(models.Expense(tenant_id=tenant_b, item_name='B synthetic', category='Other', cost=Decimal('1')))
                await writer.commit()
                assert (await writer.execute(select(models.Expense).where(models.Expense.tenant_id == tenant_b))).scalars().first()
            await restore.rollback()
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_normal_write_blocks_restore_gate_until_rollback():
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Gate shared test')
            db.add(tenant)
            await db.commit()
            tenant_id = tenant.id
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as writer:
            writer.add(models.Expense(tenant_id=tenant_id, item_name='Pending', category='Other', cost=Decimal('1')))
            await writer.flush()
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as restore:
                stmt = text('SELECT pg_try_advisory_xact_lock(:namespace, :tenant)')
                assert not (await restore.execute(stmt, {'namespace': NAMESPACE, 'tenant': tenant_id})).scalar_one()
                await writer.rollback()
                assert (await restore.execute(stmt, {'namespace': NAMESPACE, 'tenant': tenant_id})).scalar_one()
                await restore.rollback()
    finally:
        clear_tenant_context(tenant_token=token)
