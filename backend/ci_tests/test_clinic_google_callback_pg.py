"""OAuth callback resolves tenant through restricted PostgreSQL, not user input."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend import models
from backend.auth import create_access_token
from backend.database import AsyncSessionLocal, RlsContext
from backend.main import app


@pytest.mark.asyncio
async def test_oauth_callback_browser_binding_and_separate_tenant_folders(monkeypatch):
    from backend.routers import clinic_google
    monkeypatch.setenv('FRONTEND_URL', 'https://frontend.example.test')
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    monkeypatch.setattr('backend.services.clinic_google_attempts.authorization_url', lambda **kwargs: kwargs['state'])
    monkeypatch.setattr(clinic_google, 'exchange_and_verify', lambda **kwargs: {'sub': 'same-account', 'email': 'synthetic@example.test', 'refresh_token': 'synthetic-refresh'})
    class FakeProvider:
        def __init__(self, token):
            assert token == 'synthetic-refresh'
        def reserve_ids(self, count):
            return [uuid.uuid4().hex for _ in range(count)]
        def ensure_folder(self, **kwargs):
            return kwargs['folder_id']
    monkeypatch.setattr(clinic_google, 'ClinicDriveProvider', FakeProvider)
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenants = [models.Tenant(name='OAuth Clinic A'), models.Tenant(name='OAuth Clinic B')]
            db.add_all(tenants)
            await db.flush()
            users = [models.User(tenant_id=t.id, username=f'oauth_{suffix}_{i}', email=f'{suffix}_{i}@example.com', hashed_password='synthetic', role='admin', is_active=True) for i, t in enumerate(tenants)]
            db.add_all(users)
            await db.commit()
            identities = [(u.id, u.username, u.tenant_id) for u in users]
    transport = ASGITransport(app=app)
    for user_id, username, tenant_id in identities:
        jwt = create_access_token(data={'sub': username, 'tenant_id': tenant_id, 'role': 'admin'})
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            start = await client.get('/api/v1/settings/drive/auth', headers={'Authorization': f'Bearer {jwt}'})
            assert start.status_code == 200, start.text
            state = start.json()['data']['url']
            async with AsyncClient(transport=transport, base_url='http://test') as wrong_browser:
                denied = await wrong_browser.get('/api/v1/settings/drive/callback', params={'state': state, 'code': 'synthetic-code'})
                assert 'backup_status=error' in denied.headers['location']
            response = await client.get('/api/v1/settings/drive/callback', params={'state': state, 'code': 'synthetic-code'})
            assert 'backup_status=success' in response.headers['location']
            replay = await client.get('/api/v1/settings/drive/callback', params={'state': state, 'code': 'synthetic-code'})
            assert 'backup_status=error' in replay.headers['location']
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            rows = (await db.execute(select(models.Tenant).where(models.Tenant.id.in_([row[2] for row in identities])))).scalars().all()
            assert len(rows) == 2 and all(row.google_account_sub == 'same-account' for row in rows)
            assert len({row.google_root_folder_id for row in rows}) == 2
            assert len({row.google_backup_folder_id for row in rows}) == 2
            assert len({row.google_image_folder_id for row in rows}) == 2
