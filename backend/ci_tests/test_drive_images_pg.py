"""Drive image upload, protected reads and deletion on synthetic PostgreSQL."""
import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import select

from backend import models
from backend.auth import create_access_token
from backend.core.security import get_encryption_manager
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.main import app
from backend.services.drive_image_operations import stage_image_upload, run_image_upload, queue_image_delete, run_image_deletion


@pytest.fixture(autouse=True)
def _configure_test_encryption_key(monkeypatch):
    monkeypatch.setenv('ENCRYPTION_KEY', get_encryption_manager()._key)


@pytest.mark.asyncio
async def test_drive_image_upload_protected_cache_and_tracked_delete(monkeypatch):
    suffix = uuid.uuid4().hex
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    class FakeProvider:
        files = {}
        reads = 0
        def __init__(self, token):
            assert token == 'synthetic-refresh'
        def reserve_ids(self, count):
            return [uuid.uuid4().hex for _ in range(count)]
        def upload_image(self, **kwargs):
            self.files[kwargs['file_id']] = kwargs
        def download_image(self, **kwargs):
            self.__class__.reads += 1
            value = self.files[kwargs['file_id']]
            assert value['tenant_id'] == kwargs['tenant_id'] and value['storage_uuid'] == kwargs['storage_uuid']
            return value['content']
        def delete_image(self, **kwargs):
            value = self.files.get(kwargs['file_id'])
            if value:
                assert value['tenant_id'] == kwargs['tenant_id'] and value['storage_uuid'] == kwargs['storage_uuid']
                del self.files[kwargs['file_id']]
    monkeypatch.setattr('backend.services.clinic_drive_provider.ClinicDriveProvider', FakeProvider)
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            a, b = models.Tenant(name='Image Clinic A', google_refresh_token='synthetic-refresh', google_connection_status='connected', google_connection_generation=3, google_account_sub='synthetic-sub', google_image_folder_id='synthetic-folder'), models.Tenant(name='Image Clinic B')
            db.add_all([a, b])
            await db.flush()
            user = models.User(tenant_id=a.id, username='image_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            other = models.User(tenant_id=b.id, username='other_' + suffix, email='other_' + suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=a.id, name='Synthetic image patient', age=30, phone='0', medical_history='', notes='')
            doctor = models.User(tenant_id=a.id, username='doctor_' + suffix, email='doctor_' + suffix + '@example.com', hashed_password='synthetic', role='doctor', patient_visibility_mode='all_assigned', is_active=True)
            db.add_all([user, other, patient, doctor])
            await db.commit()
            tenant_id, user_id, username, other_name, other_tenant, patient_id, doctor_name = a.id, user.id, user.username, other.username, b.id, patient.id, doctor.username
    original_io = io.BytesIO()
    Image.new('RGB', (40, 30), 'red').save(original_io, format='PNG')
    original = original_io.getvalue()
    context = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            user = (await db.execute(select(models.User).where(models.User.id == user_id))).scalar_one()
            attachment = await stage_image_upload(db, tenant=tenant, user=user, patient_id=patient_id, filename='synthetic.png', mime='image/png', note=None, content=original, request_key='upload-' + suffix)
            storage_uuid, attachment_id = attachment.storage_uuid, attachment.id
            assert attachment.storage_status == 'pending'
        await run_image_upload(tenant_id=tenant_id, operation_id=storage_uuid, provider_factory=FakeProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            attachment = (await db.execute(select(models.Attachment).where(models.Attachment.id == attachment_id))).scalar_one()
            assert attachment.storage_status == 'ready' and len(FakeProvider.files) == 2
            from backend.services.tenant_archive_export import export_clinic_archive_data
            from backend.services.tenant_archive_registry import validate_archive_sections, validate_archive_references, validate_archive_values
            from backend.services.tenant_archive_identity import resolve_staff_mapping
            from backend.services.tenant_archive_import import replace_clinic_business_data
            data = validate_archive_sections(await export_clinic_archive_data(db, tenant_id), tenant_id=tenant_id)
            validate_archive_values(data)
            validate_archive_references(data, tenant_id=tenant_id)
            staff = await resolve_staff_mapping(db, tenant_id, data['staff_references'])
            _, mapping = await replace_clinic_business_data(db, tenant_id=tenant_id, data=data, staff_mapping=staff)
            await db.commit()
            restored = (await db.execute(select(models.Attachment).where(models.Attachment.storage_uuid == storage_uuid, models.Attachment.tenant_id == tenant_id))).scalar_one()
            assert restored.patient_id == mapping['patients'][patient_id] and restored.patient_id != patient_id
            assert restored.storage_uuid == storage_uuid and restored.file_path.endswith(f'{storage_uuid}/content')
            attachment_id = restored.id
        token = create_access_token(data={'sub': username, 'tenant_id': tenant_id, 'role': 'admin'})
        other_token = create_access_token(data={'sub': other_name, 'tenant_id': other_tenant, 'role': 'admin'})
        doctor_token = create_access_token(data={'sub': doctor_name, 'tenant_id': tenant_id, 'role': 'doctor'})
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            path = f'/api/v1/upload/drive/{storage_uuid}/content'
            response = await client.get(path, headers={'Authorization': f'Bearer {token}'})
            assert response.status_code == 200 and response.content == original
            assert response.headers['cache-control'] == 'private, no-store'
            cached = await client.get(path, headers={'Authorization': f'Bearer {token}', 'Range': 'bytes=0-3'})
            assert cached.status_code == 206 and cached.content == original[:4] and FakeProvider.reads == 1
            denied = await client.get(path, headers={'Authorization': f'Bearer {other_token}', 'If-None-Match': response.headers['etag']})
            assert denied.status_code == 404
            denied_doctor = await client.get(path, headers={'Authorization': f'Bearer {doctor_token}', 'If-None-Match': response.headers['etag']})
            assert denied_doctor.status_code == 404
            thumbnail = await client.get(path, params={'variant': 'thumbnail'}, headers={'Authorization': f'Bearer {token}'})
            assert thumbnail.status_code == 200 and thumbnail.headers['content-type'] == 'image/jpeg'
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
                tenant.google_connection_status = 'disconnected'
                tenant.google_connection_generation += 1
                await db.commit()
            disconnected = await client.get(path, headers={'Authorization': f'Bearer {token}', 'If-None-Match': response.headers['etag']})
            assert disconnected.status_code == 503
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            tenant.google_connection_status = 'connected'
            user = (await db.execute(select(models.User).where(models.User.id == user_id))).scalar_one()
            attachment = (await db.execute(select(models.Attachment).where(models.Attachment.id == attachment_id))).scalar_one()
            await queue_image_delete(db, attachment=attachment, user=user)
            deletion = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.kind == 'drive_image_delete'))).scalar_one()
            delete_id = deletion.id
            assert attachment.storage_status == 'deleting'
        await run_image_deletion(tenant_id=tenant_id, operation_id=delete_id, provider_factory=FakeProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            assert (await db.execute(select(models.Attachment).where(models.Attachment.id == attachment_id))).scalar_one_or_none() is None
            assert not FakeProvider.files
    finally:
        clear_tenant_context(tenant_token=context)


@pytest.mark.asyncio
async def test_interrupted_upload_tracks_and_cleans_remote_original(monkeypatch):
    from backend.services.clinic_drive_provider import DriveFailure
    suffix = uuid.uuid4().hex
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    class QuotaProvider:
        files = set()
        def __init__(self, token):
            pass
        def reserve_ids(self, count):
            return [uuid.uuid4().hex for _ in range(count)]
        def upload_image(self, **kwargs):
            if kwargs['variant'] == 'thumbnail':
                raise DriveFailure('quota')
            self.files.add(kwargs['file_id'])
        def delete_image(self, **kwargs):
            self.files.discard(kwargs['file_id'])
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Image failure clinic', google_refresh_token='synthetic-refresh', google_connection_status='connected', google_connection_generation=1, google_account_sub='synthetic-sub', google_image_folder_id='synthetic-folder')
            db.add(tenant)
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='failure_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=tenant.id, name='Synthetic', age=30, phone='0', medical_history='', notes='')
            db.add_all([user, patient])
            await db.commit()
            tenant_id, user_id, patient_id = tenant.id, user.id, patient.id
    output = io.BytesIO()
    Image.new('RGB', (10, 10), 'red').save(output, format='PNG')
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            user = (await db.execute(select(models.User).where(models.User.id == user_id))).scalar_one()
            attachment = await stage_image_upload(db, tenant=tenant, user=user, patient_id=patient_id, filename='synthetic.png', mime='image/png', note=None, content=output.getvalue(), request_key='failed-' + suffix)
            storage_uuid = attachment.storage_uuid
        with pytest.raises(RuntimeError):
            await run_image_upload(tenant_id=tenant_id, operation_id=storage_uuid, provider_factory=QuotaProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            attachment = (await db.execute(select(models.Attachment).where(models.Attachment.storage_uuid == storage_uuid))).scalar_one()
            upload = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == storage_uuid))).scalar_one()
            cleanup = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.kind == 'drive_image_cleanup'))).scalar_one()
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            assert attachment.storage_status == 'failed' and upload.error_code == 'quota' and upload.encrypted_payload is None
            assert tenant.google_connection_status == 'connected' and len(QuotaProvider.files) == 1
            cleanup_id = cleanup.id
        await run_image_deletion(tenant_id=tenant_id, operation_id=cleanup_id, provider_factory=QuotaProvider)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            attachment = (await db.execute(select(models.Attachment).where(models.Attachment.storage_uuid == storage_uuid))).scalar_one()
            assert attachment.storage_status == 'failed' and attachment.drive_original_id is None
            assert not QuotaProvider.files
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_image_upload_http_is_idempotent_and_does_not_expose_drive_ids(monkeypatch):
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='HTTP image clinic', google_refresh_token='synthetic-refresh', google_connection_status='connected', google_connection_generation=1, google_account_sub='synthetic-sub', google_image_folder_id='synthetic-folder')
            db.add(tenant)
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='httpimg_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=tenant.id, name='Synthetic', age=30, phone='0', medical_history='', notes='')
            db.add_all([user, patient])
            await db.commit()
            tenant_id, username, patient_id = tenant.id, user.username, patient.id
    output = io.BytesIO()
    Image.new('RGB', (10, 10), 'red').save(output, format='PNG')
    token = create_access_token(data={'sub': username, 'tenant_id': tenant_id, 'role': 'admin'})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        headers = {'Authorization': f'Bearer {token}', 'Idempotency-Key': 'http-image-' + suffix}
        file = ('synthetic.png', output.getvalue(), 'image/png')
        first = await client.post('/api/v1/upload', params={'patient_id': patient_id}, files={'file': file}, headers=headers)
        assert first.status_code == 200, first.text
        replay = await client.post('/api/v1/upload', params={'patient_id': patient_id}, files={'file': file}, headers=headers)
        assert replay.status_code == 200 and replay.json()['id'] == first.json()['id']
        assert first.json()['storage_status'] == 'pending'
        assert 'drive_original_id' not in first.json() and 'drive_thumbnail_id' not in first.json()
        assert first.json()['file_path'].startswith('/api/v1/upload/drive/')
