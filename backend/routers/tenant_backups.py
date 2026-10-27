"""Authenticated clinic archive, restore preview and durable operation APIs."""
import json
import logging

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.auth import verify_password
from backend.core.limiter import limiter
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response
from backend.database import get_async_db
from backend.services.tenant_archive import ArchiveError, configured_keys, encode_archive
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_import import GATE_NAMESPACE
from backend.services.tenant_archive_legacy import adapt_legacy_json
from backend.services.tenant_backup_config import archive_max_bytes, supported_archive_revisions
from backend.services.tenant_restore_coordinator import known_global_references
from backend.services.tenant_restore_preview import confirm_restore_preview, create_restore_preview
from backend.utils.audit_logger import log_admin_action

router = APIRouter(prefix='/settings/backup', tags=['Clinic backup'])
logger = logging.getLogger(__name__)


def _clinic_admin(user):
    if user.role != 'admin' or not user.tenant_id or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=403, detail='هذه العملية متاحة لمدير العيادة فقط')
    return user.tenant_id


def _archive_config():
    try:
        current_id, keys, installation = configured_keys()
        return current_id, keys, installation, archive_max_bytes()
    except ArchiveError as exc:
        raise HTTPException(status_code=503, detail='إعدادات النسخ الاحتياطي غير مكتملة') from exc


async def _revision(db):
    return (await db.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()


class ConfirmRestore(BaseModel):
    operation_id: str = Field(min_length=1, max_length=36)
    confirmation: str = Field(min_length=1, max_length=100)
    archive_digest: str = Field(min_length=64, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    otp_code: str | None = Field(default=None, max_length=16)


@router.get('/archive')
async def download_clinic_archive(db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    tenant_id = _clinic_admin(user)
    key_id, keys, installation, limit = _archive_config()
    try:
        if db.bind.dialect.name == 'postgresql':
            await db.execute(text('SELECT pg_advisory_xact_lock(:namespace, :tenant)'),
                             {'namespace': GATE_NAMESPACE, 'tenant': tenant_id})
        payload = await export_clinic_archive_data(db, tenant_id)
        revision = await _revision(db)
        await db.commit()  # Release the database gate before encryption or download.
        archive = encode_archive(payload, tenant_id=tenant_id, installation_id=installation,
                                 schema_revision=revision, key_id=key_id, key=keys[key_id], max_bytes=limit)
    except ArchiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=archive, media_type='application/octet-stream', headers={
        'Content-Disposition': 'attachment; filename="dentix-clinic-backup.dentix"', 'Cache-Control': 'private, no-store',
    })


@router.post('/preview')
@limiter.limit('5/minute')
async def preview_clinic_restore(request: Request, db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    tenant_id = _clinic_admin(user)
    key_id, keys, installation, limit = _archive_config()
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > limit:
            raise HTTPException(status_code=413, detail='حجم النسخة الاحتياطية أكبر من الحد المسموح')
        raw.extend(chunk)
    raw = bytes(raw)
    revision = await _revision(db)
    try:
        if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() == 'application/json':
            try:
                source = json.loads(raw.decode('utf-8'))
            except (ValueError, UnicodeError) as exc:
                raise ArchiveError('ملف النسخة الاحتياطية القديم غير صالح') from exc
            payload = adapt_legacy_json(source, tenant_id=tenant_id)
            raw = encode_archive(payload, tenant_id=tenant_id, installation_id=installation,
                                 schema_revision=revision, key_id=key_id, key=keys[key_id], max_bytes=limit)
        external_ids = await known_global_references(db)
        operation, confirmation, header, counts, mapping = await create_restore_preview(
            db, tenant_id=tenant_id, actor_id=user.id, archive=raw, installation_id=installation,
            keys=keys, supported_revisions=supported_archive_revisions(revision), external_ids=external_ids, max_bytes=limit,
        )
        # Metadata from the original payload is authenticated inside the file.
        from backend.services.tenant_archive import decode_archive
        _, decoded = decode_archive(raw, tenant_id=tenant_id, installation_id=installation, keys=keys, max_bytes=limit)
        return success_response(data={
            'operation_id': operation.id, 'confirmation': confirmation, 'archive_digest': operation.archive_digest,
            'backup_date': header['created_at'], 'schema_revision': header['schema_revision'], 'counts': counts,
            'legacy_unverified': bool(decoded.get('legacy_unverified')), 'missing_sections': decoded.get('missing_sections', []),
            'staff_mapping': [{'name': row.get('full_name') or row.get('username'), 'existing_user_id': mapping[row['id']]} for row in decoded['data']['staff_references']],
            'expires_at': operation.expires_at.isoformat(),
        })
    except ArchiveError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        await db.rollback()
        logger.error('Clinic restore preview failed for tenant %s', tenant_id)
        raise HTTPException(status_code=400, detail='تعذرت معاينة النسخة الاحتياطية. لم يتم تغيير بياناتك.') from None


@router.post('/confirm')
@limiter.limit('5/minute')
async def confirm_clinic_restore(request: Request, payload: ConfirmRestore, db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    tenant_id = _clinic_admin(user)
    if not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=403, detail='تعذر التحقق من الهوية')
    if user.is_2fa_enabled and (not user.otp_secret or not payload.otp_code or not pyotp.TOTP(user.otp_secret).verify(payload.otp_code)):
        raise HTTPException(status_code=403, detail='تعذر التحقق من الهوية')
    try:
        log_admin_action(db, user, action='restore_confirmed', entity_type='tenant_backup', tenant_id=tenant_id)
        operation = await confirm_restore_preview(db, tenant_id=tenant_id, actor_id=user.id,
                                                  operation_id=payload.operation_id, confirmation=payload.confirmation,
                                                  archive_digest=payload.archive_digest)
        return success_response(data={'operation_id': operation.id, 'status': operation.status})
    except ArchiveError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/operations/{operation_id}')
async def clinic_restore_status(operation_id: str, db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    tenant_id = _clinic_admin(user)
    operation = (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == tenant_id, models.TenantDataOperation.id == operation_id,
        models.TenantDataOperation.actor_id == user.id,
    ))).scalar_one_or_none()
    if operation is None:
        raise HTTPException(status_code=404, detail='عملية الاستعادة غير موجودة')
    return success_response(data={'operation_id': operation.id, 'status': operation.status,
                                  'completed_at': operation.completed_at.isoformat() if operation.completed_at else None})
