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

    @staticmethod
    def _archive_properties(*, tenant_id, installation_id, digest):
        return {'dentix_tenant': str(tenant_id), 'dentix_installation': installation_id,
                'dentix_kind': 'backup', 'dentix_sha256': digest}

    def verify_backup(self, *, file_id, folder_id, tenant_id, installation_id, digest=None):
        meta = execute_with_retry(lambda: self.service.files().get(
            fileId=file_id, fields='id,name,mimeType,parents,appProperties,trashed,size,modifiedTime,sha256Checksum'))
        props = meta.get('appProperties') or {}
        if (meta.get('id') != file_id or meta.get('trashed') or folder_id not in meta.get('parents', [])
            or props.get('dentix_tenant') != str(tenant_id) or props.get('dentix_installation') != installation_id
            or props.get('dentix_kind') != 'backup' or (digest is not None and props.get('dentix_sha256') != digest)
            or (digest is not None and meta.get('sha256Checksum') != digest)):
            raise DriveFailure('permission')
        return meta

    def upload_backup(self, *, file_id, folder_id, tenant_id, installation_id, archive, digest):
        import io
        from googleapiclient.http import MediaIoBaseUpload
        try:
            return self.verify_backup(file_id=file_id, folder_id=folder_id, tenant_id=tenant_id, installation_id=installation_id, digest=digest)
        except DriveFailure as exc:
            if exc.category != 'not_found':
                raise
        media = MediaIoBaseUpload(io.BytesIO(archive), mimetype='application/octet-stream', chunksize=1024 * 1024, resumable=True)
        body = {'id': file_id, 'name': f'dentix-backup-{file_id}.dentix', 'parents': [folder_id],
                'appProperties': self._archive_properties(tenant_id=tenant_id, installation_id=installation_id, digest=digest)}
        request = self.service.files().create(body=body, media_body=media, fields='id')
        failures = 0
        while True:
            try:
                _, response = request.next_chunk(num_retries=0)
                if response is not None:
                    break
                failures = 0
            except (HttpError, RefreshError, OSError, TimeoutError) as exc:
                category = classify_error(exc)
                if category == 'conflict':
                    break
                if category not in {'rate_limit', 'transient'} or failures >= 3:
                    # An interrupted response may still have committed the
                    # exact ID. Verify before reporting failure.
                    try:
                        return self.verify_backup(file_id=file_id, folder_id=folder_id, tenant_id=tenant_id, installation_id=installation_id, digest=digest)
                    except DriveFailure:
                        raise DriveFailure(category) from None
                time.sleep(min(8.0, 2 ** failures + random.random()))
                failures += 1
        return self.verify_backup(file_id=file_id, folder_id=folder_id, tenant_id=tenant_id, installation_id=installation_id, digest=digest)

    def list_backups(self, *, folder_id, tenant_id, installation_id, page_token=None):
        # IDs and installation IDs are generated/configured by the server, but
        # still escape Drive query literals before constructing a query.
        def escape(value):
            return str(value).replace('\\', '\\\\').replace("'", "\\'")
        query = (f"'{escape(folder_id)}' in parents and trashed = false and "
                 f"appProperties has {{ key='dentix_kind' and value='backup' }} and "
                 f"appProperties has {{ key='dentix_tenant' and value='{escape(tenant_id)}' }} and "
                 f"appProperties has {{ key='dentix_installation' and value='{escape(installation_id)}' }}")
        result = execute_with_retry(lambda: self.service.files().list(
            q=query, pageSize=100, pageToken=page_token, fields='nextPageToken,files(id,name,size,modifiedTime,parents,appProperties,trashed,sha256Checksum)', orderBy='modifiedTime desc'))
        files = result.get('files', [])
        for item in files:
            props = item.get('appProperties') or {}
            if (item.get('trashed') or folder_id not in item.get('parents', [])
                or props.get('dentix_tenant') != str(tenant_id)
                or props.get('dentix_installation') != installation_id or props.get('dentix_kind') != 'backup'):
                raise DriveFailure('permission')
        return files, result.get('nextPageToken')

    def download_backup(self, *, file_id, folder_id, tenant_id, installation_id, max_bytes):
        import io
        from googleapiclient.http import MediaIoBaseDownload
        meta = self.verify_backup(file_id=file_id, folder_id=folder_id, tenant_id=tenant_id, installation_id=installation_id)
        try:
            size = int(meta.get('size', '-1'))
        except ValueError:
            raise DriveFailure('permission') from None
        if size < 0 or size > max_bytes:
            raise DriveFailure('permission')
        class BoundedBuffer(io.BytesIO):
            def write(self, value):
                if self.tell() + len(value) > max_bytes:
                    raise DriveFailure('permission')
                return super().write(value)
        output = BoundedBuffer()
        downloader = MediaIoBaseDownload(output, self.service.files().get_media(fileId=file_id), chunksize=1024 * 1024)
        complete = False
        failures = 0
        while not complete:
            try:
                _, complete = downloader.next_chunk(num_retries=0)
                failures = 0
            except (HttpError, RefreshError, OSError, TimeoutError) as exc:
                category = classify_error(exc)
                if category not in {'rate_limit', 'transient'} or failures >= 3:
                    raise DriveFailure(category) from None
                time.sleep(min(8.0, 2 ** failures + random.random()))
                failures += 1
        raw = output.getvalue()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != meta.get('sha256Checksum'):
            raise DriveFailure('permission')
        return raw
