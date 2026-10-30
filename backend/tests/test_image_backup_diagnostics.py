"""Clinic-admin diagnostics are bounded, tenant-scoped, private and read-only."""
from datetime import datetime, timedelta, timezone
import uuid

from backend import models
from backend.auth import create_access_token


URL = '/api/v1/settings/backup/image-operations'


def headers(user):
    return {'Authorization': 'Bearer ' + create_access_token(data={
        'sub': user.username, 'tenant_id': user.tenant_id, 'role': user.role,
    })}


def operation(tenant_id, actor_id):
    now = datetime.now(timezone.utc)
    return models.TenantDataOperation(
        id=str(uuid.uuid4()), tenant_id=tenant_id, actor_id=actor_id,
        kind='drive_image_cleanup', status='running', attempts=10,
        error_code='private-token-must-not-leak', encrypted_payload='private-image-bytes',
        archive_digest='a' * 64, confirmation_digest='b' * 64,
        created_at=now, updated_at=now, expires_at=now + timedelta(days=1),
    )


def test_admin_diagnostics_isolates_tenants_and_never_exposes_payloads(client, db_session, admin_user):
    other = models.Tenant(name='Synthetic other clinic')
    db_session.add(other)
    db_session.flush()
    own = operation(admin_user.tenant_id, admin_user.id)
    foreign = operation(other.id, admin_user.id)
    db_session.add_all([own, foreign])
    db_session.flush()
    db_session.add_all([
        models.DomainEvent(tenant_id=admin_user.tenant_id, event_type='tenant.image.cleanup',
            aggregate_type='tenant_data_operation', aggregate_id=own.id,
            status='failed', attempts=10, max_attempts=10, payload={'secret': 'hidden'}, error_message='private-google-token'),
        models.DomainEvent(tenant_id=other.id, event_type='tenant.image.cleanup',
            aggregate_type='tenant_data_operation', aggregate_id=own.id,
            status='pending', payload={'secret': 'other-tenant'}),
    ])
    db_session.commit()
    response = client.get(URL, headers=headers(admin_user))
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'private, no-store'
    result = response.json()['data']
    assert result['active_operation_count'] == 1 and result['blocked']
    row = result['operations'][0]
    assert row['operation_id'] == own.id and row['error_code'] == 'unknown'
    assert row['outbox'] == [{'status': 'failed', 'attempts': 10, 'max_attempts': 10}]
    assert all(secret not in response.text for secret in ['private-', 'other-tenant', foreign.id, 'encrypted_payload'])
    db_session.refresh(own)
    assert own.status == 'running' and own.encrypted_payload == 'private-image-bytes'


def test_diagnostics_requires_authenticated_clinic_admin(client, test_user):
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers=headers(test_user)).status_code == 403


def test_diagnostics_reports_pending_attachments_without_operations(client, db_session, admin_user, test_patient):
    db_session.add(models.Attachment(tenant_id=admin_user.tenant_id, patient_id=test_patient.id,
        file_path='synthetic', filename='private-name.png', file_type='image/png',
        storage_provider='google_drive', storage_status='pending', storage_uuid=str(uuid.uuid4())))
    db_session.commit()
    response = client.get(URL, headers=headers(admin_user))
    data = response.json()['data']
    assert data['blocked'] and data['incomplete_attachment_count'] == 1
    assert data['active_operation_count'] == 0 and data['operations'] == []
    assert 'private-name' not in response.text


def test_diagnostics_caps_results_and_preserves_total(client, db_session, admin_user):
    db_session.add_all([operation(admin_user.tenant_id, admin_user.id) for _ in range(21)])
    db_session.commit()
    response = client.get(URL, headers=headers(admin_user))
    result = response.json()['data']
    assert result['active_operation_count'] == 21
    assert len(result['operations']) == 20 and result['truncated']
