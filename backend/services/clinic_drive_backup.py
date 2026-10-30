"""Durable clinic backup operations backed by the transactional outbox."""
import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.clinic_drive_provider import ClinicDriveProvider, DriveFailure
from backend.services.clinic_google_connection import drive_io, mark_needs_reconnect
from backend.services.event_service import event_service
from backend.services.tenant_archive import ArchiveError, configured_keys, encode_archive
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_import import GATE_NAMESPACE
from backend.services.tenant_backup_config import archive_max_bytes


def _now():
    return datetime.now(timezone.utc)


async def queue_drive_backup(db, *, tenant_id, actor_id, request_key):
    if not isinstance(request_key, str) or not 1 <= len(request_key) <= 128 or request_key.strip() != request_key:
        raise ArchiveError('مفتاح طلب النسخ الاحتياطي غير صالح')
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update())).scalar_one()
    if tenant.google_connection_status != 'connected' or not tenant.google_refresh_token or not tenant.google_backup_folder_id:
        raise DriveFailure('reconnect')
    existing = (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.kind == 'drive_backup',
        models.TenantDataOperation.request_key == request_key,
    ))).scalar_one_or_none()
    if existing:
        return existing
    now = _now()
    operation = models.TenantDataOperation(id=str(uuid.uuid4()), tenant_id=tenant_id, actor_id=actor_id,
        kind='drive_backup', status='queued', request_key=request_key, archive_digest='0' * 64,
        confirmation_digest=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
        connection_generation=tenant.google_connection_generation, created_at=now, updated_at=now,
        expires_at=now + timedelta(days=2))
    db.add(operation)
    event_service.emit_event(db, event_type='tenant.backup.requested', aggregate_type='tenant_data_operation',
                             aggregate_id=operation.id, payload={}, tenant_id=tenant_id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        operation = (await db.execute(select(models.TenantDataOperation).where(
            models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.kind == 'drive_backup',
            models.TenantDataOperation.request_key == request_key,
        ))).scalar_one()
    return operation


async def _load_operation(db, tenant_id, operation_id):
    return (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.id == operation_id,
        models.TenantDataOperation.kind == 'drive_backup',
    ).with_for_update())).scalar_one_or_none()


async def run_drive_backup(*, tenant_id, operation_id, provider_factory=ClinicDriveProvider):
    token = set_current_tenant_id(tenant_id)
    generation = None
    try:
        current_id, keys, installation = configured_keys()
        limit = archive_max_bytes()
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _load_operation(db, tenant_id, operation_id)
            if op is None or op.status in {'completed', 'failed', 'expired'}:
                return
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
            actor = (await db.execute(select(models.User).where(models.User.id == op.actor_id, models.User.tenant_id == tenant_id))).scalar_one_or_none()
            generation = op.connection_generation
            if not actor or actor.role != 'admin' or not actor.is_active or actor.is_deleted:
                raise DriveFailure('permission')
            if tenant.google_connection_status != 'connected' or tenant.google_connection_generation != generation or not tenant.google_refresh_token:
                raise DriveFailure('reconnect')
            refresh_token, folder_id = tenant.google_refresh_token, tenant.google_backup_folder_id
            remote_id, encrypted = op.remote_file_id, op.encrypted_payload
            op.status = 'running'
            op.attempts += 1
            op.updated_at = _now()
            await db.commit()
        provider = await drive_io(provider_factory, refresh_token)
        if not remote_id:
            proposed = (await drive_io(provider.reserve_ids, 1))[0]
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                op = await _load_operation(db, tenant_id, operation_id)
                if not op.remote_file_id:
                    op.remote_file_id = proposed
                remote_id = op.remote_file_id
                await db.commit()
        if encrypted:
            archive = base64.b64decode(encrypted, validate=True)
        else:
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                await db.execute(text('SELECT pg_advisory_xact_lock(:namespace, :tenant)'), {'namespace': GATE_NAMESPACE, 'tenant': tenant_id})
                payload = await export_clinic_archive_data(db, tenant_id)
                revision = (await db.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
                await db.commit()
            archive = encode_archive(payload, tenant_id=tenant_id, installation_id=installation,
                                     schema_revision=revision, key_id=current_id, key=keys[current_id], max_bytes=limit)
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                op = await _load_operation(db, tenant_id, operation_id)
                if op.encrypted_payload:
                    archive = base64.b64decode(op.encrypted_payload, validate=True)
                else:
                    op.encrypted_payload = base64.b64encode(archive).decode('ascii')
                    op.archive_digest = hashlib.sha256(archive).hexdigest()
                await db.commit()
        digest = hashlib.sha256(archive).hexdigest()
        await drive_io(provider.upload_backup, file_id=remote_id, folder_id=folder_id, tenant_id=tenant_id,
                       installation_id=installation, archive=archive, digest=digest)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _load_operation(db, tenant_id, operation_id)
            tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update())).scalar_one()
            if tenant.google_connection_generation != generation or tenant.google_connection_status != 'connected':
                op.status = 'failed'
                op.error_code = 'connection_changed'
            else:
                op.status = 'completed'
                tenant.last_backup_at = _now()
            op.completed_at = _now()
            op.encrypted_payload = None
            await db.commit()
    except Exception as exc:
        category = exc.category if isinstance(exc, DriveFailure) else ('configuration' if isinstance(exc, ArchiveError) else 'transient')
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            op = await _load_operation(db, tenant_id, operation_id)
            if op and op.status not in {'completed', 'failed', 'expired'}:
                if op.status == 'queued':
                    op.attempts += 1
                op.error_code = category
                op.updated_at = _now()
                if category not in {'rate_limit', 'transient'} or op.attempts >= 4:
                    op.status = 'failed'
                    op.completed_at = _now()
                    op.encrypted_payload = None
                await db.commit()
                if category == 'reconnect' and generation is not None:
                    await mark_needs_reconnect(db, tenant_id=tenant_id, generation=generation)
        raise RuntimeError('تعذر تنفيذ النسخ الاحتياطي على Google Drive') from None
    finally:
        clear_tenant_context(tenant_token=token)
