"""Clinic archive routes enforce tenant admin, confirmation and reauthentication."""
import base64
from unittest.mock import AsyncMock

import pyotp
import pytest
from sqlalchemy import select

from backend.auth import create_access_token
from backend import models


def _headers(user):
    return {'Authorization': 'Bearer ' + create_access_token(data={'sub': user.username, 'tenant_id': user.tenant_id, 'role': user.role})}


@pytest.fixture
def backup_config(monkeypatch):
    monkeypatch.setenv('TENANT_BACKUP_KEY_ID', 'synthetic-key')
    monkeypatch.setenv('TENANT_BACKUP_ENCRYPTION_KEY', base64.urlsafe_b64encode(b'a' * 32).decode())
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic-installation')
    monkeypatch.setenv('TENANT_BACKUP_MAX_BYTES', '1000000')
    monkeypatch.setattr('backend.routers.tenant_backups._revision', AsyncMock(return_value='synthetic-revision'))


def test_archive_preview_confirmation_and_role_enforcement(client, db_session, admin_user, test_user, backup_config):
    archive = client.get('/api/v1/settings/backup/archive', headers=_headers(admin_user))
    assert archive.status_code == 200
    assert 'no-store' in archive.headers['cache-control']
    assert client.get('/api/v1/settings/backup/archive', headers=_headers(test_user)).status_code == 403
    preview = client.post('/api/v1/settings/backup/preview', content=archive.content, headers={**_headers(admin_user), 'Content-Type': 'application/octet-stream'})
    assert preview.status_code == 200, preview.text
    data = preview.json()['data']
    request = {'operation_id': data['operation_id'], 'confirmation': data['confirmation'],
               'archive_digest': data['archive_digest'], 'password': 'wrong'}
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request).status_code == 403
    request['password'] = 'adminpass123'
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(test_user), json=request).status_code == 403
    confirmed = client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['data']['status'] == 'confirmed'
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request).status_code == 400
    event = db_session.execute(select(models.DomainEvent).where(models.DomainEvent.aggregate_id == data['operation_id'])).scalar_one()
    assert event.event_type == 'tenant.restore.confirmed' and event.payload == {}


@pytest.mark.parametrize('legacy_otp', [None, '000000'])
def test_confirm_uses_password_for_2fa_accounts_without_changing_login_security(client, db_session, admin_user, backup_config, legacy_otp):
    admin_user.is_2fa_enabled = True
    original_secret = pyotp.random_base32()
    admin_user.otp_secret = original_secret
    db_session.commit()
    archive = client.get('/api/v1/settings/backup/archive', headers=_headers(admin_user))
    preview = client.post('/api/v1/settings/backup/preview', content=archive.content, headers={**_headers(admin_user), 'Content-Type': 'application/octet-stream'})
    assert preview.status_code == 200, preview.text
    data = preview.json()['data']
    request = {'operation_id': data['operation_id'], 'confirmation': data['confirmation'],
               'archive_digest': data['archive_digest'], 'password': 'wrong-password'}
    if legacy_otp is not None:
        request['otp_code'] = legacy_otp
    rejected = client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request)
    assert rejected.status_code == 403
    assert rejected.json()['detail'] == 'كلمة المرور الحالية غير صحيحة'
    operation = db_session.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == data['operation_id'])).scalar_one()
    assert operation.status == 'previewed'
    request['password'] = 'adminpass123'
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request).status_code == 200
    db_session.refresh(admin_user)
    assert admin_user.is_2fa_enabled and admin_user.otp_secret == original_secret


def test_legacy_json_export_omits_account_security_fields(client, admin_user):
    response = client.get('/api/v1/settings/backup/export', headers=_headers(admin_user))
    assert response.status_code == 200
    staff = next(row for row in response.json()['data']['users'] if row['id'] == admin_user.id)
    assert staff['username'] == admin_user.username
    assert not {'hashed_password', 'otp_secret', 'role', 'permissions', 'active_session_id'} & staff.keys()


def test_preview_rejects_oversized_stream_before_decoding(client, admin_user, backup_config):
    response = client.post('/api/v1/settings/backup/preview', headers={**_headers(admin_user), 'Content-Type': 'application/octet-stream'}, content=b'x' * 1_000_001)
    assert response.status_code == 413
    assert 'الحد المسموح' in response.json()['detail']
