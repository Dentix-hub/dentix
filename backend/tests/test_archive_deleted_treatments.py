"""Backups must retain the history produced by normal treatment deletion."""
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend import models
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.treatment_service import TreatmentService
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_embedded_refs import validate_embedded_references


def _history_data():
    return {
        'treatments': [], 'staff_references': [],
        'patients': [{'id': 1, 'tenant_id': 7}, {'id': 2, 'tenant_id': 7}],
        'clinical_work_items': [{'id': 3, 'tenant_id': 7, 'patient_id': 1, 'kind': 'procedure'}],
        'clinical_events': [
            {'id': 4, 'tenant_id': 7, 'patient_id': 1, 'work_item_id': 3,
             'event_type': 'procedure_recorded', 'payload': {'treatment_id': 9}},
            {'id': 5, 'tenant_id': 7, 'patient_id': 1, 'work_item_id': 3,
             'event_type': 'procedure_cancelled',
             'payload': {'treatment_id': 9, 'action': 'deleted', 'superseded': True, 'status': 'cancelled'}},
        ],
        'stock_movements': [], 'material_learning_logs': [],
    }


@pytest.mark.parametrize('mutation', ['no_deletion', 'unmapped', 'wrong_patient', 'wrong_tenant', 'unwitnessed_id', 'invalid_type'])
def test_history_does_not_allow_arbitrary_unresolved_references(mutation):
    data = _history_data()
    deleted = data['clinical_events'][1]
    if mutation == 'no_deletion':
        data['clinical_events'].pop()
    elif mutation == 'unmapped':
        deleted['payload']['action'] = 'unmapped'
    elif mutation == 'wrong_patient':
        deleted['patient_id'] = 2
    elif mutation == 'wrong_tenant':
        deleted['tenant_id'] = 8
    elif mutation == 'unwitnessed_id':
        data['clinical_events'][0]['payload']['treatment_id'] = 99
    else:
        data['clinical_events'][0]['payload']['treatment_id'] = True
    with pytest.raises(ArchiveError):
        validate_embedded_references(data, tenant_id=7)


def test_witnessed_history_is_preserved_without_weakening_live_foreign_keys():
    from backend.services.tenant_archive_registry import validate_archive_references
    data = _history_data()
    validate_embedded_references(data, tenant_id=7)
    data['clinical_charges'] = [{'id': 6, 'tenant_id': 7, 'legacy_treatment_id': 9}]
    with pytest.raises(ArchiveError) as exc:
        validate_archive_references(data, tenant_id=7)
    assert exc.value.section == 'clinical_charges'
    assert exc.value.field == 'legacy_treatment_id'


@pytest.mark.asyncio
async def test_export_after_real_treatment_deletion_keeps_clinical_history(
    async_db_session, test_user, test_patient,
):
    db = async_db_session
    user = (await db.execute(select(models.User).where(models.User.id == test_user.id))).scalar_one()
    treatment = models.Treatment(
        tenant_id=user.tenant_id, patient_id=test_patient.id, doctor_id=user.id,
        tooth_number=16, procedure='Crown', cost=Decimal('123.45'), discount=Decimal('1.25'),
    )
    db.add(treatment)
    await db.flush()
    treatment_id = treatment.id
    service = TreatmentService(db, user.tenant_id, user)
    work_item = await service._sync_clinical_work_item(treatment)
    assert work_item is not None
    await db.commit()

    await service.delete_treatment(treatment_id)
    assert (await db.execute(select(models.Treatment.id).where(
        models.Treatment.tenant_id == user.tenant_id, models.Treatment.id == treatment_id,
    ))).first() is None

    payload = await export_clinic_archive_data(db, user.tenant_id)
    assert payload['data']['treatments'] == []
    events = payload['data']['clinical_events']
    assert len(events) == 2
    assert {event['payload']['treatment_id'] for event in events} == {treatment_id}
    assert any(event['payload'].get('action') == 'deleted' for event in events)

    # The existing JSON download and its adapter retain the same history.
    from backend.services.export_service import export_tenant_data
    from backend.services.tenant_archive_legacy import adapt_legacy_json
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_restore_preview import create_restore_preview
    legacy = adapt_legacy_json(await export_tenant_data(db, user.tenant_id), tenant_id=user.tenant_id)
    archive = encode_archive(legacy, tenant_id=user.tenant_id, installation_id='history-test',
                             schema_revision='e2b3c4d5e6f7', key_id='test', key=b'h' * 32)
    operation, _, _, counts, _ = await create_restore_preview(
        db, tenant_id=user.tenant_id, actor_id=user.id, archive=archive,
        installation_id='history-test', keys={'test': b'h' * 32},
        supported_revisions={'e2b3c4d5e6f7'}, max_bytes=1000000,
    )
    assert operation.status == 'previewed' and counts['clinical_events'] == 2
    assert counts['treatments'] == 0


def test_disclosed_unresolved_completed_history_is_explicit_and_non_mutating():
    from copy import deepcopy
    from backend.services.tenant_archive_history import disclose_unresolved_treatment_history
    source = _history_data()
    source['clinical_events'] = source['clinical_events'][:1]
    source['clinical_work_items'][0].update(status='completed', code='PROS_CROWN')
    source['clinical_events'][0]['payload'].update(kind='procedure', canonical_code='PROS_CROWN')
    exported = deepcopy(source)
    with pytest.raises(ArchiveError):
        validate_embedded_references(exported, tenant_id=7)
    disclose_unresolved_treatment_history(exported)
    validate_embedded_references(exported, tenant_id=7)
    assert exported['clinical_events'][0]['payload']['archive_reference_state'] == 'unresolved_legacy_treatment'
    assert 'archive_reference_state' not in source['clinical_events'][0]['payload']
    assert exported['treatments'] == []


@pytest.mark.parametrize('mutation', ['wrong_patient', 'wrong_tenant', 'wrong_code', 'active', 'boolean_id'])
def test_disclosure_does_not_authorize_unrelated_history(mutation):
    from backend.services.tenant_archive_history import disclose_unresolved_treatment_history
    data = _history_data()
    data['clinical_events'] = data['clinical_events'][:1]
    data['clinical_work_items'][0].update(status='completed', code='PROS_CROWN')
    data['clinical_events'][0]['payload'].update(kind='procedure', canonical_code='PROS_CROWN')
    data['clinical_events'][0]['payload']['archive_reference_state'] = 'unresolved_legacy_treatment'
    if mutation == 'wrong_patient':
        data['clinical_events'][0]['patient_id'] = 2
    elif mutation == 'wrong_tenant':
        data['clinical_events'][0]['tenant_id'] = 8
    elif mutation == 'wrong_code':
        data['clinical_events'][0]['payload']['canonical_code'] = 'OTHER'
    elif mutation == 'active':
        data['clinical_work_items'][0]['status'] = 'active'
    else:
        data['clinical_events'][0]['payload']['treatment_id'] = True
    disclose_unresolved_treatment_history(data)
    with pytest.raises(ArchiveError):
        validate_embedded_references(data, tenant_id=7)
