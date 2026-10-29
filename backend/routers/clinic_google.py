"""Per-clinic Google connection endpoints."""
import logging
import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext, get_async_db
from backend.services.clinic_drive_provider import ClinicDriveProvider
from backend.services.clinic_google_attempts import consume_google_attempt, resolve_attempt_tenant, start_google_attempt
from backend.services.clinic_google_connection import drive_io, finish_google_connection
from backend.services.clinic_google_oauth import GoogleConnectionError, exchange_and_verify

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/settings/drive', tags=['Clinic Google connection'])
BROWSER_COOKIE = 'dentix_google_browser'


def _admin(user):
    if user.role != 'admin' or not user.tenant_id or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=403, detail='ربط Google متاح لمدير العيادة فقط')
    return user.tenant_id


def _frontend():
    url = os.getenv('FRONTEND_URL', '').rstrip('/')
    parsed = urlparse(url)
    if not parsed.hostname or parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise GoogleConnectionError('إعدادات واجهة التطبيق غير مكتملة')
    if os.getenv('ENVIRONMENT', '').lower() == 'production' and parsed.scheme != 'https':
        raise GoogleConnectionError('إعدادات واجهة التطبيق غير مكتملة')
    return url


@router.get('/auth')
async def start_connection(request: Request, response: Response, db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    _admin(user)
    try:
        url, browser = await start_google_attempt(db, user=user, browser_secret=request.cookies.get(BROWSER_COOKIE))
    except GoogleConnectionError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response.set_cookie(BROWSER_COOKIE, browser, httponly=True, secure=os.getenv('ENVIRONMENT', '').lower() == 'production',
                        samesite='lax', max_age=600, path='/api/v1/settings')
    response.headers['Cache-Control'] = 'private, no-store'
    return success_response(data={'url': url})


@router.get('/callback')
async def connection_callback(request: Request, code: str = '', state: str = ''):
    try:
        frontend = _frontend()
    except GoogleConnectionError:
        raise HTTPException(status_code=503, detail='إعدادات ربط Google غير مكتملة') from None
    destination = f'{frontend}/settings?backup_status=error'
    try:
        if not state or not code or len(state) > 128 or len(code) > 4096:
            raise GoogleConnectionError('طلب الربط غير صالح')
        resolved = await resolve_attempt_tenant(state)
        if not resolved:
            raise GoogleConnectionError('طلب الربط غير صالح')
        attempt_id, tenant_id = resolved
        token = set_current_tenant_id(tenant_id)
        try:
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                details = await consume_google_attempt(db, tenant_id=tenant_id, attempt_id=attempt_id,
                                                       state=state, browser_secret=request.cookies.get(BROWSER_COOKIE))
        finally:
            clear_tenant_context(tenant_token=token)
        identity = await drive_io(exchange_and_verify, code=code, verifier=details['verifier'], nonce_digest=details['nonce_digest'])
        provider = await drive_io(ClinicDriveProvider, identity['refresh_token'])
        await finish_google_connection(details=details, identity=identity, provider=provider)
        destination = f'{frontend}/settings?backup_status=success'
    except Exception:
        # OAuth/provider exceptions may contain codes, URLs or tokens. Never log them.
        logger.warning('Clinic Google connection failed')
    return RedirectResponse(url=destination, status_code=303, headers={'Cache-Control': 'private, no-store'})


@router.get('/status')
async def connection_status(db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    tenant_id = _admin(user)
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
    return success_response(data={'status': tenant.google_connection_status, 'email': tenant.google_account_email})


@router.delete('/connection')
async def disconnect_connection(db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    tenant_id = _admin(user)
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update())).scalar_one()
    tenant.google_refresh_token = None
    tenant.google_connection_status = 'disconnected'
    tenant.google_connection_generation += 1
    await db.commit()
    from backend.services.drive_image_cache import image_cache
    image_cache.invalidate(tenant_id=tenant_id)
    return success_response(message='تم فصل العيادة عن Google Drive. تظل الملفات في حساب Google.')


async def _connected_credentials(db, tenant_id):
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
    if tenant.google_connection_status != 'connected' or not tenant.google_refresh_token or not tenant.google_backup_folder_id:
        from backend.services.clinic_drive_provider import DriveFailure
        raise DriveFailure('reconnect')
    result = (tenant.google_refresh_token, tenant.google_backup_folder_id, tenant.google_connection_generation)
    await db.commit()  # Never hold a connection during provider I/O.
    return result


async def _assert_connection_generation(db, tenant_id, generation):
    row = (await db.execute(select(models.Tenant.google_connection_generation, models.Tenant.google_connection_status).where(
        models.Tenant.id == tenant_id,
    ))).one_or_none()
    if not row or row.google_connection_generation != generation or row.google_connection_status != 'connected':
        from backend.services.clinic_drive_provider import DriveFailure
        raise DriveFailure('reconnect')


async def _drive_error(db, tenant_id, generation, exc):
    from backend.services.clinic_drive_provider import DriveFailure
    from backend.services.clinic_google_connection import mark_needs_reconnect
    if isinstance(exc, DriveFailure) and exc.category == 'reconnect' and generation is not None:
        await mark_needs_reconnect(db, tenant_id=tenant_id, generation=generation)
    raise HTTPException(status_code=400, detail=str(exc) if isinstance(exc, DriveFailure) else 'تعذر الاتصال بـ Google Drive') from None


@router.get('/backups')
async def list_clinic_backups(page_token: str | None = None, db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    from backend.services.clinic_drive_provider import DriveFailure
    from backend.services.tenant_archive import configured_keys
    tenant_id = _admin(user)
    generation = None
    try:
        refresh, folder, generation = await _connected_credentials(db, tenant_id)
        _, _, installation = configured_keys()
        provider = await drive_io(ClinicDriveProvider, refresh)
        files, next_page = await drive_io(provider.list_backups, folder_id=folder, tenant_id=tenant_id, installation_id=installation, page_token=page_token)
        await _assert_connection_generation(db, tenant_id, generation)
        return success_response(data={'files': [{'id': item['id'], 'name': item.get('name'), 'date': item.get('modifiedTime'), 'size': item.get('size')} for item in files], 'next_page_token': next_page})
    except DriveFailure as exc:
        await _drive_error(db, tenant_id, generation, exc)
    except Exception:
        raise HTTPException(status_code=400, detail='تعذر عرض نسخ Google Drive') from None


@router.post('/backups/{file_id}/preview')
async def preview_drive_backup(file_id: str, db: AsyncSession = Depends(get_async_db), user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    from sqlalchemy import text
    from backend.services.clinic_drive_provider import DriveFailure
    from backend.services.tenant_archive import ArchiveError, configured_keys, decode_archive
    from backend.services.tenant_backup_config import archive_max_bytes, supported_archive_revisions
    from backend.services.tenant_restore_coordinator import known_global_references
    from backend.services.tenant_restore_preview import create_restore_preview
    tenant_id = _admin(user)
    generation = None
    try:
        refresh, folder, generation = await _connected_credentials(db, tenant_id)
        _, keys, installation = configured_keys()
        limit = archive_max_bytes()
        provider = await drive_io(ClinicDriveProvider, refresh)
        archive = await drive_io(provider.download_backup, file_id=file_id, folder_id=folder, tenant_id=tenant_id, installation_id=installation, max_bytes=limit)
        await _assert_connection_generation(db, tenant_id, generation)
        revision = (await db.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
        external_ids = await known_global_references(db)
        operation, confirmation, header, counts, mapping = await create_restore_preview(
            db, tenant_id=tenant_id, actor_id=user.id, archive=archive, installation_id=installation,
            keys=keys, supported_revisions=supported_archive_revisions(revision), external_ids=external_ids, max_bytes=limit,
        )
        _, decoded = decode_archive(archive, tenant_id=tenant_id, installation_id=installation, keys=keys, max_bytes=limit)
        from backend.services.tenant_archive_adapters import adapt_archive_version
        from backend.services.tenant_archive_availability import attachment_availability
        decoded = adapt_archive_version(decoded, header.get('schema_revision'))
        availability = await attachment_availability(db, tenant_id=tenant_id, rows=decoded['data']['attachments'])
        return success_response(data={'operation_id': operation.id, 'confirmation': confirmation,
                                      'archive_digest': operation.archive_digest, 'backup_date': header['created_at'],
                                      'schema_revision': header['schema_revision'], 'counts': counts,
                                      'staff_mapping': [{'name': row.get('full_name') or row.get('username'), 'existing_user_id': mapping[row['id']]} for row in decoded['data']['staff_references']],
                                      'legacy_unverified': bool(decoded.get('legacy_unverified')), 'missing_sections': decoded.get('missing_sections', []),
                                      'attachment_availability': availability, 'expires_at': operation.expires_at.isoformat()})
    except DriveFailure as exc:
        await _drive_error(db, tenant_id, generation, exc)
    except ArchiveError as exc:
        await db.rollback()
        logger.warning(
            'Drive backup restore preview rejected for tenant %s: category=%s section=%s field=%s counts=%s',
            tenant_id, getattr(exc, 'category', None), getattr(exc, 'section', None),
            getattr(exc, 'field', None), getattr(exc, 'counts', None),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail='تعذرت معاينة نسخة Google Drive') from None
