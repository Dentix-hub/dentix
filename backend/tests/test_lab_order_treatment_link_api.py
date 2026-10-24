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

    # Post-count treatments: must NOT have created a synthetic treatment!
    res_after = await async_db_session.execute(
        sa.select(sa.func.count(models.Treatment.id)).where(models.Treatment.tenant_id == test_user.tenant_id)
    )
    count_after = res_after.scalar()
    assert count_after == count_before, "Must NOT auto-create a synthetic Treatment when treatment_id is given!"

    # Idempotency test: posting again for same treatment returns existing order
    res_idempotent = await create_lab_order(order=order_payload, db=async_db_session, current_user=test_user)
    assert res_idempotent["data"]["id"] == res["data"]["id"]


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
