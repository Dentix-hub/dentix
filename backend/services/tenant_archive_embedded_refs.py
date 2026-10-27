"""Validate and remap business IDs stored in version-one structured fields."""
import json
import re

from backend.services.tenant_archive import ArchiveError

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


def _mapped(mapping, table, old_id):
    if not isinstance(old_id, int) or isinstance(old_id, bool) or old_id not in mapping.get(table, {}):
        raise ArchiveError('تحتوي النسخة الاحتياطية على مرجع غير صالح')
    return mapping[table][old_id]


def remap_event_payload(payload, mapping):
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ArchiveError('بيانات الحدث السريري غير صالحة')
    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, item in value.items():
            if key in EVENT_IDS and item is not None:
                result[key] = _mapped(mapping, EVENT_IDS[key], item)
            elif key == 'bulk_work_item_ids':
                if not isinstance(item, list):
                    raise ArchiveError('بيانات الحدث السريري غير صالحة')
                result[key] = [_mapped(mapping, 'clinical_work_items', entry) for entry in item]
            elif key.endswith(('_id', '_ids')) and key not in NON_DATABASE_IDS and item is not None:
                raise ArchiveError('مرجع الحدث السريري غير مدعوم')
            else:
                result[key] = visit(item)
        return result
    return visit(payload)


def remap_stock_reference(value, mapping):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ArchiveError('مرجع المخزون غير صالح')
    match = re.fullmatch(r'(REVERSE:)?(TREATMENT|TREATMENT_MATERIALS|CARE_SESSION):(\d+)', value)
    if match:
        prefix, kind, old_id = match.groups()
        return f'{prefix or ""}{kind}:{_mapped(mapping, REFERENCE_PREFIXES[kind], int(old_id))}'
    # Unknown references cannot be safely rebound to regenerated IDs.
    raise ArchiveError('مرجع المخزون غير مدعوم في النسخة الاحتياطية')


def remap_treatment_note(value, mapping):
    if value is None:
        return None
    match = re.fullmatch(r'Link:LabOrder:(\d+)', value)
    if match:
        return f'Link:LabOrder:{_mapped(mapping, "lab_orders", int(match.group(1)))}'
    return value


def remap_price_snapshot(value, mapping):
    if value is None:
        return None
    try:
        snapshot = json.loads(value)
        if not isinstance(snapshot, dict):
            raise ValueError
        if snapshot.get('list_id') is not None:
            snapshot['list_id'] = _mapped(mapping, 'price_lists', snapshot['list_id'])
        return json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))
    except (ValueError, TypeError) as exc:
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError('بيانات سعر العلاج غير صالحة') from exc


def validate_embedded_references(data, *, tenant_id, external_ids=None):
    """Fail before deletion if any known serialized reference is unresolved."""
    mapping = {name: {row['id']: row['id'] for row in rows} for name, rows in data.items()}
    mapping['users'] = mapping['staff_references']
    mapping['tenants'] = {tenant_id: tenant_id}
    for name, ids in (external_ids or {}).items():
        mapping.setdefault(name, {}).update({value: value for value in ids})
    for row in data['clinical_events']:
        remap_event_payload(row.get('payload'), mapping)
    for row in data['stock_movements']:
        remap_stock_reference(row.get('reference_id'), mapping)
    for row in data['treatments']:
        remap_treatment_note(row.get('notes'), mapping)
        remap_price_snapshot(row.get('price_snapshot'), mapping)
