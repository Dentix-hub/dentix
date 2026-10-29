"""Validate and remap business IDs stored in version-one structured fields."""
import json
import re

from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_history import deleted_treatment_contexts, historical_treatment_ids

EVENT_IDS = {
    'treatment_id': 'treatments', 'legacy_treatment_id': 'treatments',
    'tooth_status_id': 'tooth_status', 'legacy_tooth_status_id': 'tooth_status',
    'work_item_id': 'clinical_work_items', 'original_work_item_id': 'clinical_work_items',
    'replacement_work_item_id': 'clinical_work_items', 'clinical_work_item_id': 'clinical_work_items',
    'patient_id': 'patients', 'charge_id': 'clinical_charges',
    'care_session_id': 'care_sessions', 'event_id': 'clinical_events',
    'price_list_id': 'price_lists', 'tenant_id': 'tenants',
    'actor_user_id': 'users', 'created_by_user_id': 'users', 'user_id': 'users',
}
NON_DATABASE_IDS = {'version_id', 'expected_version_id', 'root_id', 'canal_id', 'idempotency_key'}
REFERENCE_PREFIXES = {'TREATMENT': 'treatments', 'TREATMENT_MATERIALS': 'treatments', 'CARE_SESSION': 'care_sessions'}


def _mapped(mapping, table, old_id, *, section=None, field=None, historical_mapping=None):
    suffix = f' ({section}.{field})' if section and field else ''
    if not isinstance(old_id, int) or isinstance(old_id, bool):
        raise ArchiveError(
            f'نوع أو قيمة غير صالحة في النسخة الاحتياطية{suffix}',
            section=section, field=field, referenced_section=table,
            category='invalid_reference_type', counts=1,
        )
    if old_id not in mapping.get(table, {}):
        if table == 'treatments' and historical_mapping and old_id in historical_mapping:
            return historical_mapping[old_id]
        raise ArchiveError(
            f'تحتوي النسخة الاحتياطية على مرجع غير صالح{suffix}',
            section=section, field=field, referenced_section=table,
            category='invalid_reference', counts=1,
        )
    return mapping[table][old_id]


def remap_event_payload(payload, mapping, *, section='clinical_events', field_prefix='payload', historical_mapping=None):
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ArchiveError(
            f'بيانات الحدث السريري غير صالحة ({section}.{field_prefix})',
            section=section, field=field_prefix, category='invalid_payload', counts=1,
        )
    def visit(value, current_prefix):
        if isinstance(value, list):
            return [visit(item, current_prefix) for item in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, item in value.items():
            canonical_field = f'{current_prefix}.{key}' if current_prefix else key
            if key in EVENT_IDS and item is not None:
                result[key] = _mapped(mapping, EVENT_IDS[key], item, section=section, field=canonical_field,
                                      historical_mapping=historical_mapping)
            elif key == 'bulk_work_item_ids':
                if not isinstance(item, list):
                    raise ArchiveError(
                        f'بيانات الحدث السريري غير صالحة ({section}.{canonical_field})',
                        section=section, field=canonical_field, category='invalid_payload', counts=1,
                    )
                result[key] = [_mapped(mapping, 'clinical_work_items', entry, section=section, field=canonical_field) for entry in item]
            elif key.endswith(('_id', '_ids')) and key not in NON_DATABASE_IDS and item is not None:
                raise ArchiveError(
                    f'مرجع الحدث السريري غير مدعوم ({section}.{canonical_field})',
                    section=section, field=canonical_field, category='unsupported_reference', counts=1,
                )
            else:
                result[key] = visit(item, canonical_field)
        return result
    return visit(payload, field_prefix)


def remap_stock_reference(value, mapping, *, section='stock_movements', field='reference_id', historical_mapping=None):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ArchiveError(
            f'مرجع المخزون غير صالح ({section}.{field})',
            section=section, field=field, category='invalid_reference_type', counts=1,
        )
    match = re.fullmatch(r'(REVERSE:)?(TREATMENT|TREATMENT_MATERIALS|CARE_SESSION):(\d+)', value)
    if match:
        prefix, kind, old_id = match.groups()
        target_table = REFERENCE_PREFIXES[kind]
        return f'{prefix or ""}{kind}:{_mapped(mapping, target_table, int(old_id), section=section, field=field, historical_mapping=historical_mapping)}'
    # Unknown references cannot be safely rebound to regenerated IDs.
    raise ArchiveError(
        f'مرجع المخزون غير مدعوم في النسخة الاحتياطية ({section}.{field})',
        section=section, field=field, category='unsupported_reference', counts=1,
    )


def remap_treatment_note(value, mapping, *, section='treatments', field='notes'):
    if value is None:
        return None
    match = re.fullmatch(r'Link:LabOrder:(\d+)', value)
    if match:
        return f'Link:LabOrder:{_mapped(mapping, "lab_orders", int(match.group(1)), section=section, field=field)}'
    return value


def remap_price_snapshot(value, mapping, *, section='treatments', field='price_snapshot'):
    if value is None:
        return None
    try:
        snapshot = json.loads(value)
        if not isinstance(snapshot, dict):
            raise ValueError
        if snapshot.get('list_id') is not None:
            snapshot['list_id'] = _mapped(mapping, 'price_lists', snapshot['list_id'], section=section, field=f'{field}.list_id')
        return json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))
    except (ValueError, TypeError) as exc:
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError(
            f'بيانات سعر العلاج غير صالحة ({section}.{field})',
            section=section, field=field, category='invalid_price_snapshot', counts=1,
        ) from exc


def remap_learning_data(value, mapping, *, section='material_learning_logs', field='calculation_data', historical_mapping=None):
    if value is None:
        return None
    try:
        data = json.loads(value)
        if not isinstance(data, dict) or set(data) - {'error', 'treatments_count', 'total_weight_score', 'unit_weight_value', 'dist_log', 'usage_updates', 'learning_updates'}:
            raise ValueError
        for sub_field in ('dist_log', 'usage_updates'):
            if sub_field in data:
                if not isinstance(data[sub_field], list):
                    raise ValueError
                for entry in data[sub_field]:
                    if not isinstance(entry, dict) or 'treatment_id' not in entry:
                        raise ValueError
                    entry['treatment_id'] = _mapped(mapping, 'treatments', entry['treatment_id'], section=section, field=f'{field}.{sub_field}.treatment_id', historical_mapping=historical_mapping)
        if 'learning_updates' in data:
            if not isinstance(data['learning_updates'], dict):
                raise ValueError
            updates = {}
            for key, entry in data['learning_updates'].items():
                new_id = _mapped(mapping, 'procedures', int(key), section=section, field=f'{field}.learning_updates.procedure_id')
                updates[str(new_id)] = entry
            data['learning_updates'] = updates
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    except (ValueError, TypeError) as exc:
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError(
            f'سجل تعلم المواد غير صالح ({section}.{field})',
            section=section, field=field, category='invalid_learning_data', counts=1,
        ) from exc


def _validate_section_rows(rows, validator_fn, section_name):
    first_error = None
    violation_counts = {}
    for row in rows:
        try:
            validator_fn(row)
        except ArchiveError as exc:
            key = (exc.field, exc.referenced_section, exc.category, str(exc))
            violation_counts[key] = violation_counts.get(key, 0) + 1
            if first_error is None:
                first_error = exc
    if first_error is not None:
        key = (first_error.field, first_error.referenced_section, first_error.category, str(first_error))
        total_counts = violation_counts[key]
        raise ArchiveError(
            str(first_error),
            section=section_name,
            field=first_error.field,
            referenced_section=first_error.referenced_section,
            category=first_error.category,
            counts=total_counts,
        )


def validate_embedded_references(data, *, tenant_id, external_ids=None):
    """Fail before deletion if any known serialized reference is unresolved."""
    mapping = {name: {row['id']: row['id'] for row in rows} for name, rows in data.items()}
    mapping['users'] = mapping['staff_references']
    mapping['tenants'] = {tenant_id: tenant_id}
    for name, ids in (external_ids or {}).items():
        mapping.setdefault(name, {}).update({value: value for value in ids})

    contexts = deleted_treatment_contexts(data)
    historical = {value: value for value in historical_treatment_ids(contexts)}

    _validate_section_rows(
        data.get('clinical_events', []),
        lambda row: remap_event_payload(
            row.get('payload'), mapping, section='clinical_events', field_prefix='payload',
            historical_mapping={value: value for value in contexts.get((row.get('patient_id'), row.get('work_item_id')), ())},
        ),
        'clinical_events',
    )
    _validate_section_rows(
        data.get('stock_movements', []),
        lambda row: remap_stock_reference(row.get('reference_id'), mapping, section='stock_movements', field='reference_id', historical_mapping=historical),
        'stock_movements',
    )
    _validate_section_rows(
        data.get('material_learning_logs', []),
        lambda row: remap_learning_data(row.get('calculation_data'), mapping, section='material_learning_logs', field='calculation_data', historical_mapping=historical),
        'material_learning_logs',
    )
    def _validate_treatment(row):
        remap_treatment_note(row.get('notes'), mapping, section='treatments', field='notes')
        remap_price_snapshot(row.get('price_snapshot'), mapping, section='treatments', field='price_snapshot')

    _validate_section_rows(
        data.get('treatments', []),
        _validate_treatment,
        'treatments',
    )
