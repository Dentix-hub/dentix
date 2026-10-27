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
    return success_response(message='تم فصل العيادة عن Google Drive. تظل الملفات في حساب Google.')
