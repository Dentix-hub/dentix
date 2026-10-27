"""Clinic-only Google Drive adapter with bounded I/O and safe errors."""
import hashlib
import json
import random
import time

import google_auth_httplib2
import httplib2
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.services.clinic_google_oauth import DRIVE_SCOPE, oauth_config


class DriveFailure(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__({
            'reconnect': 'يرجى إعادة ربط Google Drive',
            'quota': 'مساحة Google Drive غير كافية',
            'rate_limit': 'طلبات Google Drive كثيرة، يرجى المحاولة لاحقًا',
            'transient': 'Google Drive غير متاح مؤقتًا',
            'permission': 'تعذر الوصول إلى ملف Google Drive',
            'not_found': 'ملف Google Drive غير موجود',
        }.get(category, 'تعذر إكمال العملية على Google Drive'))


def classify_error(error):
    if isinstance(error, RefreshError):
        return 'reconnect' if 'invalid_grant' in str(error) else 'transient'
    if isinstance(error, HttpError):
        code = error.resp.status
        try:
            body = json.loads(error.content.decode('utf-8'))
            reasons = {item.get('reason') for item in body.get('error', {}).get('errors', [])}
        except (ValueError, AttributeError, TypeError):
            reasons = set()
        if 'storageQuotaExceeded' in reasons:
            return 'quota'
        if code == 401:
            return 'reconnect'
        if code == 404:
            return 'not_found'
        if code == 409:
            return 'conflict'
        if code == 429 or reasons & {'rateLimitExceeded', 'userRateLimitExceeded'}:
            return 'rate_limit'
        if code >= 500:
            return 'transient'
        if code == 403:
            return 'permission'
    return 'transient'


def execute_with_retry(request_factory, *, attempts=4):
    """Retry only transient/rate-limit failures, with bounded jitter."""
    for attempt in range(attempts):
        try:
            return request_factory().execute(num_retries=0)
        except (HttpError, RefreshError, OSError, TimeoutError) as exc:
            category = classify_error(exc)
            if category not in {'transient', 'rate_limit'} or attempt + 1 == attempts:
                raise DriveFailure(category) from None
            retry_after = None
            if isinstance(exc, HttpError):
                try:
                    retry_after = float(exc.resp.get('retry-after', ''))
                except (ValueError, TypeError):
                    pass
            delay = min(10.0, max(0.0, retry_after)) if retry_after is not None else min(8.0, 2 ** attempt + random.random())
            time.sleep(delay)
    raise DriveFailure('transient')


class ClinicDriveProvider:
    """Always authenticates with this clinic's user refresh token."""
    def __init__(self, refresh_token):
        if not refresh_token:
            raise DriveFailure('reconnect')
        config, _, timeout = oauth_config()
        credentials = Credentials(None, refresh_token=refresh_token, token_uri=config['web']['token_uri'],
                                  client_id=config['web']['client_id'], client_secret=config['web']['client_secret'],
                                  scopes=[DRIVE_SCOPE])
        http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(timeout=timeout))
        self.service = build('drive', 'v3', http=http, cache_discovery=False)

    def reserve_ids(self, count):
        result = execute_with_retry(lambda: self.service.files().generateIds(count=count, space='drive', type='files'))
        ids = result.get('ids', [])
        if len(ids) != count or len(set(ids)) != count:
            raise DriveFailure('transient')
        return ids

    def get_metadata(self, file_id):
        return execute_with_retry(lambda: self.service.files().get(fileId=file_id, fields='id,name,mimeType,parents,appProperties,trashed'))

    def ensure_folder(self, *, folder_id, name, parent_id, tenant_id, installation_id, account_sub, kind):
        properties = {'dentix_tenant': str(tenant_id), 'dentix_installation': installation_id,
                      'dentix_kind': kind, 'dentix_account': hashlib.sha256(account_sub.encode()).hexdigest()}
        try:
            existing = self.get_metadata(folder_id)
        except DriveFailure as exc:
            if exc.category != 'not_found':
                raise
            body = {'id': folder_id, 'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'appProperties': properties}
            if parent_id:
                body['parents'] = [parent_id]
            try:
                existing = execute_with_retry(lambda: self.service.files().create(body=body, fields='id,name,mimeType,parents,appProperties,trashed'))
            except DriveFailure:
                # A timeout after creation or a 409 can leave a completed
                # folder. Verify this exact preallocated ID before retrying.
                existing = self.get_metadata(folder_id)
        if existing.get('id') != folder_id or existing.get('trashed') or existing.get('mimeType') != 'application/vnd.google-apps.folder' or existing.get('appProperties') != properties or (parent_id and parent_id not in existing.get('parents', [])):
            raise DriveFailure('permission')
        return folder_id
