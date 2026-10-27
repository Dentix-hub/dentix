"""Validate a clinic archive and bind a one-use restore confirmation."""
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend import models
from backend.services.tenant_archive import ArchiveError, decode_archive
from backend.services.tenant_archive_identity import resolve_staff_mapping
from backend.services.tenant_archive_legacy import missing_legacy_sections, ensure_missing_sections_empty
from backend.services.tenant_archive_embedded_refs import validate_embedded_references
from backend.services.tenant_archive_registry import (
    validate_archive_references, validate_archive_sections, validate_archive_values,
)


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _now():
    return datetime.now(timezone.utc)


async def create_restore_preview(db, *, tenant_id, actor_id, archive, installation_id, keys, supported_revisions, external_ids=None, max_bytes):
    header, payload = decode_archive(archive, tenant_id=tenant_id, installation_id=installation_id, keys=keys, max_bytes=max_bytes)
    if header.get('schema_revision') not in supported_revisions:
        raise ArchiveError('إصدار قاعدة بيانات النسخة الاحتياطية غير مدعوم')
    missing = missing_legacy_sections(payload)
    data = validate_archive_sections(payload, tenant_id=tenant_id)
    await ensure_missing_sections_empty(db, tenant_id=tenant_id, missing_sections=missing)
    validate_archive_values(data)
    validate_archive_references(data, tenant_id=tenant_id, external_ids=external_ids)
    validate_embedded_references(data, tenant_id=tenant_id, external_ids=external_ids)
    staff_mapping = await resolve_staff_mapping(db, tenant_id, data['staff_references'])
    counts = {name: len(rows) for name, rows in data.items()}
    if header.get('counts') != counts:
        raise ArchiveError('أعداد سجلات النسخة الاحتياطية غير متطابقة')
    # The envelope itself is authenticated ciphertext, never plaintext JSON.
    confirmation = secrets.token_urlsafe(32)
    now = _now()
    operation = models.TenantDataOperation(
        id=str(uuid.uuid4()), tenant_id=tenant_id, actor_id=actor_id,
        kind='restore', status='previewed', archive_digest=_digest(archive),
        confirmation_digest=_digest(confirmation.encode('ascii')),
        encrypted_payload=base64.b64encode(archive).decode('ascii'),
        created_at=now, expires_at=now + timedelta(minutes=10),
    )
    db.add(operation)
    await db.commit()
    return operation, confirmation, header, counts, staff_mapping


async def confirm_restore_preview(db, *, tenant_id, actor_id, operation_id, confirmation, archive_digest):
    operation = (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.id == operation_id,
        models.TenantDataOperation.tenant_id == tenant_id,
        models.TenantDataOperation.actor_id == actor_id,
    ).with_for_update())).scalar_one_or_none()
    if operation is None or operation.kind != 'restore' or operation.status != 'previewed':
        raise ArchiveError('تأكيد الاستعادة غير صالح أو سبق استخدامه')
    expires = operation.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _now():
        raise ArchiveError('انتهت صلاحية تأكيد الاستعادة')
    if not isinstance(confirmation, str) or not hmac.compare_digest(operation.confirmation_digest, _digest(confirmation.encode('utf-8'))):
        raise ArchiveError('تأكيد الاستعادة غير صالح أو سبق استخدامه')
    if not isinstance(archive_digest, str) or not hmac.compare_digest(operation.archive_digest, archive_digest):
        raise ArchiveError('ملف الاستعادة لا يطابق الملف الذي تمت معاينته')
    operation.status = 'confirmed'
    await db.commit()
    return operation


async def expire_restore_previews(db, *, tenant_id):
    """Remove expired encrypted input without exposing its contents."""
    from sqlalchemy import update
    stmt = (update(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == tenant_id,
        models.TenantDataOperation.kind == 'restore',
        models.TenantDataOperation.status.in_(['previewed', 'confirmed']),
        models.TenantDataOperation.expires_at <= _now(),
    ).values(status='expired', encrypted_payload=None, completed_at=_now()))
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount
