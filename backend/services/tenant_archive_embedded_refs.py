"""Validate and remap business IDs stored in version-one structured fields."""
import json
import math
import re

from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_history import deleted_treatment_contexts, historical_treatment_ids, inventory_treatment_history

EVENT_IDS = {
    'treatment_id': 'treatments', 'legacy_treatment_id': 'treatments',
    'tooth_status_id': 'tooth_status', 'legacy_tooth_status_id': 'tooth_status',
    'work_item_id': 'clinical_work_items', 'original_work_item_id': 'clinical_work_items',
    'replacement_work_item_id': 'clinical_work_items', 'clinical_work_item_id': 'clinical_work_items',
    'patient_id': 'patients', 'charge_id': 'clinical_charges',
    'care_session_id': 'care_sessions', 'event_id': 'clinical_events',
    'price_list_id': 'price_lists', 'tenant_id': 'tenants',
    'actor_user_id': 'users', 'created_by_user_id': 'users', 'user_id': 'users',
    'session_id': 'care_sessions', 'appointment_id': 'appointments',
    'provider_user_id': 'users', 'doctor_id': 'users',
    'resume_work_item_id': 'clinical_work_items', 'resume_from_session_id': 'care_sessions',
    'step_id': 'care_session_steps', 'observation_id': 'care_observations',
    'request_id': 'next_visit_requests', 'material_id': 'materials',
    'original_observation_id': 'care_observations', 'replacement_observation_id': 'care_observations',
    'amends_session_id': 'care_sessions', 'superseded_by_id': 'care_observations',
    'reference_source_session_id': 'care_sessions', 'reference_source_observation_id': 'care_observations',
    'assigned_doctor_id': 'users',
    'stopped_by_user_id': 'users', 'postponed_by_user_id': 'users',
    'handoff_by_user_id': 'users', 'handoff_to_user_id': 'users',
    'author_user_id': 'users', 'performing_user_id': 'users',
}
EVENT_ID_LISTS = {'bulk_work_item_ids': 'clinical_work_items', 'work_item_ids': 'clinical_work_items', 'usage_ids': 'treatment_material_usages', 'associated_work_item_ids': 'clinical_work_items'}
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
            elif key in EVENT_ID_LISTS:
                if not isinstance(item, list):
                    raise ArchiveError(
                        f'بيانات الحدث السريري غير صالحة ({section}.{canonical_field})',
                        section=section, field=canonical_field, category='invalid_payload', counts=1,
                    )
                result[key] = [_mapped(mapping, EVENT_ID_LISTS[key], entry, section=section, field=canonical_field) for entry in item]
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


def remap_next_visit_note(value, mapping):
    """Rebind the scheduler's functional tokens, retaining all other note text."""
    if value is None:
        return None
    def replace(match):
        try:
            old_id = int(match.group(1))
        except ValueError as exc:
            raise ArchiveError('مرجع الموعد غير صالح', section='next_visit_requests', field='notes',
                               category='invalid_reference_type', counts=1) from exc
        new_id = _mapped(mapping, 'appointments', old_id, section='next_visit_requests', field='notes')
        return f'[APPOINTMENT:{new_id}]'
    return re.sub(r'\[APPOINTMENT:(\d+)\]', replace, value)


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


def learning_procedure_ids(value, *, section='material_learning_logs', field='calculation_data'):
    """Read catalogue IDs from immutable old/observed/new learning snapshots.

    Catalogue deletion intentionally retains these audit entries. They are not
    live weight rules or foreign keys and must never recreate a procedure.
    """
    if value is None:
        return set()
    try:
        data = json.loads(value)
        if not isinstance(data, dict):
            raise ValueError
        updates = data.get('learning_updates', {})
        if not isinstance(updates, dict):
            raise ValueError
        ids = set()
        for key, entry in updates.items():
            if not re.fullmatch(r'[1-9][0-9]{0,9}', key) or int(key) > 2147483647:
                raise ValueError
            if not isinstance(entry, dict) or set(entry) != {'old', 'observed', 'new'}:
                raise ValueError
            if any(isinstance(number, bool) or not isinstance(number, (int, float, str))
                   or not math.isfinite(float(number)) for number in entry.values()):
                raise ValueError
            ids.add(int(key))
        return ids
    except (ValueError, TypeError, OverflowError) as exc:
        raise ArchiveError(
            f'سجل تعلم المواد غير صالح ({section}.{field}.learning_updates)',
            section=section, field=f'{field}.learning_updates',
            category='invalid_learning_data', counts=1,
        ) from exc


def remap_learning_data(value, mapping, *, section='material_learning_logs', field='calculation_data',
                        historical_mapping=None, historical_procedure_mapping=None):
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
            learning_procedure_ids(value, section=section, field=field)
            procedures = {'procedures': {**(historical_procedure_mapping or {}), **mapping.get('procedures', {})}}
            updates = {}
            for key, entry in data['learning_updates'].items():
                new_id = _mapped(procedures, 'procedures', int(key), section=section, field=f'{field}.learning_updates.procedure_id')
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


DRAFT_PROC_KEY_REGEX = re.compile(r'^(proc_(?:notes|next_action|custom))_(\d+)(.*)$')


def remap_draft_payload(payload, mapping, *, section='care_session_drafts', field='draft_payload'):
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ArchiveError(
            f'بيانات المسودة غير صالحة ({section}.{field})',
            section=section, field=field, category='invalid_payload_type',
        )
    remapped = {}
    wi_map = mapping.get('clinical_work_items', {})
    for k, v in payload.items():
        m = DRAFT_PROC_KEY_REGEX.match(k)
        if m:
            prefix, old_id_str, suffix = m.group(1), m.group(2), m.group(3)
            old_id = int(old_id_str)
            if old_id in wi_map:
                new_id = wi_map[old_id]
                remapped[f"{prefix}_{new_id}{suffix}"] = v
            else:
                remapped[k] = v
        else:
            remapped[k] = v
    return remapped


def validate_embedded_references(data, *, tenant_id, external_ids=None):
    """Fail before deletion if any known serialized reference is unresolved."""
    mapping = {name: {row['id']: row['id'] for row in rows} for name, rows in data.items()}
    mapping['users'] = mapping['staff_references']
    mapping['tenants'] = {tenant_id: tenant_id}
    for name, ids in (external_ids or {}).items():
        mapping.setdefault(name, {}).update({value: value for value in ids})

    contexts = deleted_treatment_contexts(data)
    historical = {value: value for value in historical_treatment_ids(contexts) | inventory_treatment_history(data)}

    _validate_section_rows(
        data.get('care_session_drafts', []),
        lambda row: remap_draft_payload(row.get('draft_payload'), mapping),
        'care_session_drafts',
    )
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
        lambda row: remap_learning_data(
            row.get('calculation_data'), mapping, historical_mapping=historical,
            historical_procedure_mapping={value: value for value in learning_procedure_ids(row.get('calculation_data'))},
        ),
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
    appointments = {row['id']: row for row in data.get('appointments', [])}
    def validate_visit(row):
        remap_next_visit_note(row.get('notes'), mapping)
        for match in re.finditer(r'\[APPOINTMENT:(\d+)\]', row.get('notes') or ''):
            appointment = appointments[int(match.group(1))]
            if (appointment.get('patient_id'), appointment.get('tenant_id')) != (row.get('patient_id'), row.get('tenant_id')):
                raise ArchiveError('مرجع الموعد لا يخص المريض', section='next_visit_requests', field='notes',
                                   referenced_section='appointments', category='invalid_reference', counts=1)
    _validate_section_rows(data.get('next_visit_requests', []), validate_visit, 'next_visit_requests')
