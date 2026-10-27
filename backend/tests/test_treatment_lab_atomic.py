"""Treatment/lab orchestration must use one tenant transaction."""
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend import models, schemas
from backend.services.feature_service import FeatureFlagService
from backend.services.treatment_service import TreatmentService


@pytest.mark.asyncio
async def test_external_lab_creates_one_order_payment_and_treatment(async_db_session, test_user, test_patient, monkeypatch):
    monkeypatch.setattr(FeatureFlagService, 'is_feature_enabled', AsyncMock(return_value=True))
    lab = models.Laboratory(name='Atomic Lab', tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.commit()
    payload = schemas.TreatmentCreate(
        patient_id=test_patient.id, tooth_number=16, procedure='Crown', cost=Decimal('500'), skip_stock_check=True,
        idempotency_key='synthetic-request-1', lab_choice='external_lab', lab_order={'laboratory_id': lab.id, 'work_type': 'Crown', 'tooth_number': '16', 'cost': '200', 'paid_now': '50'},
    )
    treatment = await TreatmentService(async_db_session, test_user.tenant_id, test_user).create_treatment(payload)
    orders = (await async_db_session.execute(select(models.LabOrder).where(models.LabOrder.treatment_id == treatment.id))).scalars().all()
    assert len(orders) == 1 and orders[0].tenant_id == test_user.tenant_id
    assert (await async_db_session.execute(select(func.count(models.LabPayment.id)).where(models.LabPayment.lab_order_id == orders[0].id))).scalar_one() == 1
    assert treatment.lab_choice == 'external_lab'
    retry = await TreatmentService(async_db_session, test_user.tenant_id, test_user).create_treatment(payload)
    assert retry.id == treatment.id
    assert (await async_db_session.execute(select(func.count(models.LabOrder.id)).where(models.LabOrder.treatment_id == treatment.id))).scalar_one() == 1
    assert (await async_db_session.execute(select(func.count(models.LabPayment.id)).where(models.LabPayment.lab_order_id == orders[0].id))).scalar_one() == 1
    changed = payload.model_copy(update={'cost': Decimal('501')})
    with pytest.raises(HTTPException) as exc:
        await TreatmentService(async_db_session, test_user.tenant_id, test_user).create_treatment(changed)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("idempotency_key", [None, "bad-lab-request"])
async def test_missing_choice_and_bad_lab_do_not_commit_treatment(async_db_session, test_user, test_patient, monkeypatch, idempotency_key):
    monkeypatch.setattr(FeatureFlagService, 'is_feature_enabled', AsyncMock(return_value=True))
    service = TreatmentService(async_db_session, test_user.tenant_id, test_user)
    base = dict(patient_id=test_patient.id, tooth_number=16, procedure='Crown', cost=Decimal('500'), skip_stock_check=True)
    with pytest.raises(HTTPException) as exc:
        await service.create_treatment(schemas.TreatmentCreate(**base))
    assert exc.value.status_code == 422
    before = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one()
    with pytest.raises(HTTPException) as exc:
        await service.create_treatment(schemas.TreatmentCreate(**base, idempotency_key=idempotency_key, lab_choice='external_lab', lab_order={'laboratory_id': 99999999, 'work_type': 'Crown', 'tooth_number': '16'}))
    assert exc.value.status_code == 422
    await async_db_session.rollback()
    assert (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one() == before


@pytest.mark.asyncio
async def test_disabled_rollout_rejects_new_choice_but_preserves_old_payload(async_db_session, test_user, test_patient, monkeypatch):
    monkeypatch.setattr(FeatureFlagService, 'is_feature_enabled', AsyncMock(return_value=False))
    service = TreatmentService(async_db_session, test_user.tenant_id, test_user)
    base = dict(patient_id=test_patient.id, tooth_number=16, procedure='Crown', cost=Decimal('500'), skip_stock_check=True)
    with pytest.raises(HTTPException) as exc:
        await service.create_treatment(schemas.TreatmentCreate(**base, lab_choice='in_clinic'))
    assert exc.value.status_code == 404
    legacy = await service.create_treatment(schemas.TreatmentCreate(**base))
    assert legacy.lab_choice is None


@pytest.mark.asyncio
async def test_direct_order_cannot_override_in_clinic_choice(async_db_session, test_user, test_patient):
    from backend.routers.laboratories import create_lab_order
    lab = models.Laboratory(name='Clinic Test Lab', tenant_id=test_user.tenant_id)
    treatment = models.Treatment(patient_id=test_patient.id, tooth_number=16, procedure='Crown', cost=Decimal('500'), discount=0, tenant_id=test_user.tenant_id, doctor_id=test_user.id, lab_choice='in_clinic')
    async_db_session.add_all([lab, treatment])
    await async_db_session.commit()
    order = schemas.LabOrderCreate(patient_id=test_patient.id, laboratory_id=lab.id, treatment_id=treatment.id, work_type='Crown', tooth_number='16')
    with pytest.raises(HTTPException) as exc:
        await create_lab_order(order=order, db=async_db_session, current_user=test_user)
    assert exc.value.status_code == 422
    assert (await async_db_session.execute(select(func.count(models.LabOrder.id)).where(models.LabOrder.treatment_id == treatment.id))).scalar_one() == 0


@pytest.mark.asyncio
async def test_multi_procedure_failure_rolls_back_prior_treatment_order_and_payment(async_db_session, test_user, test_patient, monkeypatch):
    monkeypatch.setattr(FeatureFlagService, 'is_feature_enabled', AsyncMock(return_value=True))
    lab = models.Laboratory(name='Multi Lab', tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.commit()
    before = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one()
    payload = schemas.ToothMultiProcedureCreate(patient_id=test_patient.id, tooth_number=16, procedures=[
        {'procedure': 'Crown', 'cost': '500', 'lab_choice': 'external_lab', 'lab_order': {'laboratory_id': lab.id, 'work_type': 'Crown', 'tooth_number': '16', 'cost': '200', 'paid_now': '50'}},
        {'procedure': 'Crown', 'cost': '500'},
    ])
    with pytest.raises(HTTPException) as exc:
        await TreatmentService(async_db_session, test_user.tenant_id, test_user).create_multi_procedure_treatment(payload)
    assert exc.value.status_code == 422
    await async_db_session.rollback()
    assert (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one() == before
    assert (await async_db_session.execute(select(func.count(models.LabOrder.id)))).scalar_one() == 0
    assert (await async_db_session.execute(select(func.count(models.LabPayment.id)))).scalar_one() == 0
