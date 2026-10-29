"""A deleted catalogue entry must not make immutable learning history unrestorable."""
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend import models
from backend.crud.procedure import delete_procedure
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive import encode_archive
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_embedded_refs import remap_learning_data, validate_embedded_references
from backend.services.tenant_archive_registry import validate_archive_references
from backend.services.tenant_restore_preview import create_restore_preview


@pytest.mark.asyncio
async def test_export_and_preview_preserve_learning_snapshot_after_real_procedure_deletion(
    async_db_session, test_user,
):
    db = async_db_session
    tenant_id = test_user.tenant_id
    procedure = models.Procedure(tenant_id=tenant_id, name='Historical crown', price=Decimal('100'))
    material = models.Material(tenant_id=tenant_id, name='Historical cement', type='DIVISIBLE', base_unit='g',
                               standard_price=Decimal('0'))
    warehouse = models.Warehouse(tenant_id=tenant_id, name='History warehouse')
    db.add_all([procedure, material, warehouse])
    await db.flush()
    old_id = procedure.id
    batch = models.Batch(tenant_id=tenant_id, material_id=material.id, batch_number='history',
                         expiry_date=date(2030, 1, 1), cost_per_unit=Decimal('2.50'))
    db.add(batch)
    await db.flush()
    stock = models.StockItem(tenant_id=tenant_id, warehouse_id=warehouse.id, batch_id=batch.id, quantity=0)
    db.add(stock)
    await db.flush()
    session = models.MaterialSession(tenant_id=tenant_id, stock_item_id=stock.id, status='CLOSED')
    db.add(session)
    await db.flush()
    snapshot = {'treatments_count': 1, 'total_weight_score': 1, 'unit_weight_value': 0.5,
                'dist_log': [], 'usage_updates': [],
                'learning_updates': {str(old_id): {'old': 0.25, 'observed': 0.5, 'new': 0.325}}}
    db.add_all([
        models.ProcedureMaterialWeight(tenant_id=tenant_id, procedure_id=old_id,
                                       material_id=material.id, weight=1),
        models.MaterialLearningLog(tenant_id=tenant_id, session_id=session.id,
                                  material_id=material.id, total_consumed=0.5,
                                  calculation_data=json.dumps(snapshot)),
    ])
    await db.commit()
    assert await delete_procedure(db, old_id, tenant_id) is not None
    assert not (await db.execute(select(models.Procedure.id).where(
        models.Procedure.tenant_id == tenant_id, models.Procedure.id == old_id,
    ))).first()
    assert not (await db.execute(select(models.ProcedureMaterialWeight.id).where(
        models.ProcedureMaterialWeight.tenant_id == tenant_id,
    ))).first()

    payload = await export_clinic_archive_data(db, tenant_id)
    assert payload['data']['procedures'] == []
    assert json.loads(payload['data']['material_learning_logs'][0]['calculation_data']) == snapshot
    archive = encode_archive(payload, tenant_id=tenant_id, installation_id='learning-history',
                             schema_revision='e2b3c4d5e6f7', key_id='test', key=b'l' * 32)
    operation, _, _, counts, _ = await create_restore_preview(
        db, tenant_id=tenant_id, actor_id=test_user.id, archive=archive,
        installation_id='learning-history', keys={'test': b'l' * 32},
        supported_revisions={'e2b3c4d5e6f7'}, max_bytes=1000000,
    )
    assert operation.status == 'previewed'
    assert counts['material_learning_logs'] == 1 and counts['procedures'] == 0


def _learning_data(updates):
    return {'staff_references': [], 'procedures': [{'id': 1, 'tenant_id': 7}],
            'material_learning_logs': [{'id': 1, 'tenant_id': 7,
                                       'calculation_data': json.dumps({'learning_updates': updates})}]}


def test_historical_learning_keys_never_authorize_live_sql_references():
    data = _learning_data({'9': {'old': 0, 'observed': 0.5, 'new': 0.5}})
    validate_embedded_references(data, tenant_id=7)
    data['procedure_material_weights'] = [{'id': 2, 'tenant_id': 7, 'procedure_id': 9}]
    with pytest.raises(ArchiveError) as exc:
        validate_archive_references(data, tenant_id=7)
    assert exc.value.section == 'procedure_material_weights'
    assert exc.value.field == 'procedure_id' and exc.value.category == 'invalid_reference'


@pytest.mark.parametrize('key', ['0', '-1', '01', '+1', '1.0', '1e2', 'true', ' 1', '2147483648'])
def test_learning_history_rejects_invalid_procedure_keys(key):
    with pytest.raises(ArchiveError) as exc:
        validate_embedded_references(_learning_data({key: {'old': 0, 'observed': 1, 'new': 1}}), tenant_id=7)
    assert exc.value.section == 'material_learning_logs'
    assert exc.value.field == 'calculation_data.learning_updates'
    assert exc.value.category == 'invalid_learning_data'


@pytest.mark.parametrize('entry', [None, [], {}, {'old': 0, 'new': 1},
    {'old': 0, 'observed': 1, 'new': 1, 'patient_id': 9},
    {'old': False, 'observed': 1, 'new': 1}, {'old': 'NaN', 'observed': 1, 'new': 1},
    {'old': float('inf'), 'observed': 1, 'new': 1}, {'old': [], 'observed': 1, 'new': 1},
])
def test_learning_history_rejects_malformed_snapshots(entry):
    with pytest.raises(ArchiveError) as exc:
        validate_embedded_references(_learning_data({'9': entry}), tenant_id=7)
    assert exc.value.category == 'invalid_learning_data'


def test_remapping_requires_explicit_history_mapping_and_preserves_live_and_global_entries():
    snapshot = {'learning_updates': {str(key): {'old': 0, 'observed': key, 'new': key} for key in (1, 2, 9)}}
    live = {'procedures': {1: 101, 2: 2}}
    with pytest.raises(ArchiveError):
        remap_learning_data(json.dumps(snapshot), live)
    result = json.loads(remap_learning_data(json.dumps(snapshot), live, historical_procedure_mapping={9: 109}))
    assert result['learning_updates'] == {'101': snapshot['learning_updates']['1'],
                                         '2': snapshot['learning_updates']['2'],
                                         '109': snapshot['learning_updates']['9']}
