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
    assert validate_archive_sections(payload, tenant_id=7, require_complete=False)['patients'][0]['id'] == 1
    payload['data']['patients'][0]['tenant_id'] = 8
    with pytest.raises(ArchiveError):
        validate_archive_sections(payload, tenant_id=7, require_complete=False)
    payload['data']['patients'][0]['tenant_id'] = 7
    payload['data']['patients'][0]['unexpected'] = 'value'
    with pytest.raises(ArchiveError):
        validate_archive_sections(payload, tenant_id=7, require_complete=False)
    payload['data']['patients'][0].pop('unexpected')
    payload['data']['staff_references'] = [{'id': 2, 'hashed_password': 'forbidden'}]
    with pytest.raises(ArchiveError):
        validate_archive_sections(payload, tenant_id=7, require_complete=False)


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
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
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
    payload['data']['stock_items'] = [{'id': 2, 'tenant_id': 7, 'quantity': 1.25}]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    validate_archive_values(data)
    data['expenses'][0]['cost'] = 'NaN'
    with pytest.raises(ArchiveError):
        validate_archive_values(data)
    data['expenses'][0]['cost'] = '10.25'
    data['expenses'][0]['item_name'] = ['not a string']
    with pytest.raises(ArchiveError):
        validate_archive_values(data)


@pytest.mark.asyncio
async def test_preview_confirmation_binds_actor_file_and_is_single_use(async_db_session, test_user):
    import hashlib
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, STAFF_REFERENCE_COLUMNS
    from backend.services.tenant_restore_preview import create_restore_preview, confirm_restore_preview

    data = {name: [] for name in ARCHIVE_COLUMNS}
    from backend.services.tenant_archive_export import _serialize
    staff = {column: _serialize(getattr(test_user, column)) for column in STAFF_REFERENCE_COLUMNS}
    data['staff_references'] = [staff]
    archive = encode_archive({'data': data}, tenant_id=test_user.tenant_id,
                             installation_id='synthetic', schema_revision='revision', key_id='k', key=b'a' * 32)
    operation, confirmation, _, _, mapping = await create_restore_preview(
        async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id, archive=archive,
        installation_id='synthetic', keys={'k': b'a' * 32}, supported_revisions={'revision'}, max_bytes=100_000,
    )
    assert mapping[test_user.id] == test_user.id
    digest = hashlib.sha256(archive).hexdigest()
    with pytest.raises(ArchiveError):
        await confirm_restore_preview(async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id + 1,
                                      operation_id=operation.id, confirmation=confirmation, archive_digest=digest)
    with pytest.raises(ArchiveError):
        await confirm_restore_preview(async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id,
                                      operation_id=operation.id, confirmation=confirmation, archive_digest='0' * 64)
    confirmed = await confirm_restore_preview(async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id,
                                              operation_id=operation.id, confirmation=confirmation, archive_digest=digest)
    assert confirmed.status == 'confirmed'
    with pytest.raises(ArchiveError):
        await confirm_restore_preview(async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id,
                                      operation_id=operation.id, confirmation=confirmation, archive_digest=digest)


def test_restore_gate_covers_each_archived_business_table():
    import importlib
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS
    migration = importlib.import_module('backend.alembic.versions.d42a71e9bc83_restore_transaction_gate')
    assert set(ARCHIVE_COLUMNS) == set(migration.TENANT_TABLES) - {'users'} | {'price_list_items'}


def test_serialized_references_are_rebound_and_unknown_values_fail_closed():
    from backend.services.tenant_archive_embedded_refs import (
        remap_event_payload, remap_price_snapshot, remap_stock_reference, remap_treatment_note,
    )
    mapping = {'treatments': {1: 101}, 'lab_orders': {2: 202}, 'clinical_work_items': {3: 303},
               'price_lists': {4: 404}, 'care_sessions': {5: 505}}
    assert remap_stock_reference('REVERSE:TREATMENT:1', mapping) == 'REVERSE:TREATMENT:101'
    assert remap_stock_reference('CARE_SESSION:5', mapping) == 'CARE_SESSION:505'
    assert remap_treatment_note('Link:LabOrder:2', mapping) == 'Link:LabOrder:202'
    assert remap_event_payload({'treatment_id': 1, 'bulk_work_item_ids': [3]}, mapping) == {'treatment_id': 101, 'bulk_work_item_ids': [303]}
    assert json.loads(remap_price_snapshot('{"list_id":4,"unit_price":"12.50"}', mapping)) == {'list_id': 404, 'unit_price': '12.50'}
    with pytest.raises(ArchiveError):
        remap_stock_reference('TREATMENT:999', mapping)
    with pytest.raises(ArchiveError):
        remap_event_payload({'unknown_patient_id': 42}, mapping)


def test_legacy_adapter_discards_secrets_and_reports_missing_sections():
    from backend.services.tenant_archive_legacy import adapt_legacy_json
    source = {'version': '1.0', 'tenant_id': 7, 'exported_at': '2026-01-01', 'data': {
        'users': [{'id': 1, 'tenant_id': 7, 'username': 'synthetic', 'role': 'admin',
                   'hashed_password': 'synthetic-secret', 'otp_secret': 'synthetic-otp'}],
        'tooth_statuses': [], 'patients': [],
    }}
    adapted = adapt_legacy_json(source, tenant_id=7)
    assert adapted['legacy_unverified'] is True
    assert 'material_sessions' in adapted['missing_sections']
    assert adapted['data']['tooth_status'] == []
    staff = adapted['data']['staff_references'][0]
    assert 'hashed_password' not in staff and 'otp_secret' not in staff and 'role' not in staff
    source['data']['users'][0]['role'] = 'super_admin'
    with pytest.raises(ArchiveError):
        adapt_legacy_json(source, tenant_id=7)
    source['data']['users'][0]['role'] = 'admin'
    source['data']['patients'] = [{'id': 2, 'tenant_id': 8}]
    with pytest.raises(ArchiveError):
        adapt_legacy_json(source, tenant_id=7)


@pytest.mark.asyncio
async def test_legacy_missing_sections_cannot_erase_existing_data(async_db_session, test_user):
    from decimal import Decimal
    from backend import models
    from backend.services.tenant_archive_legacy import ensure_missing_sections_empty
    async_db_session.add(models.Expense(tenant_id=test_user.tenant_id, item_name='Existing', cost=Decimal('4.00'), category='Other'))
    await async_db_session.commit()
    with pytest.raises(ArchiveError):
        await ensure_missing_sections_empty(async_db_session, tenant_id=test_user.tenant_id, missing_sections=['expenses'])
    await ensure_missing_sections_empty(async_db_session, tenant_id=test_user.tenant_id, missing_sections=['lab_payments'])
