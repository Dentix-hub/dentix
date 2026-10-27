"""OAuth attempts use FORCE RLS and never store plaintext PKCE verifiers."""
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext


@pytest.mark.asyncio
async def test_oauth_attempt_tenant_isolation_and_encrypted_verifier():
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            a, b = models.Tenant(name='OAuth test A'), models.Tenant(name='OAuth test B')
            db.add_all([a, b])
            await db.flush()
            user = models.User(tenant_id=a.id, username='oauth_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            db.add(user)
            await db.commit()
            tenant_a, tenant_b, actor = a.id, b.id, user.id
    now = datetime.now(timezone.utc)
    attempt_id = str(uuid.uuid4())
    token = set_current_tenant_id(tenant_a)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_a)) as db:
            db.add(models.GoogleOAuthAttempt(id=attempt_id, tenant_id=tenant_a, user_id=actor, state_digest=hashlib.sha256(suffix.encode()).hexdigest(), browser_digest='b' * 64, nonce_digest='c' * 64, verifier='synthetic-secret-verifier', connection_generation=0, created_at=now, expires_at=now + timedelta(minutes=10)))
            await db.commit()
            stored = (await db.execute(text('SELECT verifier FROM google_oauth_attempts WHERE id = :id'), {'id': attempt_id})).scalar_one()
            assert stored != 'synthetic-secret-verifier' and 'synthetic-secret-verifier' not in stored
    finally:
        clear_tenant_context(tenant_token=token)
    token = set_current_tenant_id(tenant_b)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_b)) as db:
            assert (await db.execute(select(models.GoogleOAuthAttempt).where(models.GoogleOAuthAttempt.id == attempt_id))).scalar_one_or_none() is None
            db.add(models.GoogleOAuthAttempt(id=str(uuid.uuid4()), tenant_id=tenant_a, user_id=actor, state_digest=hashlib.sha256((suffix + 'other').encode()).hexdigest(), browser_digest='e' * 64, nonce_digest='f' * 64, verifier='synthetic-other', connection_generation=0, created_at=now, expires_at=now + timedelta(minutes=10)))
            with pytest.raises(DBAPIError):
                await db.flush()
            await db.rollback()
    finally:
        clear_tenant_context(tenant_token=token)
