"""Durable Drive backup retries use one file and retain tenant isolation."""
import base64
import uuid

import pytest
from sqlalchemy import select

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.clinic_drive_backup import queue_drive_backup, run_drive_backup
from backend.services.clinic_drive_provider import DriveFailure


@pytest.mark.asyncio
async def test_backup_retry_reuses_file_and_ciphertext(monkeypatch):
    suffix = uuid.uuid4().hex
    monkeypatch.setenv('TENANT_BACKUP_KEY_ID', 'synthetic')
    monkeypatch.setenv('TENANT_BACKUP_ENCRYPTION_KEY', base64.urlsafe_b64encode(b'a' * 32).decode())
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    monkeypatch.setenv('TENANT_BACKUP_MAX_BYTES', '1000000')
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Backup clinic', google_refresh_token='synthetic-token', google_connection_status='connected', google_connection_generation=4, google_backup_folder_id='synthetic-folder')
            db.add(tenant)
            await db.flush()
            actor = models.User(tenant_id=tenant.id, username='backup_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            db.add(actor)
            await db.commit()
            tenant_id, actor_id = tenant.id, actor.id
    class FakeProvider:
        files = {}
        calls = 0
        def __init__(self, token):
            assert token == 'synthetic-token'
        def reserve_ids(self, count):
            assert count == 1
            return ['file-' + suffix]
        def upload_backup(self, **kwargs):
            self.__class__.calls += 1
            previous = self.files.setdefault(kwargs['file_id'], kwargs['digest'])
            assert previous == kwargs['digest']
            if self.calls == 1:
                raise DriveFailure('transient')  # Remote creation succeeded but response was lost.
            return {'id': kwargs['file_id']}
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            first = await queue_drive_backup(db, tenant_id=tenant_id, actor_id=actor_id, request_key='request-' + suffix)
            second = await queue_drive_backup(db, tenant_id=tenant_id, actor_id=actor_id, request_key='request-' + suffix)
            assert first.id == second.id
            operation_id = first.id
        with pytest.raises(RuntimeError):
            await run_drive_backup(tenant_id=tenant_id, operation_id=operation_id, provider_factory=FakeProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == operation_id))).scalar_one()
            assert op.status == 'running' and op.encrypted_payload and op.remote_file_id == 'file-' + suffix
            saved_digest = op.archive_digest
        await run_drive_backup(tenant_id=tenant_id, operation_id=operation_id, provider_factory=FakeProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == operation_id))).scalar_one()
            assert op.status == 'completed' and op.encrypted_payload is None and op.archive_digest == saved_digest
            assert len(FakeProvider.files) == 1 and FakeProvider.calls == 2
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_quota_failure_preserves_google_connection(monkeypatch):
    suffix = uuid.uuid4().hex
    monkeypatch.setenv('TENANT_BACKUP_KEY_ID', 'synthetic')
    monkeypatch.setenv('TENANT_BACKUP_ENCRYPTION_KEY', base64.urlsafe_b64encode(b'a' * 32).decode())
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Quota clinic', google_refresh_token='synthetic-token', google_connection_status='connected', google_connection_generation=2, google_backup_folder_id='synthetic-folder')
            db.add(tenant)
            await db.flush()
            actor = models.User(tenant_id=tenant.id, username='quota_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            db.add(actor)
            await db.commit()
            tenant_id, actor_id = tenant.id, actor.id
    class QuotaProvider:
        def __init__(self, token):
            pass
        def reserve_ids(self, count):
            raise DriveFailure('quota')
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await queue_drive_backup(db, tenant_id=tenant_id, actor_id=actor_id, request_key='quota-' + suffix)
            operation_id = op.id
        with pytest.raises(RuntimeError):
            await run_drive_backup(tenant_id=tenant_id, operation_id=operation_id, provider_factory=QuotaProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == operation_id))).scalar_one()
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            assert op.status == 'failed' and op.error_code == 'quota'
            assert tenant.google_connection_status == 'connected' and tenant.google_refresh_token == 'synthetic-token'
    finally:
        clear_tenant_context(tenant_token=token)
