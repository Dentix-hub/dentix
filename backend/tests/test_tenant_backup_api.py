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
    confirmed = client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['data']['status'] == 'confirmed'
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request).status_code == 400
    event = db_session.execute(select(models.DomainEvent).where(models.DomainEvent.aggregate_id == data['operation_id'])).scalar_one()
    assert event.event_type == 'tenant.restore.confirmed' and event.payload == {}


def test_confirm_requires_otp_when_enabled(client, db_session, admin_user, backup_config):
    admin_user.is_2fa_enabled = True
    admin_user.otp_secret = pyotp.random_base32()
    db_session.commit()
    archive = client.get('/api/v1/settings/backup/archive', headers=_headers(admin_user))
    preview = client.post('/api/v1/settings/backup/preview', content=archive.content, headers={**_headers(admin_user), 'Content-Type': 'application/octet-stream'})
    assert preview.status_code == 200, preview.text
    data = preview.json()['data']
    request = {'operation_id': data['operation_id'], 'confirmation': data['confirmation'],
               'archive_digest': data['archive_digest'], 'password': 'adminpass123'}
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request).status_code == 403
    request['otp_code'] = pyotp.TOTP(admin_user.otp_secret).now()
    assert client.post('/api/v1/settings/backup/confirm', headers=_headers(admin_user), json=request).status_code == 200


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
