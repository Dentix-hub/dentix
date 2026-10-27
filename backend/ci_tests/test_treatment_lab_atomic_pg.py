"""Concurrent treatment/lab retries under restricted PostgreSQL RLS."""
import asyncio
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from backend import models, schemas
from backend.core.tenancy import set_current_tenant_id, clear_tenant_context
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.feature_service import FeatureFlagService
from backend.services.treatment_service import TreatmentService


@pytest.mark.asyncio
async def test_concurrent_retry_creates_one_treatment_order_and_payment(monkeypatch):
    async def flag(_db, key, _tenant_id):
        return key == 'clinical_vnext_native_writes'
    monkeypatch.setattr(FeatureFlagService, 'is_feature_enabled', flag)
    suffix = uuid.uuid4().hex
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = models.Tenant(name='Atomic lab test', timezone='Africa/Cairo')
            db.add(tenant)
            await db.flush()
            user = models.User(username='atomic_' + suffix, email='atomic_' + suffix + '@example.com', role='admin', tenant_id=tenant.id, is_active=True, hashed_password='synthetic')
            patient = models.Patient(name='Synthetic', age=30, phone='000', medical_history='', notes='', tenant_id=tenant.id)
            lab = models.Laboratory(name='Synthetic Lab', tenant_id=tenant.id)
            db.add_all([user, patient, lab])
            await db.commit()
            tenant_id, user_id, patient_id, lab_id = tenant.id, user.id, patient.id, lab.id

    payload = dict(patient_id=patient_id, tooth_number=16, procedure='Crown', cost=Decimal('500'), skip_stock_check=True,
                   idempotency_key='retry_' + suffix, lab_choice='external_lab',
                   lab_order={'laboratory_id': lab_id, 'work_type': 'Crown', 'tooth_number': '16', 'cost': '200', 'paid_now': '50'})

    async def submit():
        token = set_current_tenant_id(tenant_id)
        try:
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                user = (await db.execute(select(models.User).where(models.User.id == user_id, models.User.tenant_id == tenant_id))).scalar_one()
                result = await TreatmentService(db, tenant_id, user).create_treatment(schemas.TreatmentCreate(**payload))
                return result.id
        finally:
            clear_tenant_context(tenant_token=token)

    ids = await asyncio.gather(submit(), submit())
    assert ids[0] == ids[1]
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            assert (await db.execute(select(func.count(models.Treatment.id)).where(models.Treatment.tenant_id == tenant_id, models.Treatment.request_key == payload['idempotency_key']))).scalar_one() == 1
            order = (await db.execute(select(models.LabOrder).where(models.LabOrder.tenant_id == tenant_id, models.LabOrder.treatment_id == ids[0]))).scalar_one()
            assert (await db.execute(select(func.count(models.LabPayment.id)).where(models.LabPayment.tenant_id == tenant_id, models.LabPayment.lab_order_id == order.id))).scalar_one() == 1
