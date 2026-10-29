"""Synthetic PostgreSQL round trip for tenant business data and identities."""
import uuid
import json
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_identity import resolve_staff_mapping
from backend.services.tenant_archive_import import replace_clinic_business_data
from backend.services.tenant_archive_registry import validate_archive_references, validate_archive_sections, validate_archive_values


@pytest.mark.asyncio
async def test_deleted_treatment_history_survives_encrypted_restore_and_id_collisions():
    """Real deletion/export/preview/restore, including stock and learned history."""
    from datetime import date
    from backend.services.treatment_service import TreatmentService
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_restore_preview import create_restore_preview, confirm_restore_preview
    from backend.services.tenant_restore_coordinator import run_confirmed_restore
    from backend.services.clinical_charge_service import ClinicalChargeService
    from backend.services.tenant_archive_embedded_refs import validate_embedded_references
    from backend.services.tenant_backup_config import supported_archive_revisions

    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Deleted history clinic')
            other_tenant = models.Tenant(name='History isolation clinic')
            db.add_all([tenant, other_tenant])
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='history_' + suffix,
                               hashed_password='unchanged', role='admin', commission_percent=Decimal('17.25'))
            patient = models.Patient(tenant_id=tenant.id, name='Synthetic history', age=30, phone='0')
            other_patient = models.Patient(tenant_id=other_tenant.id, name='Other clinic', age=40, phone='0')
            warehouse = models.Warehouse(tenant_id=tenant.id, name='History warehouse')
            material = models.Material(tenant_id=tenant.id, name='History material', type='DIVISIBLE', base_unit='g')
            db.add_all([user, patient, other_patient, warehouse, material])
            await db.flush()
            treatment = models.Treatment(tenant_id=tenant.id, patient_id=patient.id, doctor_id=user.id,
                                         procedure='Crown', tooth_number=16, cost=Decimal('123.45'), discount=Decimal('1.25'))
            batch = models.Batch(tenant_id=tenant.id, material_id=material.id, batch_number='history',
                                 expiry_date=date(2030, 1, 1), cost_per_unit=Decimal('2.50'))
            db.add_all([treatment, batch])
            await db.flush()
            stock = models.StockItem(tenant_id=tenant.id, warehouse_id=warehouse.id, batch_id=batch.id, quantity=9)
            db.add(stock)
            await db.flush()
            material_session = models.MaterialSession(tenant_id=tenant.id, stock_item_id=stock.id,
                                                       patient_id=patient.id, doctor_id=user.id, remaining_est=8)
            db.add(material_session)
            await db.flush()
            db.add_all([
                models.StockMovement(tenant_id=tenant.id, stock_item_id=stock.id, change_amount=-1,
                                     reason='use', reference_id=f'TREATMENT:{treatment.id}', performed_by=user.id),
                models.MaterialLearningLog(tenant_id=tenant.id, session_id=material_session.id,
                    material_id=material.id, total_consumed=1,
                    calculation_data=json.dumps({'dist_log': [{'treatment_id': treatment.id, 'weight': 1}]})),
                models.Payment(tenant_id=tenant.id, patient_id=patient.id, doctor_id=user.id, amount=Decimal('23.45')),
            ])
            await db.commit()
            tenant_id, other_id, actor = tenant.id, other_tenant.id, user.id
            patient_id, other_patient_id, deleted_id = patient.id, other_patient.id, treatment.id

    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            user = (await db.execute(select(models.User).where(models.User.tenant_id == tenant_id, models.User.id == actor))).scalar_one()
            treatment = (await db.execute(select(models.Treatment).where(models.Treatment.tenant_id == tenant_id, models.Treatment.id == deleted_id))).scalar_one()
            service = TreatmentService(db, tenant_id, user)
            work_item = await service._sync_clinical_work_item(treatment)
            assert work_item is not None
            await db.commit()
            await service.delete_treatment(deleted_id)
            # A live treatment and its charge must still be restored normally.
            live = models.Treatment(tenant_id=tenant_id, patient_id=patient_id, doctor_id=actor,
                                    procedure='Crown', tooth_number=17, cost=Decimal('345.67'), discount=Decimal('2.34'))
            db.add(live)
            await db.flush()
            live_item = await service._sync_clinical_work_item(live)
            assert live_item is not None
            db.add(models.ClinicalCharge(tenant_id=tenant_id, patient_id=patient_id,
                work_item_id=live_item.id, doctor_id=actor, legacy_treatment_id=live.id,
                amount=Decimal('345.67'), discount=Decimal('2.34'), status='pending'))
            await db.commit()
            live_id = live.id
        clear_tenant_context(tenant_token=token)
        token = set_current_tenant_id(other_id)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=other_id)) as db:
            # Simulate an old installation's historical ID now naming another
            # clinic's live row. Never bind the restored history to that row.
            db.add(models.Treatment(id=deleted_id, tenant_id=other_id, patient_id=other_patient_id,
                procedure='Other clinic treatment', tooth_number=18, cost=Decimal('999.99'), discount=0))
            await db.commit()
        clear_tenant_context(tenant_token=token)
        token = set_current_tenant_id(tenant_id)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            payload = await export_clinic_archive_data(db, tenant_id)
            assert len(payload['data']['clinical_events']) == 3
            assert len(payload['data']['treatments']) == 1
            assert {row['id'] for row in payload['data']['treatments']} == {live_id}
            # Exercise unmodified old-format archive contents and repeat the
            # entire cycle: historical IDs must remain safe on later restores.
            for revision in ('bc78a10d932e', 'e2b3c4d5e6f7'):
                validate_embedded_references(payload['data'], tenant_id=tenant_id)
                archive = encode_archive(payload, tenant_id=tenant_id, installation_id='synthetic-history',
                                         schema_revision=revision, key_id='test', key=b'h' * 32)
                operation, confirmation, _, _, _ = await create_restore_preview(
                    db, tenant_id=tenant_id, actor_id=actor, archive=archive,
                    installation_id='synthetic-history', keys={'test': b'h' * 32},
                    supported_revisions=supported_archive_revisions('e2b3c4d5e6f7'), max_bytes=1000000)
                await confirm_restore_preview(db, tenant_id=tenant_id, actor_id=actor,
                    operation_id=operation.id, confirmation=confirmation, archive_digest=operation.archive_digest)
                _, mapping = await run_confirmed_restore(db, tenant_id=tenant_id, operation_id=operation.id,
                    installation_id='synthetic-history', keys={'test': b'h' * 32},
                    supported_revisions=supported_archive_revisions('e2b3c4d5e6f7'), max_bytes=1000000)
                historical_id = next(iter(mapping['historical_treatments'].values()))
                live_rows = (await db.execute(select(models.Treatment).where(models.Treatment.tenant_id == tenant_id))).scalars().all()
                assert len(live_rows) == 1
                assert live_rows[0].id != historical_id and historical_id != deleted_id
                assert live_rows[0].cost == Decimal('345.67') and live_rows[0].discount == Decimal('2.34')
                events = (await db.execute(select(models.ClinicalEvent).where(models.ClinicalEvent.tenant_id == tenant_id))).scalars().all()
                historical_events = [row for row in events if row.payload['treatment_id'] == historical_id]
                assert len(events) == 3 and len(historical_events) == 2
                assert {row.payload.get('action') for row in historical_events} == {None, 'deleted'}
                assert [row.payload['treatment_id'] for row in events if row not in historical_events] == [live_rows[0].id]
                assert await ClinicalChargeService(db, tenant_id).is_legacy_synced_work_item(historical_events[0].work_item_id)
                charge = (await db.execute(select(models.ClinicalCharge).where(models.ClinicalCharge.tenant_id == tenant_id))).scalar_one()
                assert charge.legacy_treatment_id == live_rows[0].id and charge.amount == Decimal('345.67')
                stock = (await db.execute(select(models.StockItem).where(models.StockItem.tenant_id == tenant_id))).scalar_one()
                movements = (await db.execute(select(models.StockMovement).where(models.StockMovement.tenant_id == tenant_id))).scalars().all()
                assert stock.quantity == 10
                assert {(row.change_amount, row.reference_id) for row in movements} == {
                    (-1, f'TREATMENT:{historical_id}'), (1, f'REVERSE:TREATMENT:{historical_id}')}
                log = (await db.execute(select(models.MaterialLearningLog).where(models.MaterialLearningLog.tenant_id == tenant_id))).scalar_one()
                assert json.loads(log.calculation_data)['dist_log'][0]['treatment_id'] == historical_id
                assert (await db.execute(select(models.Payment.amount).where(models.Payment.tenant_id == tenant_id))).scalar_one() == Decimal('23.45')
                restored_user = (await db.execute(select(models.User).where(
                    models.User.tenant_id == tenant_id, models.User.id == actor,
                ))).scalar_one()
                assert restored_user.hashed_password == 'unchanged' and restored_user.commission_percent == Decimal('17.25')
                # Future live creation cannot reuse the historical number.
                future = models.Treatment(tenant_id=tenant_id, patient_id=live_rows[0].patient_id,
                    procedure='Future treatment', tooth_number=18, cost=Decimal('0'), discount=0)
                db.add(future)
                await db.flush()
                assert future.id > historical_id
                await db.rollback()
                payload = await export_clinic_archive_data(db, tenant_id)
        clear_tenant_context(tenant_token=token)
        token = set_current_tenant_id(other_id)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=other_id)) as db:
            other = (await db.execute(select(models.Treatment).where(models.Treatment.tenant_id == other_id, models.Treatment.id == deleted_id))).scalar_one()
            assert other.cost == Decimal('999.99') and other.procedure == 'Other clinic treatment'
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_restore_round_trip_preserves_other_tenant_and_live_identity():
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            a, b = models.Tenant(name='Archive clinic A'), models.Tenant(name='Archive clinic B')
            db.add_all([a, b])
            await db.flush()
            user = models.User(tenant_id=a.id, username='archive_' + suffix, email=suffix + '@example.com', hashed_password='unchanged-synthetic', role='admin', is_active=True, commission_percent=None, fixed_salary=None, per_appointment_fee=None)
            patient = models.Patient(tenant_id=a.id, name='Original patient', age=30, phone='0', medical_history=None, notes=None)
            other = models.Patient(tenant_id=b.id, name='Other tenant patient', age=40, phone='0', medical_history=None, notes=None)
            db.add_all([user, patient, other])
            await db.flush()
            treatment = models.Treatment(tenant_id=a.id, patient_id=patient.id, doctor_id=user.id, tooth_number=16, procedure='Crown', lab_choice='in_clinic', cost=Decimal('123.45'), discount=Decimal('1.25'))
            db.add(treatment)
            await db.commit()
            tenant_a, tenant_b, actor, patient_id = a.id, b.id, user.id, patient.id
    token = set_current_tenant_id(tenant_a)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_a)) as db:
            archive = await export_clinic_archive_data(db, tenant_a)
            data = validate_archive_sections(archive, tenant_id=tenant_a)
            validate_archive_values(data)
            validate_archive_references(data, tenant_id=tenant_a)
            staff = await resolve_staff_mapping(db, tenant_a, data['staff_references'])
            patient = (await db.execute(select(models.Patient).where(models.Patient.id == patient_id))).scalar_one()
            patient.name = 'Modified patient'
            await db.commit()
            counts, mapping = await replace_clinic_business_data(db, tenant_id=tenant_a, data=data, staff_mapping=staff)
            assert counts['patients'] == 1
            await db.commit()
            assert mapping['patients'][patient_id] != patient_id
            restored = (await db.execute(select(models.Patient).where(models.Patient.id == mapping['patients'][patient_id]))).scalar_one()
            treatment = (await db.execute(select(models.Treatment).where(models.Treatment.patient_id == restored.id))).scalar_one()
            current_user = (await db.execute(select(models.User).where(models.User.id == actor))).scalar_one()
            assert restored.name == 'Original patient'
            assert restored.medical_history is None and restored.notes is None
            assert treatment.cost == Decimal('123.45') and treatment.discount == Decimal('1.25')
            assert treatment.lab_choice == 'in_clinic' and treatment.doctor_id == actor
            assert current_user.hashed_password == 'unchanged-synthetic' and current_user.role == 'admin'
            assert current_user.commission_percent is None and current_user.fixed_salary is None
    finally:
        clear_tenant_context(tenant_token=token)
    token = set_current_tenant_id(tenant_b)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_b)) as db:
            assert (await db.execute(select(models.Patient.name).where(models.Patient.tenant_id == tenant_b))).scalar_one() == 'Other tenant patient'
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_failure_mid_import_rolls_back_deleted_business_data():
    from sqlalchemy.exc import StatementError
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Archive rollback clinic')
            db.add(tenant)
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='rollback_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True, commission_percent=None, fixed_salary=None, per_appointment_fee=None)
            patient = models.Patient(tenant_id=tenant.id, name='Rollback patient', age=30, phone='0', medical_history=None, notes=None)
            db.add_all([user, patient])
            await db.flush()
            db.add(models.Treatment(tenant_id=tenant.id, patient_id=patient.id, doctor_id=user.id, tooth_number=16, procedure='Crown', cost=Decimal('50'), discount=Decimal('0')))
            await db.commit()
            tenant_id, patient_id = tenant.id, patient.id
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            data = validate_archive_sections(await export_clinic_archive_data(db, tenant_id), tenant_id=tenant_id)
            validate_archive_values(data)
            validate_archive_references(data, tenant_id=tenant_id)
            staff = await resolve_staff_mapping(db, tenant_id, data['staff_references'])
            # Inject an integrity failure after preflight to exercise rollback
            # after the deletion and some inserts have already occurred.
            data['treatments'][0]['is_deleted'] = 'invalid-boolean'
            with pytest.raises(StatementError):
                await replace_clinic_business_data(db, tenant_id=tenant_id, data=data, staff_mapping=staff)
            await db.rollback()
            original = (await db.execute(select(models.Patient).where(models.Patient.id == patient_id))).scalar_one()
            treatment = (await db.execute(select(models.Treatment).where(models.Treatment.patient_id == patient_id))).scalar_one()
            assert original.name == 'Rollback patient'
            assert treatment.procedure == 'Crown' and treatment.cost == Decimal('50')
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_confirmed_restore_coordinator_preserves_outcome():
    import hashlib
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_restore_coordinator import run_confirmed_restore
    from backend.services.tenant_restore_preview import create_restore_preview, confirm_restore_preview
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Restore coordinator clinic')
            db.add(tenant)
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='coordinator_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True, commission_percent=None, fixed_salary=None, per_appointment_fee=None)
            patient = models.Patient(tenant_id=tenant.id, name='Original', age=30, phone='0', medical_history=None, notes=None)
            db.add_all([user, patient])
            await db.commit()
            tenant_id, user_id, patient_id = tenant.id, user.id, patient.id
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            data = await export_clinic_archive_data(db, tenant_id)
            archive = encode_archive(data, tenant_id=tenant_id, installation_id='synthetic', schema_revision='test', key_id='test', key=b'a' * 32)
            operation, confirmation, _, _, _ = await create_restore_preview(db, tenant_id=tenant_id, actor_id=user_id, archive=archive, installation_id='synthetic', keys={'test': b'a' * 32}, supported_revisions={'test'}, max_bytes=1000000)
            await confirm_restore_preview(db, tenant_id=tenant_id, actor_id=user_id, operation_id=operation.id, confirmation=confirmation, archive_digest=hashlib.sha256(archive).hexdigest())
            operation_id = operation.id
            patient = (await db.execute(select(models.Patient).where(models.Patient.id == patient_id))).scalar_one()
            patient.name = 'Modified'
            await db.commit()
            counts, mapping = await run_confirmed_restore(db, tenant_id=tenant_id, operation_id=operation_id, installation_id='synthetic', keys={'test': b'a' * 32}, supported_revisions={'test'}, max_bytes=1000000)
            assert counts['patients'] == 1
            restored = (await db.execute(select(models.Patient).where(models.Patient.id == mapping['patients'][patient_id]))).scalar_one()
            outcome = (await db.execute(select(models.TenantDataOperation).where(models.TenantDataOperation.id == operation_id))).scalar_one()
            assert restored.name == 'Original'
            assert outcome.status == 'completed' and outcome.encrypted_payload is None
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_restore_preserves_lab_payment_inventory_and_embedded_links():
    from datetime import date
    from backend.services.tenant_archive_embedded_refs import validate_embedded_references
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Archive finance clinic')
            db.add(tenant)
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='finance_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=tenant.id, name='Synthetic', age=30, phone='0', medical_history=None, notes=None)
            lab = models.Laboratory(tenant_id=tenant.id, name='Synthetic lab')
            warehouse = models.Warehouse(tenant_id=tenant.id, name='Synthetic warehouse')
            material = models.Material(tenant_id=tenant.id, name='Synthetic material', type='DIVISIBLE', base_unit='g')
            db.add_all([user, patient, lab, warehouse, material])
            await db.flush()
            treatment = models.Treatment(tenant_id=tenant.id, patient_id=patient.id, doctor_id=user.id, procedure='Crown', tooth_number=16, cost=Decimal('300'), discount=Decimal('10'), lab_choice='external_lab')
            batch = models.Batch(tenant_id=tenant.id, material_id=material.id, batch_number='synthetic', expiry_date=date(2030, 1, 1), cost_per_unit=Decimal('2.50'))
            db.add_all([treatment, batch])
            await db.flush()
            order = models.LabOrder(tenant_id=tenant.id, patient_id=patient.id, laboratory_id=lab.id, treatment_id=treatment.id, doctor_id=user.id, work_type='Crown', tooth_number='16', cost=Decimal('100'), price_to_patient=Decimal('0'))
            stock = models.StockItem(tenant_id=tenant.id, warehouse_id=warehouse.id, batch_id=batch.id, quantity=8.5)
            db.add_all([order, stock])
            await db.flush()
            db.add_all([
                models.LabPayment(tenant_id=tenant.id, laboratory_id=lab.id, lab_order_id=order.id, amount=Decimal('25')),
                models.StockMovement(tenant_id=tenant.id, stock_item_id=stock.id, change_amount=-1.5, reason='use', reference_id=f'TREATMENT:{treatment.id}', performed_by=user.id),
                models.MaterialSession(tenant_id=tenant.id, stock_item_id=stock.id, patient_id=patient.id, doctor_id=user.id, remaining_est=0.5),
            ])
            await db.commit()
            tenant_id, treatment_id = tenant.id, treatment.id
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            data = validate_archive_sections(await export_clinic_archive_data(db, tenant_id), tenant_id=tenant_id)
            validate_archive_values(data)
            validate_archive_references(data, tenant_id=tenant_id)
            validate_embedded_references(data, tenant_id=tenant_id)
            staff = await resolve_staff_mapping(db, tenant_id, data['staff_references'])
            counts, mapping = await replace_clinic_business_data(db, tenant_id=tenant_id, data=data, staff_mapping=staff)
            await db.commit()
            assert counts['lab_payments'] == counts['stock_movements'] == counts['material_sessions'] == 1
            order = (await db.execute(select(models.LabOrder).where(models.LabOrder.tenant_id == tenant_id))).scalar_one()
            payment = (await db.execute(select(models.LabPayment).where(models.LabPayment.tenant_id == tenant_id))).scalar_one()
            movement = (await db.execute(select(models.StockMovement).where(models.StockMovement.tenant_id == tenant_id))).scalar_one()
            stock = (await db.execute(select(models.StockItem).where(models.StockItem.tenant_id == tenant_id))).scalar_one()
            assert order.treatment_id == mapping['treatments'][treatment_id]
            assert payment.lab_order_id == order.id and payment.amount == Decimal('25')
            assert movement.reference_id == f"TREATMENT:{mapping['treatments'][treatment_id]}"
            assert stock.quantity == 8.5 and movement.change_amount == -1.5
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_restore_outbox_worker_finishes_confirmed_operation(monkeypatch):
    import base64
    import hashlib
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_restore_preview import create_restore_preview, confirm_restore_preview
    from backend.workers.handlers import on_tenant_restore_confirmed
    from sqlalchemy import text
    key = b'a' * 32
    monkeypatch.setenv('TENANT_BACKUP_KEY_ID', 'test')
    monkeypatch.setenv('TENANT_BACKUP_ENCRYPTION_KEY', base64.urlsafe_b64encode(key).decode())
    monkeypatch.setenv('DENTIX_INSTALLATION_ID', 'synthetic')
    monkeypatch.setenv('TENANT_BACKUP_MAX_BYTES', '1000000')
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Worker restore clinic')
            db.add(tenant)
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='worker_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            db.add(user)
            await db.commit()
            tenant_id, actor = tenant.id, user.id
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            revision = (await db.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
            payload = await export_clinic_archive_data(db, tenant_id)
            archive = encode_archive(payload, tenant_id=tenant_id, installation_id='synthetic', schema_revision=revision, key_id='test', key=key)
            operation, confirmation, _, _, _ = await create_restore_preview(db, tenant_id=tenant_id, actor_id=actor, archive=archive, installation_id='synthetic', keys={'test': key}, supported_revisions={revision}, max_bytes=1000000)
            await confirm_restore_preview(db, tenant_id=tenant_id, actor_id=actor, operation_id=operation.id, confirmation=confirmation, archive_digest=hashlib.sha256(archive).hexdigest())
            event = (await db.execute(select(models.DomainEvent).where(models.DomainEvent.aggregate_id == operation.id))).scalar_one()
            await on_tenant_restore_confirmed(event)
            await db.refresh(operation)
            assert operation.status == 'completed' and operation.encrypted_payload is None
            await on_tenant_restore_confirmed(event)
    finally:
        clear_tenant_context(tenant_token=token)


@pytest.mark.asyncio
async def test_closed_session_learning_survives_deleted_procedure_and_repeated_restore():
    from backend.crud.procedure import delete_procedure
    from backend.services.inventory_learning_service import InventoryLearningService
    from backend.services.tenant_archive import encode_archive
    from backend.services.tenant_restore_coordinator import run_confirmed_restore
    from backend.services.tenant_restore_preview import create_restore_preview, confirm_restore_preview
    from datetime import date

    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant, other = models.Tenant(name='Learning clinic'), models.Tenant(name='Other learning clinic')
            category = models.MaterialCategory(name_en='learning_' + suffix, name_ar='Synthetic learning')
            db.add_all([tenant, other, category])
            await db.flush()
            user = models.User(tenant_id=tenant.id, username='learning_' + suffix, role='admin',
                               hashed_password='unchanged', commission_percent=Decimal('17.25'))
            patient = models.Patient(tenant_id=tenant.id, name='Synthetic learning', phone='0', age=30)
            deleted = models.Procedure(tenant_id=tenant.id, name='Deleted ' + suffix, price=Decimal('50'))
            live = models.Procedure(tenant_id=tenant.id, name='Live ' + suffix, price=Decimal('100'))
            shared = models.Procedure(tenant_id=None, name='Global ' + suffix, price=Decimal('200'))
            material = models.Material(tenant_id=tenant.id, name='Cement', type='DIVISIBLE', base_unit='g',
                                       category_id=category.id, standard_price=Decimal('2.50'))
            warehouse = models.Warehouse(tenant_id=tenant.id, name='Learning warehouse')
            db.add_all([user, patient, deleted, live, shared, material, warehouse])
            await db.flush()
            batch = models.Batch(tenant_id=tenant.id, material_id=material.id, batch_number='learning',
                                 expiry_date=date(2030, 1, 1), cost_per_unit=Decimal('2.50'))
            db.add(batch)
            await db.flush()
            stock = models.StockItem(tenant_id=tenant.id, warehouse_id=warehouse.id, batch_id=batch.id, quantity=3)
            db.add(stock)
            await db.flush()
            opened = models.MaterialSession(tenant_id=tenant.id, stock_item_id=stock.id, doctor_id=user.id)
            db.add(opened)
            await db.flush()
            for procedure in (deleted, live, shared):
                treatment = models.Treatment(tenant_id=tenant.id, patient_id=patient.id, doctor_id=user.id,
                                             tooth_number=16, procedure=procedure.name, cost=procedure.price,
                                             discount=Decimal('0'))
                db.add(treatment)
                await db.flush()
                db.add_all([
                    models.ProcedureMaterialWeight(tenant_id=tenant.id, procedure_id=procedure.id,
                        material_id=material.id, category_id=category.id, weight=1),
                    models.TreatmentMaterialUsage(tenant_id=tenant.id, treatment_id=treatment.id,
                        material_id=material.id, session_id=opened.id, weight_score=1),
                ])
            await db.commit()
            tenant_id, other_id, actor, session_id = tenant.id, other.id, user.id, opened.id
            deleted_id, live_id, global_id = deleted.id, live.id, shared.id

    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            # Legacy deployments created logs with privileged DB connections,
            # including global catalogue entries hidden by today's tenant RLS.
            # Recreate that source data; export/preview/restore below all use
            # the restricted app connection and retain the global assertions.
            async with db.bypass_rls() as legacy_db:
                await InventoryLearningService(legacy_db).close_session(session_id, total_consumed=1.5, user_id=actor)
            log = (await db.execute(select(models.MaterialLearningLog).where(
                models.MaterialLearningLog.tenant_id == tenant_id))).scalar_one()
            original = json.loads(log.calculation_data)
            assert set(original['learning_updates']) == {str(deleted_id), str(live_id), str(global_id)}
            assert await delete_procedure(db, deleted_id, tenant_id) is not None

        clear_tenant_context(tenant_token=token)
        token = set_current_tenant_id(other_id)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=other_id)) as db:
            db.add(models.Procedure(id=deleted_id, tenant_id=other_id, name='Other procedure ' + suffix,
                                     price=Decimal('999.99')))
            await db.commit()
        clear_tenant_context(tenant_token=token)
        token = set_current_tenant_id(tenant_id)

        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            payload = await export_clinic_archive_data(db, tenant_id)
            assert json.loads(payload['data']['material_learning_logs'][0]['calculation_data']) == original
            from sqlalchemy import update
            from backend.services.tenant_restore_coordinator import known_global_references
            globals_ = await known_global_references(db)
            assert global_id in globals_['procedures']
            assert live_id not in globals_['procedures'] and deleted_id not in globals_['procedures']
            unchanged = await db.execute(update(models.Procedure).where(
                models.Procedure.id == global_id).values(price=Decimal('999')))
            assert unchanged.rowcount == 0
            async with db.bypass_rls() as catalog_db:
                global_price = (await catalog_db.execute(select(models.Procedure.price).where(
                    models.Procedure.tenant_id.is_(None), models.Procedure.id == global_id))).scalar_one()
                assert global_price == Decimal('200')
            from backend.services.export_service import export_tenant_data
            from backend.services.tenant_archive_legacy import adapt_legacy_json
            legacy = adapt_legacy_json(await export_tenant_data(db, tenant_id), tenant_id=tenant_id)
            # Legacy JSON omits learning/weight tables. Keep its existing
            # no-data-loss rejection rather than treating it as a full backup.
            from backend.services.tenant_archive import ArchiveError
            legacy_archive = encode_archive(legacy, tenant_id=tenant_id, installation_id='synthetic-learning',
                                           schema_revision='bc78a10d932e', key_id='test', key=b'l' * 32)
            with pytest.raises(ArchiveError, match='النسخة القديمة لا تشمل بيانات حالية'):
                await create_restore_preview(
                    db, tenant_id=tenant_id, actor_id=actor, archive=legacy_archive,
                    installation_id='synthetic-learning', keys={'test': b'l' * 32},
                    supported_revisions={'bc78a10d932e'}, max_bytes=1000000)
            assert json.loads(log.calculation_data) == original
            for revision in ('bc78a10d932e', 'e2b3c4d5e6f7'):
                archive = encode_archive(payload, tenant_id=tenant_id, installation_id='synthetic-learning',
                                         schema_revision=revision, key_id='test', key=b'l' * 32)
                operation, confirmation, _, _, _ = await create_restore_preview(
                    db, tenant_id=tenant_id, actor_id=actor, archive=archive,
                    installation_id='synthetic-learning', keys={'test': b'l' * 32},
                    supported_revisions={revision}, max_bytes=1000000)
                await confirm_restore_preview(db, tenant_id=tenant_id, actor_id=actor,
                    operation_id=operation.id, confirmation=confirmation, archive_digest=operation.archive_digest)
                _, mapping = await run_confirmed_restore(db, tenant_id=tenant_id, operation_id=operation.id,
                    installation_id='synthetic-learning', keys={'test': b'l' * 32},
                    supported_revisions={revision}, max_bytes=1000000)
                new_historical = mapping['historical_procedures'][deleted_id]
                new_live = mapping['procedures'][live_id]
                assert new_historical not in {new_live, global_id, deleted_id}
                log = (await db.execute(select(models.MaterialLearningLog).where(
                    models.MaterialLearningLog.tenant_id == tenant_id).execution_options(populate_existing=True))).scalar_one()
                restored = json.loads(log.calculation_data)
                assert restored['learning_updates'] == {
                    str(new_historical): original['learning_updates'][str(deleted_id)],
                    str(new_live): original['learning_updates'][str(live_id)],
                    str(global_id): original['learning_updates'][str(global_id)],
                }
                assert [entry['treatment_id'] for entry in restored['dist_log']] == [
                    mapping['treatments'][entry['treatment_id']] for entry in original['dist_log']]
                assert [entry['cost'] for entry in restored['usage_updates']] == [
                    entry['cost'] for entry in original['usage_updates']]
                procedures = (await db.execute(select(models.Procedure).where(
                    models.Procedure.tenant_id == tenant_id))).scalars().all()
                assert len(procedures) == 1 and procedures[0].id == new_live
                assert procedures[0].price == Decimal('100')
                weights = (await db.execute(select(models.ProcedureMaterialWeight).where(
                    models.ProcedureMaterialWeight.tenant_id == tenant_id))).scalars().all()
                assert {row.procedure_id for row in weights} == {new_live, global_id}
                assert all(row.current_average_usage == 0.5 and row.sample_size == 1 for row in weights)
                user = (await db.execute(select(models.User).where(
                    models.User.tenant_id == tenant_id, models.User.id == actor))).scalar_one()
                assert user.hashed_password == 'unchanged' and user.commission_percent == Decimal('17.25')
                future = models.Procedure(tenant_id=tenant_id, name='Future ' + uuid.uuid4().hex, price=Decimal('0'))
                db.add(future)
                await db.flush()
                assert future.id != new_historical
                await db.rollback()
                payload = await export_clinic_archive_data(db, tenant_id)
                original, deleted_id, live_id = restored, new_historical, new_live
            await db.rollback()

        clear_tenant_context(tenant_token=token)
        token = set_current_tenant_id(other_id)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=other_id)) as db:
            other_proc = (await db.execute(select(models.Procedure).where(
                models.Procedure.tenant_id == other_id))).scalar_one()
            assert other_proc.price == Decimal('999.99') and other_proc.name == 'Other procedure ' + suffix
    finally:
        clear_tenant_context(tenant_token=token)
