import json
import struct

import pytest

from backend.services.tenant_archive import ArchiveError, MAGIC, decode_archive, encode_archive


@pytest.fixture
def archive_args():
    return dict(tenant_id=7, installation_id='synthetic-installation', schema_revision='head', key_id='current', key=b'a' * 32)


def test_authenticated_archive_round_trip_and_tenant_isolation(archive_args):
    payload = {'data': {'patients': [{'id': 1, 'name': 'synthetic'}]}}
    archive = encode_archive(payload, **archive_args)
    kwargs = dict(tenant_id=7, installation_id='synthetic-installation', keys={'current': b'a' * 32})
    header, restored = decode_archive(archive, **kwargs)
    assert restored == payload
    assert header['counts'] == {'patients': 1}
    with pytest.raises(ArchiveError):
        decode_archive(archive, **{**kwargs, 'tenant_id': 8})
    with pytest.raises(ArchiveError):
        decode_archive(archive, **{**kwargs, 'installation_id': 'other'})
    with pytest.raises(ArchiveError):
        decode_archive(archive, **{**kwargs, 'keys': {'current': b'b' * 32}})


def test_modified_header_with_recomputed_plain_checksum_fails_authentication(archive_args):
    archive = encode_archive({'data': {}}, **archive_args)
    length = struct.unpack('>I', archive[len(MAGIC):len(MAGIC) + 4])[0]
    start = len(MAGIC) + 4
    header = json.loads(archive[start:start + length])
    header['payload_sha256'] = '0' * 64
    encoded = json.dumps(header, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    forged = MAGIC + struct.pack('>I', len(encoded)) + encoded + archive[start + length:]
    with pytest.raises(ArchiveError):
        decode_archive(forged, tenant_id=7, installation_id='synthetic-installation', keys={'current': b'a' * 32})


def test_size_limit_rejects_input_and_output(archive_args):
    with pytest.raises(ArchiveError):
        encode_archive({'data': {}, 'padding': 'x' * 200}, **archive_args, max_bytes=128)
    archive = encode_archive({'data': {}}, **archive_args)
    with pytest.raises(ArchiveError):
        decode_archive(archive, tenant_id=7, installation_id='synthetic-installation', keys={'current': b'a' * 32}, max_bytes=20)


def test_registry_rejects_unknown_columns_and_cross_tenant_rows():
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, validate_archive_sections
    payload = {'data': {name: [] for name in ARCHIVE_COLUMNS}}
    payload['data']['staff_references'] = []
    payload['data']['patients'] = [{'id': 1, 'tenant_id': 7, 'name': 'synthetic'}]
    assert validate_archive_sections(payload, tenant_id=7)['patients'][0]['id'] == 1
    payload['data']['patients'][0]['tenant_id'] = 8
    with pytest.raises(ArchiveError):
        validate_archive_sections(payload, tenant_id=7)
    payload['data']['patients'][0]['tenant_id'] = 7
    payload['data']['patients'][0]['unexpected'] = 'value'
    with pytest.raises(ArchiveError):
        validate_archive_sections(payload, tenant_id=7)
    payload['data']['patients'][0].pop('unexpected')
    payload['data']['staff_references'] = [{'id': 2, 'hashed_password': 'forbidden'}]
    with pytest.raises(ArchiveError):
        validate_archive_sections(payload, tenant_id=7)


@pytest.mark.asyncio
async def test_registry_export_scopes_tenant_and_excludes_credentials(async_db_session, test_user, test_patient):
    from decimal import Decimal
    from backend import models
    from backend.services.tenant_archive_export import export_clinic_archive_data
    from backend.services.tenant_archive_registry import validate_archive_sections

    expense = models.Expense(tenant_id=test_user.tenant_id, item_name='Synthetic', cost=Decimal('123.45'), category='Other')
    other = models.Tenant(name='Other archive tenant', domain='archive-other.invalid', is_active=True)
    async_db_session.add_all([expense, other])
    await async_db_session.flush()
    async_db_session.add(models.Expense(tenant_id=other.id, item_name='Other tenant', cost=Decimal('999'), category='Other'))
    await async_db_session.commit()
    payload = await export_clinic_archive_data(async_db_session, test_user.tenant_id)
    data = validate_archive_sections(payload, tenant_id=test_user.tenant_id)
    assert any(row['id'] == test_patient.id for row in data['patients'])
    assert next(row for row in data['expenses'] if row['id'] == expense.id)['cost'] == '123.45'
    assert all(row['tenant_id'] == test_user.tenant_id for row in data['expenses'])
    staff = next(row for row in data['staff_references'] if row['id'] == test_user.id)
    assert 'hashed_password' not in staff and 'role' not in staff and 'permissions' not in staff


def test_registry_rejects_missing_or_forged_foreign_references():
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, validate_archive_references, validate_archive_sections
    payload = {'data': {name: [] for name in ARCHIVE_COLUMNS}}
    payload['data']['staff_references'] = [{'id': 3, 'username': 'synthetic'}]
    payload['data']['patients'] = [{'id': 1, 'tenant_id': 7, 'assigned_doctor_id': 3}]
    payload['data']['treatments'] = [{'id': 4, 'tenant_id': 7, 'patient_id': 1, 'doctor_id': 3}]
    data = validate_archive_sections(payload, tenant_id=7)
    validate_archive_references(data, tenant_id=7)
    data['treatments'][0]['patient_id'] = 99
    with pytest.raises(ArchiveError):
        validate_archive_references(data, tenant_id=7)
    data['treatments'][0]['patient_id'] = 1
    data['treatments'][0]['doctor_id'] = 99
    with pytest.raises(ArchiveError):
        validate_archive_references(data, tenant_id=7)


@pytest.mark.asyncio
async def test_staff_mapping_uses_existing_tenant_identity_and_fails_closed(async_db_session, test_user):
    from backend.services.tenant_archive_identity import resolve_staff_mapping
    mapping = await resolve_staff_mapping(async_db_session, test_user.tenant_id, [
        {'id': test_user.id, 'username': test_user.username},
    ])
    assert mapping == {test_user.id: test_user.id}
    with pytest.raises(ArchiveError):
        await resolve_staff_mapping(async_db_session, test_user.tenant_id, [
            {'id': test_user.id, 'username': 'different-synthetic-user'},
        ])
    with pytest.raises(ArchiveError):
        await resolve_staff_mapping(async_db_session, test_user.tenant_id + 99999, [
            {'id': test_user.id, 'username': test_user.username},
        ])


def test_registry_rejects_invalid_money_and_column_types():
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, validate_archive_sections, validate_archive_values
    payload = {'data': {name: [] for name in ARCHIVE_COLUMNS}}
    payload['data']['staff_references'] = []
    payload['data']['expenses'] = [{'id': 1, 'tenant_id': 7, 'item_name': 'synthetic', 'cost': '10.25'}]
    data = validate_archive_sections(payload, tenant_id=7)
    validate_archive_values(data)
    data['expenses'][0]['cost'] = 'NaN'
    with pytest.raises(ArchiveError):
        validate_archive_values(data)
    data['expenses'][0]['cost'] = '10.25'
    data['expenses'][0]['item_name'] = ['not a string']
    with pytest.raises(ArchiveError):
        validate_archive_values(data)
