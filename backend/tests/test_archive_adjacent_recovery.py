"""Real workflow regressions for the adjacent archive-reference failures."""
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_embedded_refs import validate_embedded_references
from backend.services.treatment_service import TreatmentService


@pytest.mark.asyncio
async def test_real_session_start_exports_and_previews(async_db_session, test_user, test_patient):
    from backend.services.care_session_service import CareSessionService
    from backend.tests.services.test_care_session_service import set_native_writes_flag
    db = async_db_session
    user = (await db.execute(select(models.User).where(models.User.id == test_user.id))).scalar_one()
    await set_native_writes_flag(db, user.tenant_id, True)
    started = await CareSessionService(db, user.tenant_id, user).start_session(
        test_patient.id, schemas.CareSessionCreate())
    assert started.id is not None
    payload = await export_clinic_archive_data(db, user.tenant_id)
    assert len(payload['data']['care_sessions']) == 1
    assert payload['data']['clinical_events'][0]['payload']['session_id'] == started.id
    await _preview(db, user.tenant_id, user.id, payload)



@pytest.mark.asyncio
async def test_unprojected_treatment_deletion_preserves_stock_and_learning_history(
    async_db_session, test_user, test_patient,
):
    db = async_db_session
    user = (await db.execute(select(models.User).where(models.User.id == test_user.id))).scalar_one()
    tid = user.tenant_id
    treatment = models.Treatment(tenant_id=tid, patient_id=test_patient.id, doctor_id=user.id,
        tooth_number=16, procedure='Legacy custom procedure with no canonical mapping',
        cost=Decimal('100'), discount=Decimal('0'))
    material = models.Material(tenant_id=tid, name='Probe cement', type='DIVISIBLE', base_unit='g',
                               standard_price=Decimal('1'))
    warehouse = models.Warehouse(tenant_id=tid, name='Probe warehouse')
    db.add_all([treatment, material, warehouse])
    await db.flush()
    old_id = treatment.id
    batch = models.Batch(tenant_id=tid, material_id=material.id, batch_number='probe',
                         expiry_date=date(2030, 1, 1), cost_per_unit=Decimal('1'))
    db.add(batch)
    await db.flush()
    stock = models.StockItem(tenant_id=tid, warehouse_id=warehouse.id, batch_id=batch.id, quantity=9)
    db.add(stock)
    await db.flush()
    session = models.MaterialSession(tenant_id=tid, stock_item_id=stock.id, status='CLOSED')
    db.add(session)
    await db.flush()
    db.add_all([
        models.StockMovement(tenant_id=tid, stock_item_id=stock.id, change_amount=-1,
            reason='use', reference_id=f'TREATMENT:{old_id}', performed_by=user.id),
        models.MaterialLearningLog(tenant_id=tid, session_id=session.id, material_id=material.id,
            total_consumed=1, calculation_data=json.dumps({'treatments_count': 1,
                'total_weight_score': 1, 'unit_weight_value': 1,
                'dist_log': [{'treatment_id': old_id, 'procedure': treatment.procedure, 'weight': 1}],
                'usage_updates': [], 'learning_updates': {}})),
    ])
    service = TreatmentService(db, tid, user)
    assert await service._sync_clinical_work_item(treatment) is None
    await db.commit()
    await service.delete_treatment(old_id)
    payload = await export_clinic_archive_data(db, tid)
    assert not payload['data']['treatments'] and not payload['data']['clinical_events']
    movements = payload['data']['stock_movements']
    assert len(movements) == 2 and sum(row['change_amount'] for row in movements) == 0
    assert payload['data']['stock_items'][0]['quantity'] == 10
    assert json.loads(payload['data']['material_learning_logs'][0]['calculation_data'])['dist_log'][0]['treatment_id'] == old_id
    await _preview(db, tid, user.id, payload)
    # A complete closed-session calculation independently retains its history
    # when the treatment had no stock movements.
    payload['data']['stock_movements'] = []
    validate_embedded_references(payload['data'], tenant_id=tid)



@pytest.mark.parametrize('path', ['service', 'router', 'legacy', 'rollback'])
@pytest.mark.asyncio
async def test_lab_delete_preserves_restorable_events(
    async_db_session, test_user, test_patient, path, monkeypatch,
):
    from backend.services.lab_service import LabService
    db = async_db_session
    user = (await db.execute(select(models.User).where(models.User.id == test_user.id))).scalar_one()
    tid = user.tenant_id
    lab = models.Laboratory(tenant_id=tid, name='Probe laboratory')
    db.add(lab)
    await db.flush()
    order = models.LabOrder(tenant_id=tid, patient_id=test_patient.id, laboratory_id=lab.id,
        work_type='Crown', cost=Decimal('20'), price_to_patient=Decimal('100'), doctor_id=user.id)
    db.add(order)
    await db.flush()
    treatment = models.Treatment(tenant_id=tid, patient_id=test_patient.id, doctor_id=user.id,
        tooth_number=16, procedure='Crown', cost=Decimal('100'), discount=Decimal('0'),
        notes=f'Link:LabOrder:{order.id}')
    db.add(treatment)
    await db.flush()
    assert await TreatmentService(db, tid, user)._sync_clinical_work_item(treatment) is not None
    await db.commit()
    if path == 'rollback':
        order_id, treatment_id = order.id, treatment.id
        original_delete = db.delete
        async def fail_order_delete(row):
            if isinstance(row, models.LabOrder):
                raise RuntimeError('synthetic failure after treatment deletion')
            await original_delete(row)
        monkeypatch.setattr(db, 'delete', fail_order_delete)
        with pytest.raises(RuntimeError, match='synthetic failure'):
            await LabService(db, tid).delete_lab_order(order_id, current_user=user)
        await db.rollback()
        assert (await db.execute(select(models.LabOrder.id).where(
            models.LabOrder.tenant_id == tid, models.LabOrder.id == order_id))).scalar_one() == order_id
        assert (await db.execute(select(models.Treatment.id).where(
            models.Treatment.tenant_id == tid, models.Treatment.id == treatment_id))).scalar_one() == treatment_id
        events = (await db.execute(select(models.ClinicalEvent).where(models.ClinicalEvent.tenant_id == tid))).scalars().all()
        assert len(events) == 1 and events[0].event_type == 'procedure_recorded'
        await _preview(db, tid, test_user.id, await export_clinic_archive_data(db, tid))
        return
    if path == 'legacy':
        # Pre-fix data has only the original, generated lab provenance.
        await db.delete(treatment)
        await db.delete(order)
        await db.commit()
    elif path == 'router':
        from backend.routers.laboratories import delete_lab_order
        await delete_lab_order(order.id, db=db, current_user=user)
    else:
        assert await LabService(db, tid).delete_lab_order(order.id)
    payload = await export_clinic_archive_data(db, tid)
    assert payload['data']['treatments'] == [] and payload['data']['lab_orders'] == []
    events = payload['data']['clinical_events']
    assert len(events) == (1 if path == 'legacy' else 2)
    if path != 'legacy':
        assert events[-1]['payload']['action'] == 'deleted'
    await _preview(db, tid, user.id, payload)


async def _preview(db, tenant_id, actor_id, payload):
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_restore_preview import create_restore_preview
    archive = encode_archive(payload, tenant_id=tenant_id, installation_id='adjacent-regression',
                             schema_revision='e2b3c4d5e6f7', key_id='test', key=b'a' * 32)
    operation, _, _, _, _ = await create_restore_preview(
        db, tenant_id=tenant_id, actor_id=actor_id, archive=archive,
        installation_id='adjacent-regression', keys={'test': b'a' * 32},
        supported_revisions={'e2b3c4d5e6f7'}, max_bytes=1000000)
    assert operation.status == 'previewed'


def test_session_event_references_remap_nested_materials_and_usage_lists():
    from backend.services.tenant_archive_embedded_refs import remap_event_payload
    mapping = {name: {1: new_id} for name, new_id in {
        'care_sessions': 101, 'appointments': 201, 'users': 301, 'clinical_work_items': 401,
        'care_session_steps': 501, 'care_observations': 601, 'next_visit_requests': 701,
        'materials': 801, 'treatment_material_usages': 901,
    }.items()}
    payload = {'session_id': 1, 'appointment_id': 1, 'provider_user_id': 1,
        'resume_work_item_id': 1, 'resume_from_session_id': 1, 'step_id': 1,
        'observation_id': 1, 'request_id': 1, 'doctor_id': 1,
        'usage_ids': [1], 'items': [{'material_id': 1, 'quantity': 2}],
        'canal_id': 'MB1', 'root_id': 'MB', 'version_id': 1}
    assert remap_event_payload(payload, mapping) == {
        'session_id': 101, 'appointment_id': 201, 'provider_user_id': 301,
        'resume_work_item_id': 401, 'resume_from_session_id': 101, 'step_id': 501,
        'observation_id': 601, 'request_id': 701, 'doctor_id': 301,
        'usage_ids': [901], 'items': [{'material_id': 801, 'quantity': 2}],
        'canal_id': 'MB1', 'root_id': 'MB', 'version_id': 1}
    for invalid in ({'usage_ids': True}, {'usage_ids': [True]}, {'usage_ids': [999]},
                    {'session_id': 999}, {'unknown_id': 1}, {'items': [{'material_id': 999}]}):
        with pytest.raises(ArchiveError):
            remap_event_payload(invalid, mapping)


def test_appointment_tokens_preserve_text_and_reject_missing_or_wrong_patient():
    from backend.services.tenant_archive_embedded_refs import remap_next_visit_note
    assert remap_next_visit_note('متابعة [APPOINTMENT:1] ثم [APPOINTMENT:2] 123',
                                {'appointments': {1: 101, 2: 202}}) == 'متابعة [APPOINTMENT:101] ثم [APPOINTMENT:202] 123'
    data = {'staff_references': [], 'appointments': [{'id': 1, 'tenant_id': 7, 'patient_id': 2}],
            'next_visit_requests': [{'id': 3, 'tenant_id': 7, 'patient_id': 1, 'notes': '[APPOINTMENT:1]'}]}
    with pytest.raises(ArchiveError) as exc:
        validate_embedded_references(data, tenant_id=7)
    assert exc.value.section == 'next_visit_requests' and exc.value.field == 'notes'
    data['appointments'] = []
    with pytest.raises(ArchiveError):
        validate_embedded_references(data, tenant_id=7)


def _reversed_history():
    return {'staff_references': [], 'treatments': [],
        'stock_items': [{'id': 1, 'tenant_id': 7}],
        'stock_movements': [
            {'id': 2, 'tenant_id': 7, 'stock_item_id': 1, 'reference_id': 'TREATMENT:9',
             'change_amount': -2, 'reason': 'use'},
            {'id': 3, 'tenant_id': 7, 'stock_item_id': 1, 'reference_id': 'REVERSE:TREATMENT:9',
             'change_amount': 2, 'reason': 'REVERSAL'}]}


@pytest.mark.parametrize('mutation', ['partial', 'wrong_tenant', 'wrong_stock', 'wrong_reason', 'missing_source'])
def test_only_complete_same_clinic_stock_reversals_authorize_inventory_history(mutation):
    data = _reversed_history()
    validate_embedded_references(data, tenant_id=7)
    if mutation == 'partial':
        data['stock_movements'][1]['change_amount'] = 1
    elif mutation == 'wrong_tenant':
        data['stock_movements'][1]['tenant_id'] = 8
    elif mutation == 'wrong_stock':
        data['stock_movements'][1]['stock_item_id'] = 99
    elif mutation == 'wrong_reason':
        data['stock_movements'][1]['reason'] = 'use'
    else:
        data['stock_movements'].pop(0)
    with pytest.raises(ArchiveError):
        validate_embedded_references(data, tenant_id=7)


def test_inventory_history_cannot_authorize_clinical_or_live_foreign_keys():
    from backend.services.tenant_archive_registry import validate_archive_references
    data = _reversed_history()
    data['clinical_events'] = [{'id': 4, 'patient_id': 1, 'work_item_id': 2, 'payload': {'treatment_id': 9}}]
    with pytest.raises(ArchiveError) as exc:
        validate_embedded_references(data, tenant_id=7)
    assert exc.value.section == 'clinical_events'
    data['clinical_events'] = []
    data['treatment_sessions'] = [{'id': 5, 'tenant_id': 7, 'treatment_id': 9}]
    with pytest.raises(ArchiveError) as exc:
        validate_archive_references(data, tenant_id=7)
    assert exc.value.section == 'treatment_sessions'


@pytest.mark.parametrize('mutation', ['wrong_patient', 'wrong_tenant', 'wrong_note', 'wrong_code'])
def test_legacy_lab_history_requires_matching_generated_provenance(mutation):
    data = {'staff_references': [], 'patients': [{'id': 1, 'tenant_id': 7}],
        'clinical_work_items': [{'id': 2, 'tenant_id': 7, 'patient_id': 1, 'kind': 'procedure',
                                 'code': 'CROWN', 'notes': 'Link:LabOrder:8'}],
        'clinical_events': [{'id': 3, 'tenant_id': 7, 'patient_id': 1, 'work_item_id': 2,
            'event_type': 'procedure_recorded', 'notes': 'Link:LabOrder:8',
            'payload': {'treatment_id': 9, 'kind': 'procedure', 'canonical_code': 'CROWN'}}]}
    validate_embedded_references(data, tenant_id=7)
    event = data['clinical_events'][0]
    if mutation == 'wrong_patient':
        event['patient_id'] = 99
    elif mutation == 'wrong_tenant':
        event['tenant_id'] = 8
    elif mutation == 'wrong_note':
        event['notes'] = 'Link:LabOrder:88'
    else:
        event['payload']['canonical_code'] = 'OTHER'
    with pytest.raises(ArchiveError):
        validate_embedded_references(data, tenant_id=7)


@pytest.mark.parametrize('mutation', ['active', 'wrong_material', 'wrong_tenant', 'incomplete', 'invalid_weight', 'foreign_usage'])
def test_learning_history_requires_complete_closed_same_clinic_snapshot(mutation):
    snapshot = {'treatments_count': 1, 'total_weight_score': 1, 'unit_weight_value': 1,
                'dist_log': [{'treatment_id': 9, 'procedure': 'Legacy', 'weight': 1}],
                'usage_updates': [], 'learning_updates': {}}
    data = {'staff_references': [], 'treatments': [], 'stock_movements': [],
        'stock_items': [{'id': 1, 'tenant_id': 7, 'batch_id': 2}],
        'batches': [{'id': 2, 'tenant_id': 7, 'material_id': 3}],
        'materials': [{'id': 3, 'tenant_id': 7}],
        'material_sessions': [{'id': 4, 'tenant_id': 7, 'stock_item_id': 1, 'status': 'CLOSED'}],
        'material_learning_logs': [{'id': 5, 'tenant_id': 7, 'session_id': 4,
                                   'material_id': 3, 'total_consumed': 1, 'calculation_data': json.dumps(snapshot)}]}
    validate_embedded_references(data, tenant_id=7)
    if mutation == 'active':
        data['material_sessions'][0]['status'] = 'ACTIVE'
    elif mutation == 'wrong_material':
        data['batches'][0]['material_id'] = 99
    elif mutation == 'wrong_tenant':
        data['materials'][0]['tenant_id'] = 8
    elif mutation == 'incomplete':
        snapshot.pop('unit_weight_value')
    elif mutation == 'invalid_weight':
        snapshot['dist_log'][0]['weight'] = -1
    else:
        snapshot['usage_updates'] = [{'treatment_id': 99, 'quantity': 1, 'cost': 1}]
    data['material_learning_logs'][0]['calculation_data'] = json.dumps(snapshot)
    with pytest.raises(ArchiveError):
        validate_embedded_references(data, tenant_id=7)
