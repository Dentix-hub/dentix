"""Recognize treatment history left by the supported hard-delete workflow.

A cancellation event is historical evidence, not a live foreign key. Only a
matching deletion event permits an absent treatment in serialized history;
SQL foreign keys and all other unresolved references remain fail-closed.
"""


def deleted_treatment_contexts(data: dict) -> dict[tuple[int, int], set[int]]:
    """Return absent treatment IDs witnessed by a same-patient/work-item delete."""
    live = {row['id'] for row in data.get('treatments', [])}
    patients = {row['id']: row for row in data.get('patients', [])}
    items = {row['id']: row for row in data.get('clinical_work_items', [])}
    contexts = {}
    for event in data.get('clinical_events', []):
        payload = event.get('payload')
        if not isinstance(payload, dict) or event.get('event_type') != 'procedure_cancelled':
            continue
        if not (
            payload.get('action') == 'deleted'
            and payload.get('superseded') is True
            and payload.get('status') == 'cancelled'
        ):
            continue
        patient = patients.get(event.get('patient_id'))
        item = items.get(event.get('work_item_id'))
        if not patient or not item or item.get('kind') != 'procedure':
            continue
        if item.get('patient_id') != patient['id'] or not (
            event.get('tenant_id') == item.get('tenant_id') == patient.get('tenant_id')
        ):
            continue
        for field in ('treatment_id', 'legacy_treatment_id'):
            value = payload.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0 and value not in live:
                contexts.setdefault((patient['id'], item['id']), set()).add(value)
    return contexts


def historical_treatment_ids(contexts: dict[tuple[int, int], set[int]]) -> set[int]:
    return set().union(*contexts.values()) if contexts else set()
