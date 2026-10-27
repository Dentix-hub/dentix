"""Per-browser Google OAuth state and provider-scope regressions."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from backend import models
from backend.services.clinic_google_attempts import start_google_attempt, consume_google_attempt
from backend.services.clinic_google_oauth import GoogleConnectionError


@pytest.mark.asyncio
async def test_attempt_is_browser_bound_single_use_and_rechecks_role(async_db_session, admin_user):
    admin_user = await async_db_session.get(models.User, admin_user.id)
    with patch('backend.services.clinic_google_attempts.authorization_url', side_effect=lambda **kwargs: kwargs['state']):
        state, browser = await start_google_attempt(async_db_session, user=admin_user)
        attempt = (await async_db_session.execute(select(models.GoogleOAuthAttempt).where(models.GoogleOAuthAttempt.user_id == admin_user.id))).scalar_one()
        with pytest.raises(GoogleConnectionError):
            await consume_google_attempt(async_db_session, tenant_id=admin_user.tenant_id, attempt_id=attempt.id, state=state, browser_secret='different-browser')
        details = await consume_google_attempt(async_db_session, tenant_id=admin_user.tenant_id, attempt_id=attempt.id, state=state, browser_secret=browser)
        assert details['user_id'] == admin_user.id and details['verifier']
        with pytest.raises(GoogleConnectionError):
            await consume_google_attempt(async_db_session, tenant_id=admin_user.tenant_id, attempt_id=attempt.id, state=state, browser_secret=browser)
        state2, browser2 = await start_google_attempt(async_db_session, user=admin_user, browser_secret=browser)
        attempt2 = (await async_db_session.execute(select(models.GoogleOAuthAttempt).where(models.GoogleOAuthAttempt.state_digest != attempt.state_digest))).scalar_one()
        admin_user.role = 'doctor'
        async_db_session.add(admin_user)
        await async_db_session.commit()
        with pytest.raises(GoogleConnectionError):
            await consume_google_attempt(async_db_session, tenant_id=admin_user.tenant_id, attempt_id=attempt2.id, state=state2, browser_secret=browser2)


@pytest.mark.asyncio
async def test_expired_state_and_other_tenant_are_rejected(async_db_session, admin_user):
    admin_user = await async_db_session.get(models.User, admin_user.id)
    with patch('backend.services.clinic_google_attempts.authorization_url', side_effect=lambda **kwargs: kwargs['state']):
        state, browser = await start_google_attempt(async_db_session, user=admin_user)
        attempt = (await async_db_session.execute(select(models.GoogleOAuthAttempt))).scalar_one()
        with pytest.raises(GoogleConnectionError):
            await consume_google_attempt(async_db_session, tenant_id=admin_user.tenant_id + 1000, attempt_id=attempt.id, state=state, browser_secret=browser)
        attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await async_db_session.commit()
        with pytest.raises(GoogleConnectionError):
            await consume_google_attempt(async_db_session, tenant_id=admin_user.tenant_id, attempt_id=attempt.id, state=state, browser_secret=browser)


def test_provider_requires_offline_token_exact_scopes_and_nonce(monkeypatch):
    from types import SimpleNamespace
    from backend.services import clinic_google_oauth as oauth
    nonce = 'synthetic-nonce'
    class FakeFlow:
        credentials = SimpleNamespace(refresh_token='synthetic-refresh')
        def fetch_token(self, **kwargs):
            assert kwargs['timeout'] == 9
            return {'scope': 'openid email https://www.googleapis.com/auth/drive.file', 'id_token': 'synthetic-id-token'}
    monkeypatch.setattr(oauth, 'oauth_config', lambda: ({'web': {'client_id': 'synthetic-client'}}, 'https://example.test/callback', 9))
    monkeypatch.setattr(oauth, '_flow', lambda _: FakeFlow())
    monkeypatch.setattr(oauth.id_token, 'verify_oauth2_token', lambda *args, **kwargs: {'iss': 'https://accounts.google.com', 'sub': 'stable-sub', 'nonce': nonce, 'email': 'synthetic@example.test'})
    result = oauth.exchange_and_verify(code='synthetic-code', verifier='synthetic-verifier', nonce_digest=oauth.digest(nonce))
    assert result['sub'] == 'stable-sub' and result['refresh_token'] == 'synthetic-refresh'
    with pytest.raises(GoogleConnectionError):
        oauth.exchange_and_verify(code='synthetic-code', verifier='synthetic-verifier', nonce_digest=oauth.digest('wrong'))
    class BroadFlow(FakeFlow):
        def fetch_token(self, **kwargs):
            return {'scope': 'openid email https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/drive', 'id_token': 'synthetic-id-token'}
    monkeypatch.setattr(oauth, '_flow', lambda _: BroadFlow())
    with pytest.raises(GoogleConnectionError):
        oauth.exchange_and_verify(code='synthetic-code', verifier='synthetic-verifier', nonce_digest=oauth.digest(nonce))
    class NoRefreshFlow(FakeFlow):
        credentials = SimpleNamespace(refresh_token=None)
    monkeypatch.setattr(oauth, '_flow', lambda _: NoRefreshFlow())
    with pytest.raises(GoogleConnectionError):
        oauth.exchange_and_verify(code='synthetic-code', verifier='synthetic-verifier', nonce_digest=oauth.digest(nonce))


@pytest.mark.asyncio
async def test_folder_reservations_survive_failure_without_losing_connection(async_db_session, admin_user, monkeypatch):
    import uuid
    from backend.services.clinic_google_connection import finish_google_connection
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    monkeypatch.setattr('backend.services.clinic_google_attempts.authorization_url', lambda **kwargs: kwargs['state'])
    class Provider:
        def __init__(self):
            self.fail_once = True
            self.created = []
            self.reservations = []
        def reserve_ids(self, count):
            ids = [uuid.uuid4().hex for _ in range(count)]
            self.reservations.append(ids)
            return ids
        def ensure_folder(self, **kwargs):
            self.created.append(kwargs['folder_id'])
            if kwargs['kind'] == 'backups' and self.fail_once:
                self.fail_once = False
                raise RuntimeError('synthetic outage')
    provider = Provider()
    local_admin = await async_db_session.get(models.User, admin_user.id)
    tenant = await async_db_session.get(models.Tenant, admin_user.tenant_id)
    tenant.google_refresh_token = 'healthy-old-token'
    tenant.google_account_sub = 'same-account'
    tenant.google_connection_status = 'connected'
    await async_db_session.commit()
    state, browser = await start_google_attempt(async_db_session, user=local_admin)
    attempt = (await async_db_session.execute(select(models.GoogleOAuthAttempt).where(models.GoogleOAuthAttempt.user_id == local_admin.id))).scalar_one()
    details = await consume_google_attempt(async_db_session, tenant_id=tenant.id, attempt_id=attempt.id, state=state, browser_secret=browser)
    identity = {'sub': 'same-account', 'email': 'synthetic@example.test', 'refresh_token': 'new-token'}
    with pytest.raises(RuntimeError):
        await finish_google_connection(details=details, identity=identity, provider=provider)
    await async_db_session.refresh(tenant)
    assert tenant.google_refresh_token == 'healthy-old-token'
    state2, _ = await start_google_attempt(async_db_session, user=local_admin, browser_secret=browser)
    attempt2 = (await async_db_session.execute(select(models.GoogleOAuthAttempt).where(models.GoogleOAuthAttempt.state_digest != attempt.state_digest))).scalar_one()
    details2 = await consume_google_attempt(async_db_session, tenant_id=tenant.id, attempt_id=attempt2.id, state=state2, browser_secret=browser)
    await finish_google_connection(details=details2, identity=identity, provider=provider)
    await async_db_session.refresh(tenant)
    assert tenant.google_refresh_token == 'new-token'
    assert [tenant.google_root_folder_id, tenant.google_backup_folder_id, tenant.google_image_folder_id] == provider.reservations[0]
    assert tenant.google_connection_generation == 1


def test_drive_error_classification_and_clinic_credentials_ignore_service_accounts(monkeypatch):
    import json
    import httplib2
    from googleapiclient.errors import HttpError
    from backend.services import clinic_drive_provider as provider
    monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{"type":"synthetic"}')
    monkeypatch.setattr(provider, 'oauth_config', lambda: ({'web': {'client_id': 'id', 'client_secret': 'secret', 'token_uri': 'https://example.test/token'}}, 'https://example.test/callback', 7))
    captured = {}
    def fake_build(*args, **kwargs):
        captured['http'] = kwargs['http']
        return object()
    monkeypatch.setattr(provider, 'build', fake_build)
    provider.ClinicDriveProvider('clinic-user-token')
    assert captured['http'].credentials.refresh_token == 'clinic-user-token'
    assert captured['http'].http.timeout == 7
    def error(status, reason):
        body = json.dumps({'error': {'errors': [{'reason': reason}]}}).encode()
        return HttpError(httplib2.Response({'status': str(status)}), body)
    assert provider.classify_error(error(403, 'storageQuotaExceeded')) == 'quota'
    assert provider.classify_error(error(403, 'rateLimitExceeded')) == 'rate_limit'
    assert provider.classify_error(error(403, 'insufficientFilePermissions')) == 'permission'
    assert provider.classify_error(error(401, 'authError')) == 'reconnect'
    assert provider.classify_error(error(503, 'backendError')) == 'transient'


@pytest.mark.asyncio
async def test_stale_provider_failure_cannot_invalidate_reconnected_account(async_db_session, admin_user):
    from backend.services.clinic_google_connection import mark_needs_reconnect
    tenant = await async_db_session.get(models.Tenant, admin_user.tenant_id)
    tenant.google_connection_status = 'connected'
    tenant.google_connection_generation = 8
    await async_db_session.commit()
    assert not await mark_needs_reconnect(async_db_session, tenant_id=tenant.id, generation=7)
    await async_db_session.refresh(tenant)
    assert tenant.google_connection_status == 'connected' and tenant.google_connection_generation == 8
    assert await mark_needs_reconnect(async_db_session, tenant_id=tenant.id, generation=8)
    await async_db_session.refresh(tenant)
    assert tenant.google_connection_status == 'needs_reconnect' and tenant.google_connection_generation == 9


def test_drive_backup_metadata_rejects_cross_tenant_and_wrong_folder():
    from types import SimpleNamespace
    from backend.services.clinic_drive_provider import ClinicDriveProvider, DriveFailure
    class Request:
        def __init__(self, value):
            self.value = value
        def execute(self, **kwargs):
            return self.value
    class Files:
        def __init__(self, value):
            self.value = value
        def get(self, **kwargs):
            return Request(self.value)
    meta = {'id': 'file', 'parents': ['folder-a'], 'trashed': False, 'sha256Checksum': 'digest',
            'appProperties': {'dentix_tenant': '7', 'dentix_installation': 'env', 'dentix_kind': 'backup', 'dentix_sha256': 'digest'}}
    provider = ClinicDriveProvider.__new__(ClinicDriveProvider)
    provider.service = SimpleNamespace(files=lambda: Files(meta))
    assert provider.verify_backup(file_id='file', folder_id='folder-a', tenant_id=7, installation_id='env', digest='digest') == meta
    with pytest.raises(DriveFailure):
        provider.verify_backup(file_id='file', folder_id='folder-b', tenant_id=7, installation_id='env')
    with pytest.raises(DriveFailure):
        provider.verify_backup(file_id='file', folder_id='folder-a', tenant_id=8, installation_id='env')
    with pytest.raises(DriveFailure):
        provider.verify_backup(file_id='file', folder_id='folder-a', tenant_id=7, installation_id='other-env')


def test_drive_backup_listing_checks_folder_metadata_and_pagination():
    from types import SimpleNamespace
    from backend.services.clinic_drive_provider import ClinicDriveProvider, DriveFailure
    calls = []
    class Request:
        def execute(self, **kwargs):
            return {'files': [{'id': 'file', 'parents': ['folder'], 'appProperties': {
                'dentix_tenant': '7', 'dentix_installation': 'env', 'dentix_kind': 'backup'}}], 'nextPageToken': 'next'}
    class Files:
        def list(self, **kwargs):
            calls.append(kwargs)
            return Request()
    provider = ClinicDriveProvider.__new__(ClinicDriveProvider)
    provider.service = SimpleNamespace(files=lambda: Files())
    files, next_page = provider.list_backups(folder_id='folder', tenant_id=7, installation_id='env', page_token='previous')
    assert files[0]['id'] == 'file' and next_page == 'next'
    assert calls[0]['pageToken'] == 'previous'
    with pytest.raises(DriveFailure):
        provider.list_backups(folder_id='other-folder', tenant_id=7, installation_id='env')
