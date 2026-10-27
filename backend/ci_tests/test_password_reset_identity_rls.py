"""Reset identity bootstrap remains narrow under FORCE RLS."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend import models
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.auth_bootstrap import resolve_password_reset_identity, password_reset_identity_scope


@pytest.mark.asyncio
async def test_reset_identity_bootstrap_binds_tenant_and_denies_orphans():
    suffix = uuid.uuid4().hex[:12]
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Reset identity test', timezone='Africa/Cairo')
            db.add(tenant)
            await db.flush()
            clinic = models.User(username='reset_' + suffix, email='reset_' + suffix + '@example.com', role='admin', tenant_id=tenant.id, is_active=True, hashed_password='synthetic')
            orphan = models.User(username='orphan_' + suffix, email='orphan_' + suffix + '@example.com', role='doctor', tenant_id=None, is_active=True, hashed_password='synthetic')
            system = models.User(username='system_' + suffix, email='system_' + suffix + '@example.com', role='super_admin', tenant_id=None, is_active=True, hashed_password='synthetic')
            db.add_all([clinic, orphan, system])
            await db.flush()
            digest = hashlib.sha256(('synthetic-reset-token-' + suffix).encode()).hexdigest()
            db.add(models.PasswordResetToken(user_id=clinic.id, token=digest, expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)))
            await db.commit()
            clinic_id, tenant_id, orphan_email, system_email = clinic.id, tenant.id, orphan.email, system.email
            clinic_email, clinic_username, system_id = clinic.email, clinic.username, system.id

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as db:
        assert (await db.execute(select(models.User).where(models.User.id == clinic_id))).scalar_one_or_none() is None
        assert await resolve_password_reset_identity(email=clinic_username) is None
        assert await resolve_password_reset_identity(email=orphan_email) is None
        identity = await resolve_password_reset_identity(email=clinic_email.upper())
        assert identity == (clinic_id, tenant_id, 'admin')
        assert await resolve_password_reset_identity(token_hash=digest) == identity
        async with password_reset_identity_scope(db, identity, for_update=True) as (scoped, user):
            assert scoped is db
            assert user.id == clinic_id and user.tenant_id == tenant_id
    identity = await resolve_password_reset_identity(email=system_email)
    assert identity == (system_id, None, 'super_admin')
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as db:
        async with password_reset_identity_scope(db, identity, for_update=True) as (scoped, user):
            assert scoped is not db
            assert user.id == system_id and user.tenant_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize('system_account', [False, True])
async def test_verify_reset_token_http_under_rls(system_account):
    import httpx
    from backend.main import app

    suffix = uuid.uuid4().hex
    raw = 'synthetic-' + suffix
    digest = hashlib.sha256(raw.encode()).hexdigest()
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant_id = None
            if not system_account:
                tenant = models.Tenant(name='Reset verify test', timezone='Africa/Cairo')
                db.add(tenant)
                await db.flush()
                tenant_id = tenant.id
            user = models.User(username='verify_' + suffix, email='verify_' + suffix + '@example.com', role='super_admin' if system_account else 'admin', tenant_id=tenant_id, is_active=True, hashed_password='synthetic')
            db.add(user)
            await db.flush()
            db.add(models.PasswordResetToken(user_id=user.id, token=digest, expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)))
            await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        valid = await client.get('/api/v1/auth/verify-reset-token', params={'token': raw})
        assert valid.status_code == 200, valid.text
        assert valid.json()['data']['valid'] is True
        invalid = await client.get('/api/v1/auth/verify-reset-token', params={'token': raw + 'wrong'})
        assert invalid.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize('system_account', [False, True])
async def test_reset_delivery_and_login_under_rls(system_account, monkeypatch, caplog):
    import asyncio
    import httpx
    from backend.auth import get_password_hash
    from backend.main import app
    from backend import email_service
    from backend.workers.handlers import on_password_reset_requested

    suffix = uuid.uuid4().hex
    username, email = 'journey_' + suffix, 'journey_' + suffix + '@example.com'
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant_id = None
            if not system_account:
                tenant = models.Tenant(name='Reset journey test', timezone='Africa/Cairo')
                db.add(tenant)
                await db.flush()
                tenant_id = tenant.id
            user = models.User(username=username, email=email, role='super_admin' if system_account else 'admin', tenant_id=tenant_id, is_active=True, hashed_password=get_password_hash('OldDental92'))
            db.add(user)
            await db.commit()
            user_id = user.id
    captured = []
    monkeypatch.setattr(email_service, 'send_password_reset_email', lambda address, token, name: captured.append(token) or True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        login = await client.post('/api/v1/auth/token', data={'username': username, 'password': 'OldDental92'})
        assert login.status_code == 200, login.text
        old_refresh = login.json()['refresh_token']
        response = await client.post('/api/v1/auth/forgot-password', json={'email': email})
        unknown = await client.post('/api/v1/auth/forgot-password', json={'email': 'absent_' + suffix + '@example.com'})
        assert response.status_code == unknown.status_code == 200
        assert {k: v for k, v in response.json().items() if k != 'trace_id'} == {k: v for k, v in unknown.json().items() if k != 'trace_id'}
        async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
            async with session.bypass_rls() as db:
                event = (await db.execute(select(models.DomainEvent).where(models.DomainEvent.event_type == 'auth.password_reset.requested', models.DomainEvent.aggregate_id == str(user_id)))).scalar_one()
                assert set(event.payload) == {'encrypted_token'}
                await on_password_reset_requested(event)
                await db.refresh(event)
                assert event.payload == {}
        assert len(captured) == 1
        assert captured[0] not in caplog.text
        verify = await client.get('/api/v1/auth/verify-reset-token', params={'token': captured[0]})
        assert verify.status_code == 200
        attempts = await asyncio.gather(*[
            client.post('/api/v1/auth/reset-password', json={'token': captured[0], 'new_password': 'NewDental92'})
            for _ in range(2)
        ])
        assert sorted(response.status_code for response in attempts) == [200, 400]
        replay = await client.post('/api/v1/auth/reset-password', json={'token': captured[0], 'new_password': 'NewDental92'})
        assert replay.status_code == 400
        expired_session = await client.post('/api/v1/auth/refresh', data={'refresh_token': old_refresh})
        assert expired_session.status_code == 401
        new_login = await client.post('/api/v1/auth/token', data={'username': username, 'password': 'NewDental92'})
        assert new_login.status_code == 200, new_login.text
