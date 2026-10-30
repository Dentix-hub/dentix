"""Recognize bounded evidence for retained, non-operational treatment history.

SQL foreign keys and unrelated unresolved references remain fail-closed.
"""
import json
import math
import re

UNRESOLVED_HISTORY = 'unresolved_legacy_treatment'


def _is_completed_history(event, item, payload):
    return (
        event.get('event_type') in {'procedure_recorded', 'procedure_updated'}
        and item.get('status') == 'completed'
        and payload.get('kind') == 'procedure'
        and bool(item.get('code')) and payload.get('canonical_code') == item['code']
    )


def disclose_unresolved_treatment_history(data):
    """Annotate exported copies, never database rows or fabricated treatments.

    A completed same-patient procedure retains its legacy provenance even
    without a deletion witness. The marker explicitly discloses that the
    treatment cannot be resolved; it does not assert a legitimate deletion.
    """
    live = {row['id'] for row in data.get('treatments', [])}
    items = {row['id']: row for row in data.get('clinical_work_items', [])}
    patients = {row['id']: row for row in data.get('patients', [])}
    for event in data.get('clinical_events', []):
        item = items.get(event.get('work_item_id'))
        patient = patients.get(event.get('patient_id'))
        payload = event.get('payload')
        if not item or not patient or not isinstance(payload, dict):
            continue
        if not (event.get('tenant_id') == item.get('tenant_id') == patient.get('tenant_id')
                and item.get('patient_id') == patient['id'] and item.get('kind') == 'procedure'
                and _is_completed_history(event, item, payload)):
            continue
        refs = [payload[k] for k in ('treatment_id', 'legacy_treatment_id') if payload.get(k) is not None]
        if refs and all(isinstance(v, int) and not isinstance(v, bool) and 0 < v <= 2147483647 and v not in live for v in refs):
            event['payload'] = {**payload, 'archive_reference_state': UNRESOLVED_HISTORY}


def deleted_treatment_contexts(data: dict) -> dict[tuple[int, int], set[int]]:
    """Return absent treatment IDs witnessed by a same-patient/work-item delete."""
    live = {row['id'] for row in data.get('treatments', [])}
    patients = {row['id']: row for row in data.get('patients', [])}
    items = {row['id']: row for row in data.get('clinical_work_items', [])}
    contexts = {}
    for event in data.get('clinical_events', []):
        payload = event.get('payload')
        if not isinstance(payload, dict):
            continue
        patient = patients.get(event.get('patient_id'))
        item = items.get(event.get('work_item_id'))
        if not patient or not item or item.get('kind') != 'procedure':
            continue
        if item.get('patient_id') != patient['id'] or not (
            event.get('tenant_id') == item.get('tenant_id') == patient.get('tenant_id')
        ):
            continue
        explicit_deletion = (
            event.get('event_type') == 'procedure_cancelled'
            and payload.get('action') == 'deleted'
            and payload.get('superseded') is True and payload.get('status') == 'cancelled'
        )
        # Older lab deletion directly removed a generated treatment. Its event
        # and same-patient work item retain identical generated provenance.
        # The note is historical text here, not an operational lab-order link.
        lab_provenance = (
            event.get('event_type') in {'procedure_recorded', 'procedure_updated'}
            and payload.get('kind') == 'procedure'
            and payload.get('canonical_code') == item.get('code') and bool(item.get('code'))
            and isinstance(item.get('notes'), str)
            and re.fullmatch(r'Link:LabOrder:[1-9][0-9]*', item['notes']) is not None
            and event.get('notes') == item['notes']
        )
        disclosed_history = (
            payload.get('archive_reference_state') == UNRESOLVED_HISTORY
            and _is_completed_history(event, item, payload)
            and all(isinstance(value, int) and not isinstance(value, bool)
                    and 0 < value <= 2147483647 and value not in live
                    for value in (payload.get('treatment_id'), payload.get('legacy_treatment_id'))
                    if value is not None)
        )
        if not (explicit_deletion or lab_provenance or disclosed_history):
            continue
        for field in ('treatment_id', 'legacy_treatment_id'):
            value = payload.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0 and value not in live:
                contexts.setdefault((patient['id'], item['id']), set()).add(value)
    return contexts


def historical_treatment_ids(contexts: dict[tuple[int, int], set[int]]) -> set[int]:
    return set().union(*contexts.values()) if contexts else set()


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _finite(value, *, positive=False):
    number = _number(value)
    return number is not None and (number > 0 if positive else number >= 0)


def _positive_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value <= 2147483647


def inventory_treatment_history(data):
    """Recognize fully reversed stock and complete closed-session snapshots.

    Evidence here is usable only in stock/learning history, never to authorize
    clinical payloads or live SQL foreign keys. No live row is reconstructed.
    """
    live = {row['id'] for row in data.get('treatments', [])}
    stocks = {row['id']: row for row in data.get('stock_items', [])}
    groups = {}
    for row in data.get('stock_movements', []):
        reference = row.get('reference_id')
        match = re.fullmatch(r'(REVERSE:)?(TREATMENT|TREATMENT_MATERIALS):([1-9][0-9]{0,9})', reference) if isinstance(reference, str) else None
        if not match:
            continue
        reverse, kind, raw_id = match.groups()
        old_id = int(raw_id)
        if not _positive_id(old_id) or old_id in live:
            continue
        stock = stocks.get(row.get('stock_item_id'))
        key = (old_id, row.get('stock_item_id'), kind)
        group = groups.setdefault(key, {'valid': True, 'source': [], 'reverse': []})
        amount = _number(row.get('change_amount'))
        if not stock or row.get('tenant_id') != stock.get('tenant_id') or amount is None:
            group['valid'] = False
            continue
        if (reverse and (amount <= 0 or row.get('reason') != 'REVERSAL')) or (not reverse and amount >= 0):
            group['valid'] = False
        group['reverse' if reverse else 'source'].append(amount)
    eligible = {}
    for (old_id, _, _), group in groups.items():
        try:
            net = math.fsum(group['source'] + group['reverse'])
        except OverflowError:
            net = math.inf
        valid = (group['valid'] and bool(group['source']) and bool(group['reverse'])
                 and abs(net) <= 1e-9)
        eligible[old_id] = eligible.get(old_id, True) and valid
    historical = {old_id for old_id, valid in eligible.items() if valid}

    sessions = {row['id']: row for row in data.get('material_sessions', [])}
    batches = {row['id']: row for row in data.get('batches', [])}
    materials = {row['id']: row for row in data.get('materials', [])}
    for row in data.get('material_learning_logs', []):
        session = sessions.get(row.get('session_id'))
        stock = stocks.get(session.get('stock_item_id')) if session else None
        batch = batches.get(stock.get('batch_id')) if stock else None
        material = materials.get(row.get('material_id'))
        if not all((session, stock, batch, material)) or session.get('status') != 'CLOSED':
            continue
        if batch.get('material_id') != material['id'] or any(
            parent.get('tenant_id') != row.get('tenant_id') for parent in (session, stock, batch, material)
        ) or not _finite(row.get('total_consumed')):
            continue
        try:
            snapshot = json.loads(row.get('calculation_data') or '{}')
            if not isinstance(snapshot, dict) or not {'treatments_count', 'total_weight_score', 'unit_weight_value', 'dist_log', 'usage_updates', 'learning_updates'} <= snapshot.keys():
                continue
            count = snapshot['treatments_count']
            distribution, usages = snapshot['dist_log'], snapshot['usage_updates']
            if not _positive_id(count) or not isinstance(distribution, list) or not distribution or count < len(distribution):
                continue
            if not _finite(snapshot['total_weight_score'], positive=True) or not _finite(snapshot['unit_weight_value']):
                continue
            if any(not isinstance(entry, dict) or set(entry) != {'treatment_id', 'procedure', 'weight'}
                   or not _positive_id(entry['treatment_id']) or not isinstance(entry['procedure'], str)
                   or not entry['procedure'] or not _finite(entry['weight']) for entry in distribution):
                continue
            ids = {entry['treatment_id'] for entry in distribution}
            if len(ids) != len(distribution) or not isinstance(usages, list) or any(
                not isinstance(entry, dict) or set(entry) != {'treatment_id', 'quantity', 'cost'}
                or not _positive_id(entry['treatment_id']) or entry['treatment_id'] not in ids
                or not _finite(entry['quantity']) or not _finite(entry['cost']) for entry in usages
            ):
                continue
            historical.update(ids - live)
        except (ValueError, TypeError, OverflowError):
            continue
    return historical
