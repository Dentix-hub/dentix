import os
import tempfile
import pytest
from datetime import datetime
from decimal import Decimal
import sqlalchemy as sa
from alembic.config import Config
from alembic import command
from fastapi.testclient import TestClient

from backend import models, schemas
from backend.main import app
from backend.database import get_async_db


def test_alembic_treatment_link_migration_lifecycle_sqlite(monkeypatch):
    """Rehearse Alembic migration 6f7a8b9c0d1e upgrade and downgrade on SQLite."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        engine = sa.create_engine(sqlite_url)
        alembic_cfg_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        )
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Create base tables needed for lab_orders
        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY, name VARCHAR)"))
            conn.execute(sa.text("CREATE TABLE patients (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE laboratories (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE treatments (id INTEGER PRIMARY KEY, tenant_id INTEGER, patient_id INTEGER)"))
            conn.execute(
                sa.text(
                    """CREATE TABLE lab_orders (
                        id INTEGER PRIMARY KEY,
                        patient_id INTEGER,
                        laboratory_id INTEGER,
                        work_item_id INTEGER,
                        work_type VARCHAR,
                        tooth_number VARCHAR,
                        shade VARCHAR,
                        material VARCHAR,
                        cost NUMERIC(14, 2) DEFAULT 0.0,
                        price_to_patient NUMERIC(14, 2) DEFAULT 0.0,
                        status VARCHAR DEFAULT 'pending',
                        notes TEXT,
                        order_date TIMESTAMP,
                        delivery_date TIMESTAMP,
                        received_date TIMESTAMP,
                        tenant_id INTEGER,
                        doctor_id INTEGER
                    )"""
                )
            )
            conn.commit()

        # 2. Stamp at 5e6f7a8b9c0d (parent revision)
        command.stamp(config, "5e6f7a8b9c0d")

        # 3. Upgrade to 6f7a8b9c0d1e
        command.upgrade(config, "6f7a8b9c0d1e")

        # Verify upgraded schema
        inspector = sa.inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("lab_orders")}
        assert "treatment_id" in cols, "treatment_id must be added to lab_orders"
        assert cols["treatment_id"]["nullable"] is True, "treatment_id must be nullable"

        indexes = {ix["name"]: ix for ix in inspector.get_indexes("lab_orders")}
        assert "ix_lab_orders_treatment_id" in indexes
        assert "ix_lab_orders_tenant_treatment" in indexes
        assert indexes["ix_lab_orders_treatment_id"]["column_names"] == ["treatment_id"]
        assert indexes["ix_lab_orders_tenant_treatment"]["column_names"] == ["tenant_id", "treatment_id"]

        # 4. Downgrade back to 5e6f7a8b9c0d
        command.downgrade(config, "5e6f7a8b9c0d")

        # Verify downgraded schema
        inspector = sa.inspect(engine)
        cols_after = {c["name"]: c for c in inspector.get_columns("lab_orders")}
        assert "treatment_id" not in cols_after, "treatment_id must be dropped on downgrade"

        indexes_after = {ix["name"] for ix in inspector.get_indexes("lab_orders")}
        assert "ix_lab_orders_treatment_id" not in indexes_after
        assert "ix_lab_orders_tenant_treatment" not in indexes_after

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_create_lab_order_with_treatment_id_skips_synthetic_treatment(async_db_session, test_user, test_patient):
    """When treatment_id is given, validate tenant/patient, link it, and create ZERO synthetic treatments."""
    from backend.routers.laboratories import create_lab_order

    # Setup lab
    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    # Setup real clinical treatment (e.g. Crown recorded by doctor)
    treatment = models.Treatment(
        patient_id=test_patient.id,
        tooth_number=16,
        procedure="Crown Zirconia",
        diagnosis="Caries",
        cost=Decimal("2500.00"),
        discount=Decimal("0.00"),
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(treatment)
    await async_db_session.flush()

    # Pre-count treatments
    res_before = await async_db_session.execute(
        sa.select(sa.func.count(models.Treatment.id)).where(models.Treatment.tenant_id == test_user.tenant_id)
    )
    count_before = res_before.scalar()

    order_payload = schemas.LabOrderCreate(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=treatment.id,
        work_type="Crown",
        tooth_number="16",
        shade="A2",
        material="Zirconia",
        cost=Decimal("400.00"),
        price_to_patient=Decimal("2500.00"),
    )

    res = await create_lab_order(order=order_payload, db=async_db_session, current_user=test_user)
    assert res["data"]["treatment_id"] == treatment.id
    assert res["data"]["patient_name"] == test_patient.name
    assert res["data"]["laboratory_name"] == lab.name
    assert res["data"]["is_existing"] is False

    # Post-count treatments: must NOT have created a synthetic treatment!
    res_after = await async_db_session.execute(
        sa.select(sa.func.count(models.Treatment.id)).where(models.Treatment.tenant_id == test_user.tenant_id)
    )
    count_after = res_after.scalar()
    assert count_after == count_before, "Must NOT auto-create a synthetic Treatment when treatment_id is given!"

    # Idempotency test: posting again for same treatment returns existing order with is_existing=True
    res_idempotent = await create_lab_order(order=order_payload, db=async_db_session, current_user=test_user)
    assert res_idempotent["data"]["id"] == res["data"]["id"]
    assert res_idempotent["data"]["is_existing"] is True


@pytest.mark.asyncio
async def test_create_lab_order_invalid_treatment_id_rejected(async_db_session, test_user, test_patient):
    """When treatment_id belongs to another patient or tenant, return 404."""
    from backend.routers.laboratories import create_lab_order
    from fastapi import HTTPException

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    order_payload = schemas.LabOrderCreate(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=999999,
        work_type="Crown",
        tooth_number="16",
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_lab_order(order=order_payload, db=async_db_session, current_user=test_user)
    assert exc_info.value.status_code == 404
    assert "Treatment not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_lab_order_without_treatment_creates_synthetic_legacy_behavior(async_db_session, test_user, test_patient):
    """Old clients posting without treatment_id/work_item_id with price_to_patient still create synthetic treatment."""
    from backend.routers.laboratories import create_lab_order

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    res_before = await async_db_session.execute(
        sa.select(sa.func.count(models.Treatment.id)).where(models.Treatment.tenant_id == test_user.tenant_id)
    )
    count_before = res_before.scalar()

    order_payload = schemas.LabOrderCreate(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=None,
        work_item_id=None,
        work_type="Crown",
        tooth_number="16",
        shade="A2",
        material="Zirconia",
        cost=Decimal("400.00"),
        price_to_patient=Decimal("1500.00"),
    )

    res = await create_lab_order(order=order_payload, db=async_db_session, current_user=test_user)
    assert res["data"]["treatment_id"] is None

    # Post-count treatments: legacy synthetic treatment was created
    res_after = await async_db_session.execute(
        sa.select(sa.func.count(models.Treatment.id)).where(models.Treatment.tenant_id == test_user.tenant_id)
    )
    count_after = res_after.scalar()
    assert count_after == count_before + 1, "Legacy clients must retain synthetic treatment creation"


@pytest.mark.asyncio
async def test_update_lab_order_cross_tenant_treatment_id_rejected_404(async_db_session, test_user, test_patient):
    """Updating lab order with treatment_id belonging to another tenant returns 404."""
    from backend.routers.laboratories import update_lab_order
    from fastapi import HTTPException

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    order = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        work_type="Crown",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(order)

    # Treatment from different tenant
    other_tenant = models.Tenant(name="Other Clinic")
    async_db_session.add(other_tenant)
    await async_db_session.flush()

    cross_tenant_treatment = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown",
        tenant_id=other_tenant.id,
        doctor_id=test_user.id,
    )
    async_db_session.add(cross_tenant_treatment)
    await async_db_session.flush()

    update_payload = schemas.LabOrderUpdate(treatment_id=cross_tenant_treatment.id)
    with pytest.raises(HTTPException) as exc_info:
        await update_lab_order(order_id=order.id, order_update=update_payload, db=async_db_session, current_user=test_user)
    assert exc_info.value.status_code == 404
    assert "Treatment not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_lab_order_other_patient_treatment_id_rejected_404(async_db_session, test_user, test_patient):
    """Updating lab order with treatment_id belonging to another patient returns 404."""
    from backend.routers.laboratories import update_lab_order
    from fastapi import HTTPException

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    order = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        work_type="Crown",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(order)

    # Other patient in the same clinic
    other_patient = models.Patient(
        name="Other Patient",
        tenant_id=test_user.tenant_id,
        age=30,
        phone="01011223344",
        medical_history="",
        notes="",
    )
    async_db_session.add(other_patient)
    await async_db_session.flush()

    other_patient_treatment = models.Treatment(
        patient_id=other_patient.id,
        procedure="Crown",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(other_patient_treatment)
    await async_db_session.flush()

    update_payload = schemas.LabOrderUpdate(treatment_id=other_patient_treatment.id)
    with pytest.raises(HTTPException) as exc_info:
        await update_lab_order(order_id=order.id, order_update=update_payload, db=async_db_session, current_user=test_user)
    assert exc_info.value.status_code == 404
    assert "Treatment not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_lab_order_deleted_treatment_id_rejected_404(async_db_session, test_user, test_patient):
    """Updating lab order with a soft-deleted treatment returns 404."""
    from backend.routers.laboratories import update_lab_order
    from fastapi import HTTPException

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    order = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        work_type="Crown",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(order)

    deleted_treatment = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
        is_deleted=True,
    )
    async_db_session.add(deleted_treatment)
    await async_db_session.flush()

    update_payload = schemas.LabOrderUpdate(treatment_id=deleted_treatment.id)
    with pytest.raises(HTTPException) as exc_info:
        await update_lab_order(order_id=order.id, order_update=update_payload, db=async_db_session, current_user=test_user)
    assert exc_info.value.status_code == 404
    assert "Treatment not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_lab_order_treatment_already_linked_rejected_409(async_db_session, test_user, test_patient):
    """Updating lab order to link to a treatment that already has an active order raises 409."""
    from backend.routers.laboratories import update_lab_order
    from fastapi import HTTPException

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    treatment_1 = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown A",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    treatment_2 = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown B",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add_all([treatment_1, treatment_2])
    await async_db_session.flush()

    # Order 1 already linked to Treatment 1 (active: pending)
    order_1 = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=treatment_1.id,
        work_type="Crown",
        status="pending",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    # Order 2 linked to Treatment 2
    order_2 = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=treatment_2.id,
        work_type="Crown",
        status="pending",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add_all([order_1, order_2])
    await async_db_session.flush()

    # Attempt to re-point Order 2 to Treatment 1 -> 409
    update_payload = schemas.LabOrderUpdate(treatment_id=treatment_1.id)
    with pytest.raises(HTTPException) as exc_info:
        await update_lab_order(order_id=order_2.id, order_update=update_payload, db=async_db_session, current_user=test_user)
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_lab_order_valid_relink_and_cancelled_order_does_not_block(async_db_session, test_user, test_patient):
    """Cancelled existing order does not block relinking, and valid relink updates treatment_id."""
    from backend.routers.laboratories import update_lab_order

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    treatment_target = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown Target",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(treatment_target)
    await async_db_session.flush()

    # Pre-existing cancelled order linked to target treatment
    cancelled_order = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=treatment_target.id,
        work_type="Crown",
        status="cancelled",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    # Active order to be relinked
    active_order = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=None,
        work_type="Crown",
        status="pending",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add_all([cancelled_order, active_order])
    await async_db_session.flush()

    update_payload = schemas.LabOrderUpdate(treatment_id=treatment_target.id)
    res = await update_lab_order(order_id=active_order.id, order_update=update_payload, db=async_db_session, current_user=test_user)
    assert res["data"]["treatment_id"] == treatment_target.id


@pytest.mark.asyncio
async def test_update_lab_order_cannot_link_treatment_to_work_item_order_rejected_400(async_db_session, test_user, test_patient):
    """Never let an update link a treatment to an order that was created through the work_item path."""
    from backend.routers.laboratories import update_lab_order
    from fastapi import HTTPException

    lab = models.Laboratory(name="Dental Art Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.flush()

    treatment = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown Target",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(treatment)
    await async_db_session.flush()

    # Order created through work_item path
    work_item_order = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        work_item_id=77,
        treatment_id=None,
        work_type="Crown",
        status="pending",
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(work_item_order)
    await async_db_session.flush()

    update_payload = schemas.LabOrderUpdate(treatment_id=treatment.id)
    with pytest.raises(HTTPException) as exc_info:
        await update_lab_order(order_id=work_item_order.id, order_update=update_payload, db=async_db_session, current_user=test_user)
    assert exc_info.value.status_code == 400
    assert "Cannot link treatment to a work item lab order" in exc_info.value.detail


@pytest.mark.asyncio
async def test_deferred_lab_order_and_payment_roll_back_together(async_db_session, test_user, test_patient):
    """The caller can atomically roll back an order and its initial payment."""
    from backend.services.lab_service import LabService

    lab = models.Laboratory(name="Atomic Lab", tenant_id=test_user.tenant_id)
    async_db_session.add(lab)
    await async_db_session.commit()
    lab_id, patient_id, tenant_id, doctor_id = lab.id, test_patient.id, test_user.tenant_id, test_user.id
    service = LabService(async_db_session, tenant_id)
    order = await service.create_lab_order(
        schemas.LabOrderCreate(patient_id=patient_id, laboratory_id=lab_id, work_type="Crown", cost=Decimal("400"), paid_now=Decimal("100")),
        doctor_id=doctor_id,
        commit=False,
    )
    order_id = order.id
    assert (await async_db_session.execute(sa.select(sa.func.count(models.LabPayment.id)).where(models.LabPayment.lab_order_id == order_id))).scalar_one() == 1
    await async_db_session.rollback()
    assert (await async_db_session.execute(sa.select(models.LabOrder.id).where(models.LabOrder.id == order_id))).scalar_one_or_none() is None
    assert (await async_db_session.execute(sa.select(sa.func.count(models.LabPayment.id)).where(models.LabPayment.lab_order_id == order_id))).scalar_one() == 0
