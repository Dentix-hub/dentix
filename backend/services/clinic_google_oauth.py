"""Per-attempt Google OAuth flow and verified identity for clinic connections."""
import hashlib
import json
import os
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from backend.google_drive_client import get_client_config
from backend.core.config import API_V1_STR

DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.file'
EMAIL_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
SCOPES = [DRIVE_SCOPE, 'openid', 'email']


class GoogleConnectionError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def oauth_config():
    try:
        Fernet(os.environ['ENCRYPTION_KEY'].encode('ascii'))
    except (KeyError, ValueError, UnicodeError) as exc:
        raise GoogleConnectionError('إعدادات ربط Google غير مكتملة') from exc
    redirect = os.getenv('GOOGLE_REDIRECT_URI', '').strip()
    parts = urlparse(redirect)
    allow_local = os.getenv('ENVIRONMENT', '').lower() != 'production' and parts.hostname in {'localhost', '127.0.0.1'}
    if not redirect or not parts.hostname or (parts.scheme != 'https' and not (allow_local and parts.scheme == 'http')) or parts.fragment or parts.query or parts.username or parts.password or parts.path not in {f'{API_V1_STR}/settings/backup/callback', f'{API_V1_STR}/settings/drive/callback'}:
        raise GoogleConnectionError('إعدادات ربط Google غير مكتملة')
    config = get_client_config()
    if not config['web'].get('client_id') or not config['web'].get('client_secret'):
        raise GoogleConnectionError('إعدادات ربط Google غير مكتملة')
    try:
        timeout = int(os.getenv('GOOGLE_API_TIMEOUT', '60'))
    except ValueError as exc:
        raise GoogleConnectionError('إعدادات ربط Google غير صالحة') from exc
    if not 1 <= timeout <= 120:
        raise GoogleConnectionError('إعدادات ربط Google غير صالحة')
    config['web']['redirect_uris'] = [redirect]
    return config, redirect, timeout


def _normalize_access_token_response(response):
    try:
        data = response.json()
    except Exception:
        return response
    scope_val = data.get('scope')
    if isinstance(scope_val, str):
        parts = scope_val.split()
        normalized = ['email' if p == EMAIL_SCOPE else p for p in parts]
        data['scope'] = ' '.join(normalized)
        response._content = json.dumps(data).encode(response.encoding or 'utf-8')
    elif isinstance(scope_val, (list, tuple)):
        normalized = ['email' if p == EMAIL_SCOPE else p for p in scope_val]
        data['scope'] = normalized
        response._content = json.dumps(data).encode(response.encoding or 'utf-8')
    return response


def normalize_scopes(raw_scope) -> set[str]:
    if raw_scope is None:
        raise GoogleConnectionError('صلاحيات Google المستلمة غير صالحة')
    if isinstance(raw_scope, str):
        items = raw_scope.split()
    elif isinstance(raw_scope, (list, tuple, set)):
        items = []
        for item in raw_scope:
            if not isinstance(item, str):
                raise GoogleConnectionError('صلاحيات Google المستلمة غير صالحة')
            items.append(item.strip())
    else:
        raise GoogleConnectionError('صلاحيات Google المستلمة غير صالحة')

    normalized = set()
    for s in items:
        if not s:
            continue
        if s == EMAIL_SCOPE:
            normalized.add('email')
        else:
            normalized.add(s)
    return normalized


def _flow(verifier):
    config, redirect, _ = oauth_config()
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=redirect,
                                   code_verifier=verifier, autogenerate_code_verifier=False)
    flow.oauth2session.register_compliance_hook('access_token_response', _normalize_access_token_response)
    return flow


def authorization_url(*, state, nonce, verifier):
    flow = _flow(verifier)
    url, returned_state = flow.authorization_url(state=state, nonce=nonce, access_type='offline', prompt='consent select_account', include_granted_scopes='false')
    if returned_state != state:
        raise GoogleConnectionError('تعذر بدء ربط Google')
    return url


def exchange_and_verify(*, code, verifier, nonce_digest):
    config, _, timeout = oauth_config()
    flow = _flow(verifier)
    token = flow.fetch_token(code=code, timeout=timeout)
    granted = normalize_scopes(token.get('scope'))
    if granted != set(SCOPES):
        raise GoogleConnectionError('لم تُمنح صلاحيات Google المطلوبة فقط')
    credentials = flow.credentials
    if not credentials.refresh_token or not token.get('id_token'):
        raise GoogleConnectionError('لم يتم استلام صلاحية اتصال مستمرة')
    transport = Request()
    def bounded_request(*args, **kwargs):
        kwargs['timeout'] = timeout
        return transport(*args, **kwargs)
    claims = id_token.verify_oauth2_token(token['id_token'], bounded_request, audience=config['web']['client_id'])
    if claims.get('iss') not in {'accounts.google.com', 'https://accounts.google.com'} or not claims.get('sub') or digest(str(claims.get('nonce', ''))) != nonce_digest:
        raise GoogleConnectionError('تعذر التحقق من حساب Google')
    return {'sub': claims['sub'], 'email': claims.get('email'), 'refresh_token': credentials.refresh_token}
