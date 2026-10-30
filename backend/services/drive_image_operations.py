"""Durable Drive image upload and deletion operations."""
import base64
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend import models
from backend.core.security import get_encryption_manager
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.clinic_drive_provider import ClinicDriveProvider, DriveFailure
from backend.services.clinic_google_connection import drive_io, mark_needs_reconnect
from backend.services.drive_image_cache import image_cache
from backend.services.drive_image_processing import prepare_image
from backend.services.event_service import event_service


def _now():
    return datetime.now(timezone.utc)


async def stage_image_upload(db, *, tenant, user, patient_id, filename, mime, note, content, request_key):
    if not isinstance(request_key, str) or not 1 <= len(request_key) <= 128 or request_key.strip() != request_key:
        raise ValueError('مفتاح رفع الصورة غير صالح')
    import os
    from cryptography.fernet import Fernet
    configured_key = os.getenv('ENCRYPTION_KEY', '')
    try:
        Fernet(configured_key.encode('ascii'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('إعدادات تشفير الصور غير مكتملة') from exc
    if get_encryption_manager()._key != configured_key:
        raise ValueError('إعدادات تشفير الصور غير مكتملة')
    prepared = await drive_io(prepare_image, content, mime)
    expected_generation = tenant.google_connection_generation
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant.id).with_for_update())).scalar_one()
    await db.refresh(tenant)
    if tenant.google_connection_status != 'connected' or tenant.google_connection_generation != expected_generation or not tenant.google_refresh_token or not tenant.google_image_folder_id or not tenant.google_account_sub:
        raise DriveFailure('reconnect')
    fingerprint = hashlib.sha256(json.dumps({'patient_id': patient_id, 'actor_id': user.id, 'sha256': prepared['sha256'], 'filename': filename, 'note': note}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    existing = (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == tenant.id, models.TenantDataOperation.kind == 'drive_image_upload',
        models.TenantDataOperation.request_key == request_key,
    ))).scalar_one_or_none()
    if existing:
        if existing.confirmation_digest != fingerprint:
            raise ValueError('مفتاح الرفع مستخدم لصورة أخرى')
        return (await db.execute(select(models.Attachment).where(
            models.Attachment.tenant_id == tenant.id, models.Attachment.storage_uuid == existing.id,
        ))).scalar_one()
    storage_uuid = str(uuid.uuid4())
    now = _now()
    encrypted = get_encryption_manager().encrypt(json.dumps({
        'original': base64.b64encode(prepared['original']).decode('ascii'),
        'thumbnail': base64.b64encode(prepared['thumbnail']).decode('ascii'),
    }, separators=(',', ':')))
    attachment = models.Attachment(tenant_id=tenant.id, patient_id=patient_id, filename=filename,
        file_type=mime, note=note, file_path=f'/api/v1/upload/drive/{storage_uuid}/content',
        storage_provider='google_drive', storage_uuid=storage_uuid, storage_status='pending',
        original_size=prepared['size'], original_sha256=prepared['sha256'],
        thumbnail_sha256=prepared['thumbnail_sha256'], google_account_sub=tenant.google_account_sub,
        connection_generation=tenant.google_connection_generation)
    operation = models.TenantDataOperation(id=storage_uuid, tenant_id=tenant.id, actor_id=user.id,
        kind='drive_image_upload', status='queued', request_key=request_key, archive_digest=prepared['sha256'],
        confirmation_digest=fingerprint, encrypted_payload=encrypted, connection_generation=tenant.google_connection_generation,
        created_at=now, updated_at=now, expires_at=now + timedelta(hours=24))
    db.add_all([attachment, operation])
    event_service.emit_event(db, event_type='tenant.image.upload', aggregate_type='tenant_data_operation',
                             aggregate_id=operation.id, payload={}, tenant_id=tenant.id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(select(models.TenantDataOperation).where(
            models.TenantDataOperation.tenant_id == tenant.id, models.TenantDataOperation.kind == 'drive_image_upload',
            models.TenantDataOperation.request_key == request_key,
        ))).scalar_one()
        if existing.confirmation_digest != fingerprint:
            raise ValueError('مفتاح الرفع مستخدم لصورة أخرى')
        attachment = (await db.execute(select(models.Attachment).where(
            models.Attachment.tenant_id == tenant.id, models.Attachment.storage_uuid == existing.id,
        ))).scalar_one()
    await db.refresh(attachment)
    return attachment


async def queue_image_delete(db, *, attachment, user):
    if attachment.storage_status == 'deleting':
        return
    attachment.storage_status = 'deleting'
    now = _now()
    operation = models.TenantDataOperation(id=str(uuid.uuid4()), tenant_id=attachment.tenant_id, actor_id=user.id,
        kind='drive_image_delete', status='queued', request_key=attachment.storage_uuid,
        archive_digest=attachment.original_sha256 or '0' * 64,
        confirmation_digest=hashlib.sha256(attachment.storage_uuid.encode()).hexdigest(),
        connection_generation=attachment.connection_generation, created_at=now, updated_at=now,
        expires_at=now + timedelta(days=30))
    db.add(operation)
    event = event_service.emit_event(db, event_type='tenant.image.delete', aggregate_type='tenant_data_operation',
                                     aggregate_id=operation.id, payload={}, tenant_id=attachment.tenant_id)
    event.max_attempts = 10
    await db.commit()
    image_cache.invalidate(tenant_id=attachment.tenant_id, storage_uuid=attachment.storage_uuid)


async def _get_operation(db, tenant_id, operation_id):
    return (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.id == operation_id,
    ).with_for_update())).scalar_one_or_none()


async def _schedule_failed_upload_cleanup(db, *, attachment, actor_id):
    if not attachment.drive_original_id and not attachment.drive_thumbnail_id:
        return
    existing = (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == attachment.tenant_id,
        models.TenantDataOperation.kind == 'drive_image_cleanup',
        models.TenantDataOperation.request_key == attachment.storage_uuid,
    ))).scalar_one_or_none()
    if existing:
        return
    now = _now()
    cleanup = models.TenantDataOperation(id=str(uuid.uuid4()), tenant_id=attachment.tenant_id, actor_id=actor_id,
        kind='drive_image_cleanup', status='queued', request_key=attachment.storage_uuid,
        archive_digest=attachment.original_sha256, confirmation_digest=hashlib.sha256(attachment.storage_uuid.encode()).hexdigest(),
        connection_generation=attachment.connection_generation, created_at=now, updated_at=now,
        expires_at=now + timedelta(days=30))
    db.add(cleanup)
    event = event_service.emit_event(db, event_type='tenant.image.cleanup', aggregate_type='tenant_data_operation',
                                     aggregate_id=cleanup.id, payload={}, tenant_id=attachment.tenant_id)
    event.max_attempts = 10


async def run_image_upload(*, tenant_id, operation_id, provider_factory=ClinicDriveProvider):
    import os
    from backend.core.permissions import Permission, has_permission
    from backend.services.file_service import MAX_FILE_SIZE_BYTES
    from backend.services.visibility_service import get_visibility_service
    token = set_current_tenant_id(tenant_id)
    generation = None
    try:
        installation = os.getenv('DENTIX_INSTALLATION_ID', '').strip()
        if not installation:
            raise DriveFailure('permission')
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _get_operation(db, tenant_id, operation_id)
            if op is None or op.status in {'completed', 'failed', 'expired'}:
                return
            expires = op.expires_at.replace(tzinfo=timezone.utc) if op.expires_at.tzinfo is None else op.expires_at
            if expires <= _now():
                raise DriveFailure('permission')
            attachment = (await db.execute(select(models.Attachment).where(
                models.Attachment.tenant_id == tenant_id, models.Attachment.storage_uuid == operation_id,
            ).with_for_update())).scalar_one_or_none()
            if not attachment or attachment.storage_status == 'deleting':
                op.status = 'failed'
                op.error_code = 'cancelled'
                op.encrypted_payload = None
                await db.commit()
                return
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            actor = (await db.execute(select(models.User).where(models.User.tenant_id == tenant_id, models.User.id == op.actor_id))).scalar_one_or_none()
            if not actor or not actor.is_active or actor.is_deleted or not has_permission(actor.role, Permission.PATIENT_UPDATE):
                raise DriveFailure('permission')
            if not await get_visibility_service(db, actor, tenant_id).can_view_patient(attachment.patient_id):
                raise DriveFailure('permission')
            generation = op.connection_generation
            if tenant.google_connection_status != 'connected' or tenant.google_connection_generation != generation or tenant.google_account_sub != attachment.google_account_sub or not tenant.google_refresh_token or not tenant.google_image_folder_id:
                raise DriveFailure('reconnect')
            refresh, folder, patient_id = tenant.google_refresh_token, tenant.google_image_folder_id, attachment.patient_id
            ids = (attachment.drive_original_id, attachment.drive_thumbnail_id)
            original_digest, thumbnail_digest, mime = attachment.original_sha256, attachment.thumbnail_sha256, attachment.file_type
            encrypted = op.encrypted_payload
            op.status = 'running'
            op.attempts += 1
            op.updated_at = _now()
            await db.commit()
        payload = json.loads(get_encryption_manager().decrypt(encrypted, allow_plaintext_fallback=False))
        original = base64.b64decode(payload['original'], validate=True)
        thumbnail = base64.b64decode(payload['thumbnail'], validate=True)
        if len(original) > MAX_FILE_SIZE_BYTES or len(thumbnail) > 8 * 1024 * 1024 or hashlib.sha256(original).hexdigest() != original_digest or hashlib.sha256(thumbnail).hexdigest() != thumbnail_digest:
            raise DriveFailure('permission')
        provider = await drive_io(provider_factory, refresh)
        if not all(ids):
            proposed = await drive_io(provider.reserve_ids, 2)
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                attachment = (await db.execute(select(models.Attachment).where(
                    models.Attachment.tenant_id == tenant_id, models.Attachment.storage_uuid == operation_id,
                ).with_for_update())).scalar_one()
                if not attachment.drive_original_id and not attachment.drive_thumbnail_id:
                    attachment.drive_original_id, attachment.drive_thumbnail_id = proposed
                ids = (attachment.drive_original_id, attachment.drive_thumbnail_id)
                await db.commit()
        common = {'folder_id': folder, 'tenant_id': tenant_id, 'installation_id': installation,
                  'storage_uuid': operation_id, 'patient_id': patient_id}
        await drive_io(provider.upload_image, file_id=ids[0], variant='original', content=original, mime=mime, digest=original_digest, **common)
        await drive_io(provider.upload_image, file_id=ids[1], variant='thumbnail', content=thumbnail, mime='image/jpeg', digest=thumbnail_digest, **common)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _get_operation(db, tenant_id, operation_id)
            attachment = (await db.execute(select(models.Attachment).where(
                models.Attachment.tenant_id == tenant_id, models.Attachment.storage_uuid == operation_id,
            ).with_for_update())).scalar_one_or_none()
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            if not attachment or attachment.storage_status != 'pending':
                op.status = 'failed'
                op.error_code = 'cancelled'
                op.encrypted_payload = None
                op.completed_at = _now()
                await db.commit()
                return
            if tenant.google_connection_generation != generation or tenant.google_connection_status != 'connected':
                raise DriveFailure('reconnect')
            attachment.storage_status = 'ready'
            op.status = 'completed'
            op.encrypted_payload = None
            op.completed_at = _now()
            await db.commit()
    except Exception as exc:
        category = exc.category if isinstance(exc, DriveFailure) else 'transient'
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _get_operation(db, tenant_id, operation_id)
            if op and op.status not in {'completed', 'failed', 'expired'}:
                if op.status == 'queued':
                    op.attempts += 1
                op.error_code = category
                op.updated_at = _now()
                attachment = (await db.execute(select(models.Attachment).where(
                    models.Attachment.tenant_id == tenant_id, models.Attachment.storage_uuid == operation_id,
                ).with_for_update())).scalar_one_or_none()
                if category not in {'rate_limit', 'transient'} or op.attempts >= 4:
                    op.status = 'failed'
                    op.completed_at = _now()
                    op.encrypted_payload = None
                    if attachment and attachment.storage_status != 'deleting':
                        attachment.storage_status = 'failed'
                        await _schedule_failed_upload_cleanup(db, attachment=attachment, actor_id=op.actor_id)
                await db.commit()
                if category == 'reconnect' and generation is not None:
                    await mark_needs_reconnect(db, tenant_id=tenant_id, generation=generation)
        raise RuntimeError('تعذر رفع صورة المريض إلى Google Drive') from None
    finally:
        clear_tenant_context(tenant_token=token)


async def run_image_deletion(*, tenant_id, operation_id, provider_factory=ClinicDriveProvider):
    """Retain DB ownership until both remote files are deleted or absent."""
    import os
    token = set_current_tenant_id(tenant_id)
    generation = None
    try:
        installation = os.getenv('DENTIX_INSTALLATION_ID', '').strip()
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _get_operation(db, tenant_id, operation_id)
            if op is None or op.status == 'completed':
                return
            if op.kind not in {'drive_image_delete', 'drive_image_cleanup'}:
                raise DriveFailure('permission')
            attachment = (await db.execute(select(models.Attachment).where(
                models.Attachment.tenant_id == tenant_id, models.Attachment.storage_uuid == op.request_key,
            ).with_for_update())).scalar_one_or_none()
            if not attachment:
                op.status = 'completed'
                op.completed_at = _now()
                await db.commit()
                return
            upload = (await db.execute(select(models.TenantDataOperation).where(
                models.TenantDataOperation.tenant_id == tenant_id,
                models.TenantDataOperation.id == attachment.storage_uuid,
                models.TenantDataOperation.kind == 'drive_image_upload',
            ))).scalar_one_or_none()
            if upload and upload.status in {'queued', 'running'}:
                raise DriveFailure('transient')
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            generation = tenant.google_connection_generation
            if not installation or tenant.google_connection_status != 'connected' or tenant.google_account_sub != attachment.google_account_sub or not tenant.google_refresh_token or not tenant.google_image_folder_id:
                raise DriveFailure('reconnect')
            refresh, folder, storage = tenant.google_refresh_token, tenant.google_image_folder_id, attachment.storage_uuid
            originals = ((attachment.drive_original_id, 'original', attachment.original_sha256),
                         (attachment.drive_thumbnail_id, 'thumbnail', attachment.thumbnail_sha256))
            op.status = 'running'
            op.attempts += 1
            op.updated_at = _now()
            await db.commit()
        provider = await drive_io(provider_factory, refresh)
        for file_id, variant, digest in originals:
            if file_id:
                await drive_io(provider.delete_image, file_id=file_id, folder_id=folder, tenant_id=tenant_id,
                               installation_id=installation, storage_uuid=storage, variant=variant, digest=digest)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _get_operation(db, tenant_id, operation_id)
            attachment = (await db.execute(select(models.Attachment).where(
                models.Attachment.tenant_id == tenant_id, models.Attachment.storage_uuid == storage,
            ).with_for_update())).scalar_one_or_none()
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            if tenant.google_connection_generation != generation or tenant.google_connection_status != 'connected':
                raise DriveFailure('reconnect')
            if attachment:
                if op.kind == 'drive_image_delete' and attachment.storage_status == 'deleting':
                    await db.delete(attachment)
                elif op.kind == 'drive_image_cleanup' and attachment.storage_status == 'failed':
                    attachment.drive_original_id = None
                    attachment.drive_thumbnail_id = None
            op.status = 'completed'
            op.completed_at = _now()
            await db.commit()
        image_cache.invalidate(tenant_id=tenant_id, storage_uuid=storage)
    except Exception as exc:
        category = exc.category if isinstance(exc, DriveFailure) else 'transient'
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _get_operation(db, tenant_id, operation_id)
            if op and op.status != 'completed':
                op.error_code = category
                op.updated_at = _now()
                await db.commit()
                if category == 'reconnect' and generation is not None:
                    await mark_needs_reconnect(db, tenant_id=tenant_id, generation=generation)
        raise RuntimeError('تعذر حذف صورة المريض من Google Drive') from None
    finally:
        clear_tenant_context(tenant_token=token)
