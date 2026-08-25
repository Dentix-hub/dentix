"""Real PostgreSQL FORCE-RLS and parent/child tenant consistency gate."""

from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from backend import models
from backend.database import AsyncSessionLocal, RlsContext

TENANT_A = 99571
TENANT_B = 99572


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_A) is not None:
                return
            tenant_a = models.Tenant(id=TENANT_A, name="Child RLS A")
            tenant_b = models.Tenant(id=TENANT_B, name="Child RLS B")
            db.add_all([tenant_a, tenant_b])
            await db.flush()
            patient_a = models.Patient(
                id=995711,
                tenant_id=TENANT_A,
                name="A",
                age=30,
                phone="01099571001",
                medical_history="",
                notes="",
            )
            patient_b = models.Patient(
                id=995721,
                tenant_id=TENANT_B,
                name="B",
                age=31,
                phone="01099572001",
                medical_history="",
                notes="",
            )
            warehouse_a = models.Warehouse(id=995712, tenant_id=TENANT_A, name="A")
            warehouse_b = models.Warehouse(id=995722, tenant_id=TENANT_B, name="B")
            material_a = models.Material(
                id=995713, tenant_id=TENANT_A, name="A", type="DIVISIBLE", base_unit="g"
            )
            material_b = models.Material(
                id=995723, tenant_id=TENANT_B, name="B", type="DIVISIBLE", base_unit="g"
            )
            db.add_all([patient_a, patient_b, warehouse_a, warehouse_b, material_a, material_b])
            await db.flush()
            batch_a = models.Batch(
                id=995714,
                tenant_id=TENANT_A,
                material_id=material_a.id,
                batch_number="A",
                expiry_date=date(2030, 1, 1),
            )
            batch_b = models.Batch(
                id=995724,
                tenant_id=TENANT_B,
                material_id=material_b.id,
                batch_number="B",
                expiry_date=date(2030, 1, 1),
            )
            db.add_all([batch_a, batch_b])
            await db.flush()
            stock_a = models.StockItem(
                id=995715,
                tenant_id=TENANT_A,
                warehouse_id=warehouse_a.id,
                batch_id=batch_a.id,
                quantity=1,
            )
            stock_b = models.StockItem(
                id=995725,
                tenant_id=TENANT_B,
                warehouse_id=warehouse_b.id,
                batch_id=batch_b.id,
                quantity=1,
            )
            db.add_all([stock_a, stock_b])
            await db.flush()
            db.add_all(
                [
                    models.ToothStatus(id=995716, tenant_id=TENANT_A, patient_id=patient_a.id, tooth_number=11, condition="A"),
                    models.ToothStatus(id=995726, tenant_id=TENANT_B, patient_id=patient_b.id, tooth_number=11, condition="B"),
                    models.Prescription(id=995717, tenant_id=TENANT_A, patient_id=patient_a.id, medications="A"),
                    models.Prescription(id=995727, tenant_id=TENANT_B, patient_id=patient_b.id, medications="B"),
                    models.Attachment(id=995718, tenant_id=TENANT_A, patient_id=patient_a.id, file_path="a", filename="a", file_type="text/plain"),
                    models.Attachment(id=995728, tenant_id=TENANT_B, patient_id=patient_b.id, file_path="b", filename="b", file_type="text/plain"),
                    models.MaterialSession(id=995719, tenant_id=TENANT_A, stock_item_id=stock_a.id, patient_id=patient_a.id),
                    models.MaterialSession(id=995729, tenant_id=TENANT_B, stock_item_id=stock_b.id, patient_id=patient_b.id),
                    models.StockMovement(id=995710, tenant_id=TENANT_A, stock_item_id=stock_a.id, change_amount=1, reason="TEST"),
                    models.StockMovement(id=995720, tenant_id=TENANT_B, stock_item_id=stock_b.id, change_amount=1, reason="TEST"),
                ]
            )
            await db.commit()


@pytest.mark.asyncio
async def test_five_child_tables_are_isolated_and_cross_tenant_writes_fail():
    await _seed()
    expectations = (
        (models.ToothStatus, 995716, 995726),
        (models.Prescription, 995717, 995727),
        (models.Attachment, 995718, 995728),
        (models.MaterialSession, 995719, 995729),
        (models.StockMovement, 995710, 995720),
    )
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as db:
        for model, own_id, foreign_id in expectations:
            ids = set((await db.execute(select(model.id))).scalars())
            assert own_id in ids
            assert foreign_id not in ids

        db.add(
            models.Attachment(
                tenant_id=TENANT_A,
                patient_id=995721,
                file_path="cross",
                filename="cross",
                file_type="text/plain",
            )
        )
        with pytest.raises(DBAPIError):
            await db.commit()
        await db.rollback()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as db:
        for model, _, _ in expectations:
            assert list((await db.execute(select(model.id))).scalars()) == []


@pytest.mark.asyncio
async def test_application_role_cannot_self_enable_cross_tenant_bypass():
    """A custom GUC must never promote the NOBYPASSRLS application role."""
    await _seed()
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as db:
        await db.execute(text("SELECT set_config('rls.bypass_rls', 'true', true)"))
        visible = set(
            (await db.execute(select(models.Patient.id))).scalars().all()
        )
        assert 995711 in visible
        assert 995721 not in visible
