"""Tenant-scoped, browser-bound OAuth state with a narrow audited bootstrap."""
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend import models
from backend.core.permissions import Permission, has_permission
from backend.services.clinic_google_oauth import GoogleConnectionError, authorization_url, digest


def _active_admin(user, tenant):
    return bool(user and tenant and user.role == 'admin' and user.tenant_id == tenant.id
                and user.is_active and not user.is_deleted and tenant.is_active and not tenant.is_deleted
                and has_permission(user.role, Permission.SYSTEM_CONFIG))


async def start_google_attempt(db, *, user, browser_secret=None):
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == user.tenant_id).with_for_update())).scalar_one_or_none()
    if not _active_admin(user, tenant):
        raise GoogleConnectionError('ربط Google متاح لمدير العيادة فقط')
    if not isinstance(browser_secret, str) or not re.fullmatch(r'[A-Za-z0-9_-]{40,100}', browser_secret):
        browser_secret = secrets.token_urlsafe(32)
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    url = authorization_url(state=state, nonce=nonce, verifier=verifier)
    now = datetime.now(timezone.utc)
    attempt = models.GoogleOAuthAttempt(
        id=str(uuid.uuid4()), tenant_id=tenant.id, user_id=user.id,
        state_digest=digest(state), browser_digest=digest(browser_secret), nonce_digest=digest(nonce),
        verifier=verifier, connection_generation=tenant.google_connection_generation,
        created_at=now, expires_at=now + timedelta(minutes=10),
    )
    db.add(attempt)
    await db.commit()
    return url, browser_secret


async def resolve_attempt_tenant(state):
    """Look up only an opaque state digest under the audited system role."""
    from backend.database import system_session_scope
    from backend.services.auth_bootstrap import _audit_bootstrap
    from backend.core.tenancy import set_current_tenant_id, set_super_admin_bypass, clear_tenant_context
    tenant_token = set_current_tenant_id(None)
    bypass_token = set_super_admin_bypass(False)
    try:
        async with system_session_scope() as db:
            result = (await db.execute(select(models.GoogleOAuthAttempt.id, models.GoogleOAuthAttempt.tenant_id, models.GoogleOAuthAttempt.user_id).where(
                models.GoogleOAuthAttempt.state_digest == digest(state),
            ))).one_or_none()
    finally:
        clear_tenant_context(tenant_token=tenant_token, admin_token=bypass_token)
    await _audit_bootstrap(user_id=result.user_id if result else None, tenant_id=result.tenant_id if result else None,
                           username='[google-oauth-redacted]', reason='google_oauth_state')
    return (result.id, result.tenant_id) if result else None


async def consume_google_attempt(db, *, tenant_id, attempt_id, state, browser_secret):
    attempt = (await db.execute(select(models.GoogleOAuthAttempt).where(
        models.GoogleOAuthAttempt.id == attempt_id, models.GoogleOAuthAttempt.tenant_id == tenant_id,
        models.GoogleOAuthAttempt.state_digest == digest(state),
    ).with_for_update())).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    expires = attempt.expires_at if attempt else None
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not attempt or attempt.consumed_at is not None or not expires or expires <= now or not browser_secret or not hmac.compare_digest(attempt.browser_digest, digest(browser_secret)):
        raise GoogleConnectionError('انتهت صلاحية طلب ربط Google أو أنه غير صالح')
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update())).scalar_one_or_none()
    user = (await db.execute(select(models.User).where(models.User.id == attempt.user_id, models.User.tenant_id == tenant_id))).scalar_one_or_none()
    if not _active_admin(user, tenant) or tenant.google_connection_generation != attempt.connection_generation:
        raise GoogleConnectionError('تغير حساب أو صلاحيات مدير العيادة أثناء الربط')
    details = {'attempt_id': attempt.id, 'user_id': user.id, 'tenant_id': tenant_id, 'generation': attempt.connection_generation,
               'verifier': attempt.verifier, 'nonce_digest': attempt.nonce_digest}
    attempt.consumed_at = now
    attempt.verifier = ''  # erase the verifier after the single-use claim
    await db.commit()
    return details
