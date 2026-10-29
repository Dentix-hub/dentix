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


def test_known_pre_image_archive_defaults_to_legacy_storage():
    from backend.services.tenant_archive_adapters import adapt_archive_version
    payload = {'data': {'attachments': [{'id': 1, 'tenant_id': 7, 'patient_id': 3, 'file_path': 'legacy/path.png', 'filename': 'x.png', 'file_type': 'image/png', 'note': None, 'created_at': '2026-01-01T00:00:00'}]}}
    adapted = adapt_archive_version(payload, 'ab52d9c807a1')
    row = adapted['data']['attachments'][0]
    assert row['storage_provider'] == 'legacy' and row['storage_status'] == 'ready'
    assert row['storage_uuid'] is None and row['file_path'] == 'legacy/path.png'
    assert 'storage_provider' not in payload['data']['attachments'][0]
    payload['data']['attachments'][0]['drive_original_id'] = 'forged'
    with pytest.raises(ArchiveError):
        adapt_archive_version(payload, 'ab52d9c807a1')


def test_restored_attachment_paths_cannot_escape_tenant_or_forge_drive_metadata():
    from backend.services.tenant_archive_attachments import validate_attachment_metadata
    data = {'attachments': [{'storage_provider': 'legacy', 'file_path': 'tenant_7/synthetic.png'}]}
    validate_attachment_metadata(data, 7)
    data['attachments'][0]['file_path'] = 'tenant_8/other.png'
    with pytest.raises(ArchiveError):
        validate_attachment_metadata(data, 7)
    data['attachments'][0]['file_path'] = 'tenant_7/../../etc/passwd'
    with pytest.raises(ArchiveError):
        validate_attachment_metadata(data, 7)
    data['attachments'][0] = {'storage_provider': 'google_drive', 'storage_uuid': 'not-a-uuid', 'file_path': '/api/v1/upload/drive/not-a-uuid/content'}
    with pytest.raises(ArchiveError):
        validate_attachment_metadata(data, 7)


@pytest.mark.asyncio
async def test_preview_reports_unavailable_and_unverified_attachment_references(async_db_session, test_user):
    from backend.services.tenant_archive_availability import attachment_availability
    rows = [
        {'storage_provider': 'legacy', 'file_path': f'tenant_{test_user.tenant_id}/missing-synthetic.png'},
        {'storage_provider': 'legacy', 'file_path': 'https://res.cloudinary.com/example/image/upload/synthetic.png'},
        {'storage_provider': 'google_drive', 'storage_status': 'ready', 'google_account_sub': 'synthetic'},
    ]
    result = await attachment_availability(async_db_session, tenant_id=test_user.tenant_id, rows=rows)
    assert result == {'missing': 2, 'unverified': 1}


@pytest.mark.asyncio
async def test_realistic_historical_null_optional_fields_pass_preview_and_export(async_db_session, test_user):
    from decimal import Decimal
    from backend import models
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_archive_export import export_clinic_archive_data
    from backend.services.tenant_restore_preview import create_restore_preview
    from backend.services.tenant_archive_registry import validate_archive_values

    # Realistic patient with optional clinical fields left as NULL (None)
    patient = models.Patient(
        tenant_id=test_user.tenant_id,
        name="Null Notes Patient",
        age=35,
        phone="01099999999",
        medical_history=None,
        notes=None,
    )
    # User with no compensation set (NULL in DB)
    staff_user = models.User(
        tenant_id=test_user.tenant_id,
        username="null_comp_staff",
        email="nullcomp@example.com",
        hashed_password="synthetic_hash",
        role="nurse",
        is_active=True,
        commission_percent=None,
        fixed_salary=None,
        per_appointment_fee=None,
    )
    async_db_session.add_all([patient, staff_user])
    await async_db_session.commit()

    # Exporter should assess compatibility and pass without raising NULL value rejection
    payload = await export_clinic_archive_data(async_db_session, test_user.tenant_id)
    assert payload is not None
    # Direct validation of the values should also pass
    validate_archive_values(payload['data'])

    # Round trip to encrypted .dentix archive and create_restore_preview
    archive = encode_archive(
        payload, tenant_id=test_user.tenant_id, installation_id='synthetic-inst',
        schema_revision='e2b3c4d5e6f7', key_id='k1', key=b'k' * 32, max_bytes=1000000,
    )
    operation, confirmation, header, counts, mapping = await create_restore_preview(
        async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id,
        archive=archive, installation_id='synthetic-inst', keys={'k1': b'k' * 32},
        supported_revisions={'e2b3c4d5e6f7'}, max_bytes=1000000,
    )
    assert operation.status == 'previewed'
    assert counts['patients'] >= 1


def test_genuinely_required_missing_values_fail_with_structured_diagnostics():
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, validate_archive_sections, validate_archive_values

    # Test missing patient name
    payload = {'data': {name: [] for name in ARCHIVE_COLUMNS}}
    payload['data']['staff_references'] = [{'id': 1, 'username': 'admin'}]
    payload['data']['patients'] = [{
        'id': 10, 'tenant_id': 7, 'name': None, 'age': 25, 'phone': '011',
        'is_deleted': False, 'created_at': '2026-01-01T00:00:00',
    }]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_archive_values(data)
    err = exc_info.value
    assert err.section == 'patients'
    assert err.field == 'name'
    assert err.category == 'missing_required_value'
    assert err.counts == 1
    assert 'قيمة مطلوبة مفقودة في النسخة الاحتياطية (patients.name)' in str(err)

    # Test missing user username in staff_references
    payload['data']['patients'][0]['name'] = 'Valid Name'
    payload['data']['staff_references'][0]['username'] = None
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_archive_values(data)
    err = exc_info.value
    assert err.section == 'staff_references'
    assert err.field == 'username'
    assert err.category == 'missing_required_value'
    assert err.counts == 1
    assert 'قيمة مطلوبة مفقودة في النسخة الاحتياطية (staff_references.username)' in str(err)


def test_legacy_json_numeric_and_null_staff_compensation_adaptation():
    from backend.services.tenant_archive_legacy import adapt_legacy_json
    from backend.services.tenant_archive_registry import validate_archive_values

    source = {
        'version': '1.0',
        'tenant_id': 7,
        'exported_at': '2026-01-01T00:00:00',
        'data': {
            'users': [{
                'id': 1, 'tenant_id': 7, 'username': 'synthetic_legacy', 'role': 'doctor',
                # commission_percent and fixed_salary omitted or float
                'commission_percent': 15.5,
            }],
            'patients': [{
                'id': 2, 'tenant_id': 7, 'name': 'Legacy Patient', 'age': 40, 'phone': '123',
                'medical_history': None, 'notes': None, 'created_at': '2026-01-01T00:00:00',
                'is_deleted': False,
            }],
            'expenses': [{
                'id': 100, 'tenant_id': 7, 'item_name': 'Supplies', 'cost': 123.45,
            }],
        },
    }
    adapted = adapt_legacy_json(source, tenant_id=7)
    assert adapted['legacy_unverified'] is True
    # Verify that float cost was converted to string for exact Decimal handling
    assert adapted['data']['expenses'][0]['cost'] == '123.45'
    assert adapted['data']['staff_references'][0]['commission_percent'] == '15.5'
    # Fixed salary was omitted, so it should be None
    assert adapted['data']['staff_references'][0]['fixed_salary'] is None
    # Validate that validate_archive_values succeeds on this adapted data
    validate_archive_values(adapted['data'])


@pytest.mark.asyncio
async def test_preview_failure_makes_no_clinical_or_financial_writes(async_db_session, test_user, test_patient):
    from sqlalchemy import select
    from backend import models
    from backend.services.tenant_restore_preview import create_restore_preview

    patients_before = (await async_db_session.execute(select(models.Patient).where(models.Patient.tenant_id == test_user.tenant_id))).scalars().all()
    count_before = len(patients_before)
    name_before = test_patient.name

    # Create forged archive (corrupted data)
    corrupted_archive = b"corrupted-invalid-archive-bytes"
    with pytest.raises(ArchiveError):
        await create_restore_preview(
            async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id,
            archive=corrupted_archive, installation_id='synth', keys={'k': b'k' * 32},
            supported_revisions={'e2b3c4d5e6f7'}, max_bytes=1000000,
        )

    # Re-check database state to verify zero mutations
    patients_after = (await async_db_session.execute(select(models.Patient).where(models.Patient.tenant_id == test_user.tenant_id))).scalars().all()
    assert len(patients_after) == count_before
    current_patient = (await async_db_session.execute(select(models.Patient).where(models.Patient.id == test_patient.id))).scalar_one()
    assert current_patient.name == name_before


@pytest.mark.asyncio
async def test_export_fails_early_when_business_data_is_invalid(async_db_session, test_user, test_patient):
    from backend.services.tenant_archive_export import export_clinic_archive_data

    # Test that validate_restore catches invalid data during export
    # e.g., if a required column is forced to None
    async def mock_export_corrupt(db, tenant_id):
        payload = await export_clinic_archive_data(db, tenant_id, validate_restore=False)
        payload['data']['patients'][0]['name'] = None
        from backend.services.tenant_archive_registry import validate_archive_compatibility
        await validate_archive_compatibility(db, payload, tenant_id=tenant_id)
        return payload

    with pytest.raises(ArchiveError) as exc_info:
        await mock_export_corrupt(async_db_session, test_user.tenant_id)
    assert exc_info.value.field == 'name'
    assert exc_info.value.category == 'missing_required_value'


def test_sql_foreign_key_structured_diagnostics():
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, validate_archive_references, validate_archive_sections

    payload = {'data': {name: [] for name in ARCHIVE_COLUMNS}}
    payload['data']['staff_references'] = [{'id': 10, 'username': 'doctor_a'}]
    payload['data']['patients'] = [{'id': 1, 'tenant_id': 7, 'assigned_doctor_id': 10}]
    payload['data']['treatments'] = [
        {'id': 101, 'tenant_id': 7, 'patient_id': 1, 'doctor_id': 999},
        {'id': 102, 'tenant_id': 7, 'patient_id': 1, 'doctor_id': 999},
    ]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)

    # Rejection of invalid foreign reference doctor_id with aggregate count=2
    with pytest.raises(ArchiveError) as exc_info:
        validate_archive_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'treatments'
    assert err.field == 'doctor_id'
    assert err.referenced_section == 'users'
    assert err.category == 'invalid_reference'
    assert err.counts == 2
    assert 'تحتوي النسخة الاحتياطية على مرجع غير صالح (treatments.doctor_id)' in str(err)

    # Rejection of SQL type mismatch in patient_id
    payload['data']['treatments'][0]['doctor_id'] = 10
    payload['data']['treatments'][1]['doctor_id'] = 10
    payload['data']['treatments'][0]['patient_id'] = 'not-an-integer'
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_archive_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'treatments'
    assert err.field == 'patient_id'
    assert err.referenced_section == 'patients'
    assert err.category == 'invalid_reference_type'
    assert err.counts == 1


def test_embedded_references_structured_diagnostics():
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, validate_archive_sections
    from backend.services.tenant_archive_embedded_refs import validate_embedded_references

    payload = {'data': {name: [] for name in ARCHIVE_COLUMNS}}
    payload['data']['staff_references'] = [{'id': 10, 'username': 'doc'}]
    payload['data']['treatments'] = [{'id': 1, 'tenant_id': 7}]
    payload['data']['price_lists'] = [{'id': 5, 'tenant_id': 7}]
    payload['data']['lab_orders'] = [{'id': 20, 'tenant_id': 7}]

    # 1. Invalid stock movement reference with aggregate count
    payload['data']['stock_movements'] = [
        {'id': 1, 'tenant_id': 7, 'reference_id': 'TREATMENT:999'},
        {'id': 2, 'tenant_id': 7, 'reference_id': 'REVERSE:TREATMENT:999'},
    ]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_embedded_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'stock_movements'
    assert err.field == 'reference_id'
    assert err.referenced_section == 'treatments'
    assert err.category == 'invalid_reference'
    assert err.counts == 2
    assert 'تحتوي النسخة الاحتياطية على مرجع غير صالح (stock_movements.reference_id)' in str(err)

    # 2. Invalid clinical event payload treatment reference
    payload['data']['stock_movements'] = []
    payload['data']['clinical_events'] = [
        {'id': 1, 'tenant_id': 7, 'payload': {'treatment_id': 888, 'kind': 'procedure'}},
    ]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_embedded_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'clinical_events'
    assert err.field == 'payload.treatment_id'
    assert err.referenced_section == 'treatments'
    assert err.category == 'invalid_reference'
    assert err.counts == 1
    assert 'تحتوي النسخة الاحتياطية على مرجع غير صالح (clinical_events.payload.treatment_id)' in str(err)

    # 3. Invalid treatment notes lab order link
    payload['data']['clinical_events'] = []
    payload['data']['treatments'] = [
        {'id': 1, 'tenant_id': 7, 'notes': 'Link:LabOrder:777'},
    ]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_embedded_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'treatments'
    assert err.field == 'notes'
    assert err.referenced_section == 'lab_orders'
    assert err.category == 'invalid_reference'
    assert err.counts == 1

    # 4. Invalid treatment price_snapshot list_id
    payload['data']['treatments'] = [
        {'id': 1, 'tenant_id': 7, 'price_snapshot': '{"list_id":666,"price":"50"}'},
    ]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_embedded_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'treatments'
    assert err.field == 'price_snapshot.list_id'
    assert err.referenced_section == 'price_lists'
    assert err.category == 'invalid_reference'
    assert err.counts == 1

    # 5. Invalid learning log treatment reference
    payload['data']['treatments'] = [{'id': 1, 'tenant_id': 7}]
    payload['data']['material_learning_logs'] = [
        {'id': 1, 'tenant_id': 7, 'calculation_data': '{"dist_log":[{"treatment_id":555}]}'},
    ]
    data = validate_archive_sections(payload, tenant_id=7, require_complete=False)
    with pytest.raises(ArchiveError) as exc_info:
        validate_embedded_references(data, tenant_id=7)
    err = exc_info.value
    assert err.section == 'material_learning_logs'
    assert err.field == 'calculation_data.dist_log.treatment_id'
    assert err.referenced_section == 'treatments'
    assert err.category == 'invalid_reference'
    assert err.counts == 1


@pytest.mark.asyncio
async def test_tenant_consistency_audit_report(async_db_session, test_user, test_patient):
    from decimal import Decimal
    from backend import models
    from backend.services.tenant_archive_consistency import (
        audit_tenant_consistency, format_consistency_report,
    )

    # 1. Consistent tenant check
    result = await audit_tenant_consistency(async_db_session, test_user.tenant_id)
    assert result["consistent"] is True
    assert result["summary"]["missing_targets_count"] == 0
    assert result["summary"]["forbidden_cross_tenant_reference_count"] == 0
    report_text = format_consistency_report(result)
    assert "CONSISTENT" in report_text

    # 2. Add another tenant and inject cross-tenant reference
    other_tenant = models.Tenant(name="Other consistency tenant", domain="other.invalid", is_active=True)
    async_db_session.add(other_tenant)
    await async_db_session.flush()

    other_user = models.User(
        tenant_id=other_tenant.id, username="other_doc", email="otherdoc@example.com",
        hashed_password="synth", role="doctor", is_active=True,
    )
    async_db_session.add(other_user)
    await async_db_session.flush()

    # Treatment in test_user's tenant referencing other_user (cross-tenant)
    bad_treatment = models.Treatment(
        tenant_id=test_user.tenant_id,
        patient_id=test_patient.id,
        doctor_id=other_user.id,
        cost=Decimal("100"),
        discount=Decimal("0"),
    )
    async_db_session.add(bad_treatment)
    await async_db_session.commit()

    inconsistent = await audit_tenant_consistency(async_db_session, test_user.tenant_id)
    assert inconsistent["consistent"] is False
    assert inconsistent["summary"]["forbidden_cross_tenant_reference_count"] == 1
    assert any(
        entry["relation"] == "treatments.doctor_id -> users"
        for entry in inconsistent["categories"]["forbidden_cross_tenant_reference"]
    )
    inconsistent_report = format_consistency_report(inconsistent)
    assert "INCONSISTENT" in inconsistent_report
    assert "FORBIDDEN CROSS TENANT REFERENCE" in inconsistent_report
