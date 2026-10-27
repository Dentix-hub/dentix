"""Synthetic PostgreSQL round trip for tenant business data and identities."""
import uuid
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
async def test_restore_round_trip_preserves_other_tenant_and_live_identity():
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            a, b = models.Tenant(name='Archive clinic A'), models.Tenant(name='Archive clinic B')
            db.add_all([a, b])
            await db.flush()
            user = models.User(tenant_id=a.id, username='archive_' + suffix, email=suffix + '@example.com', hashed_password='unchanged-synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=a.id, name='Original patient', age=30, phone='0', medical_history='', notes='')
            other = models.Patient(tenant_id=b.id, name='Other tenant patient', age=40, phone='0', medical_history='', notes='')
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
            assert treatment.cost == Decimal('123.45') and treatment.discount == Decimal('1.25')
            assert treatment.lab_choice == 'in_clinic' and treatment.doctor_id == actor
            assert current_user.hashed_password == 'unchanged-synthetic' and current_user.role == 'admin'
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
            user = models.User(tenant_id=tenant.id, username='rollback_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=tenant.id, name='Rollback patient', age=30, phone='0', medical_history='', notes='')
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
            user = models.User(tenant_id=tenant.id, username='coordinator_' + suffix, email=suffix + '@example.com', hashed_password='synthetic', role='admin', is_active=True)
            patient = models.Patient(tenant_id=tenant.id, name='Original', age=30, phone='0', medical_history='', notes='')
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
            patient = models.Patient(tenant_id=tenant.id, name='Synthetic', age=30, phone='0', medical_history='', notes='')
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
