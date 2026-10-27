"""A restore-operation record cannot be read or written by another tenant."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext


@pytest.mark.asyncio
async def test_restore_operation_rls_isolates_reads_and_writes():
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            a = models.Tenant(name='Synthetic restore A')
            b = models.Tenant(name='Synthetic restore B')
            db.add_all([a, b])
            await db.flush()
            user = models.User(tenant_id=a.id, username='restore_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            db.add(user)
            await db.commit()
            tenant_a, tenant_b, actor = a.id, b.id, user.id
    op_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    token = set_current_tenant_id(tenant_a)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_a)) as db:
            db.add(models.TenantDataOperation(id=op_id, tenant_id=tenant_a, actor_id=actor, kind='restore', status='previewed', archive_digest='a' * 64, confirmation_digest='b' * 64, expires_at=now + timedelta(minutes=10), created_at=now))
            await db.commit()
    finally:
        clear_tenant_context(tenant_token=token)
    token = set_current_tenant_id(tenant_b)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_b)) as db:
            assert (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == op_id))).scalar_one_or_none() is None
            db.add(models.TenantDataOperation(id=str(uuid.uuid4()), tenant_id=tenant_a, actor_id=actor, kind='restore', status='previewed', archive_digest='a' * 64, confirmation_digest='b' * 64, expires_at=now + timedelta(minutes=10), created_at=now))
            with pytest.raises(DBAPIError):
                await db.flush()
            await db.rollback()
    finally:
        clear_tenant_context(tenant_token=token)
