"""Tests for Phase G12 / Slice S27: Lab Order work_item_id FK, Legacy Link Backfill & Optional Data.

Verifies:
1. G12-M01: LabOrder model has real work_item_id column referencing clinical_work_items.id,
   composite index ix_lab_orders_tenant_work_item, and bidirectional ORM relationships.
2. G12-M02 & G4-M08: Exact legacy lab link backfill in backfill_clinical_work_items.py Phase 5
   (dry-run, apply, idempotency, ambiguous duplicate link rejection, cross-tenant rejection).
3. G12-M03: Direct lab order creation with work_item_id via router/schema without note tokens.
4. G12-M07: Support for missing optional lab data (shade, material, tooth_number nullable).
5. Cross-tenant and cross-patient work_item_id validation in laboratories router.
6. CHILD_TENANT_RELATIONSHIPS lockstep configuration and deterministic trigger naming.
7. Alembic migration lifecycle upgrade, downgrade, and re-upgrade on ephemeral SQLite.
"""

from decimal import Decimal
import os
import tempfile
import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from alembic.config import Config
from alembic import command

from backend.database import Base
from backend.models.clinical import LabOrder, Laboratory, Treatment
from backend.models.clinical_core import ClinicalWorkItem
from backend.models.patient import Patient
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.schemas.laboratory import LabOrderCreate, LabOrderUpdate
from backend.scripts.preflight_migrations import (
    CHILD_TENANT_RELATIONSHIPS,
    _child_tenant_trigger_name,
)
from scripts.backfill_clinical_work_items import backfill_tenant


def test_child_tenant_relationships_lockstep_configuration():
    """Verify lab_orders.work_item_id is in CHILD_TENANT_RELATIONSHIPS in lockstep."""
    config_entry = next(
        (rel for rel in CHILD_TENANT_RELATIONSHIPS if rel[0] == "lab_orders" and rel[1] == "work_item_id"),
        None,
    )
    assert config_entry is not None, "Missing lab_orders.work_item_id in CHILD_TENANT_RELATIONSHIPS"
    table, key, parent, allow_null = config_entry
    assert table == "lab_orders"
    assert key == "work_item_id"
    assert parent == "clinical_work_items"
    assert allow_null is True

    # Trigger name must follow convention and remain <= 63 bytes for PostgreSQL
    trg_name = _child_tenant_trigger_name(table, key)
    assert trg_name == "trg_lab_orders_work_item_id_parent_tenant"
    assert len(trg_name.encode("utf-8")) <= 63

    # Metadata parity check
    table_meta = Base.metadata.tables["lab_orders"]
    assert "work_item_id" in table_meta.columns
    col = table_meta.columns["work_item_id"]
    assert col.nullable is True
    fk_targets = [fk.column.table.name for fk in col.foreign_keys]
    assert "clinical_work_items" in fk_targets


def test_g12_m01_lab_order_work_item_fk_and_relationships():
    """Verify LabOrder has work_item_id and ORM relationship with ClinicalWorkItem."""
    col = LabOrder.__table__.columns.get("work_item_id")
    assert col is not None, "LabOrder.work_item_id column must exist"
    assert col.nullable is True, "LabOrder.work_item_id must be nullable"

    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    assert "clinical_work_items.id" in fk_targets, "LabOrder.work_item_id must reference clinical_work_items.id"

    # Index check
    index_names = {idx.name for idx in LabOrder.__table__.indexes}
    assert "ix_lab_orders_tenant_work_item" in index_names, "Composite index ix_lab_orders_tenant_work_item must exist"

    # Relationship check
    assert hasattr(LabOrder, "work_item"), "LabOrder must have work_item relationship"
    assert hasattr(ClinicalWorkItem, "lab_orders"), "ClinicalWorkItem must have lab_orders relationship"


def test_g12_m07_allow_missing_optional_lab_data():
    """Verify LabOrder schema and model allow missing optional fields (shade, material, tooth_number)."""
    # Schema validation
    order_in = LabOrderCreate(
        patient_id=1,
        laboratory_id=1,
        work_type="Crown",
        tooth_number=None,
        shade=None,
        material=None,
        cost=Decimal("150.00"),
        price_to_patient=Decimal("300.00"),
    )
    assert order_in.tooth_number is None
    assert order_in.shade is None
    assert order_in.material is None
    assert order_in.work_item_id is None

    # Model attributes
    lo = LabOrder(
        tenant_id=1,
        patient_id=1,
        laboratory_id=1,
        work_type="Crown",
        tooth_number=None,
        shade=None,
        material=None,
        cost=Decimal("150.00"),
        price_to_patient=Decimal("300.00"),
    )
    assert lo.tooth_number is None
    assert lo.shade is None
    assert lo.material is None


@pytest.mark.asyncio
async def test_g12_m02_and_g4_m08_exact_legacy_lab_link_backfill(async_db_session):
    """Verify Phase 5 backfill correctly links legacy LabOrders to ClinicalWorkItems."""
    db = async_db_session

    tenant = Tenant(name="Lab Backfill Clinic", is_active=True, is_deleted=False)
    db.add(tenant)
    await db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        name="Sarah Jenkins",
        age=30,
        phone="0123456789",
        medical_history="None",
        notes="",
        is_deleted=False,
    )
    db.add(patient)
    await db.flush()

    doctor = User(
        tenant_id=tenant.id,
        username="dr_smith",
        email="smith@clinic.com",
        hashed_password="fakehash",
        role="doctor",
    )
    db.add(doctor)
    await db.flush()

    lab = Laboratory(tenant_id=tenant.id, name="Modern Dental Lab")
    db.add(lab)
    await db.flush()

    # 1. Create legacy LabOrder #1 with matching Treatment having "Link:LabOrder:<id>"
    lab_order_1 = LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        laboratory_id=lab.id,
        doctor_id=doctor.id,
        work_type="Crown",
        tooth_number="16",
        shade="A2",
        material="Zirconia",
        cost=Decimal("200.00"),
        price_to_patient=Decimal("500.00"),
        status="pending",
    )
    db.add(lab_order_1)
    await db.flush()

    treatment_1 = Treatment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        tooth_number=16,
        procedure="Crown",
        cost=500.0,
        discount=0.0,
        notes=f"Link:LabOrder:{lab_order_1.id}",
    )
    db.add(treatment_1)
    await db.flush()

    # 2. Create legacy LabOrder #2 with NO matching treatment (should be skipped)
    lab_order_2 = LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        laboratory_id=lab.id,
        doctor_id=doctor.id,
        work_type="Denture",
        cost=Decimal("300.00"),
        status="pending",
    )
    db.add(lab_order_2)

    # 3. Create legacy LabOrder #3 with ambiguous duplicate treatments (should be skipped)
    lab_order_3 = LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        laboratory_id=lab.id,
        doctor_id=doctor.id,
        work_type="Bridge",
        cost=Decimal("400.00"),
        status="pending",
    )
    db.add(lab_order_3)
    await db.flush()

    dup_tx_1 = Treatment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        tooth_number=21,
        procedure="Crown",
        notes=f"Link:LabOrder:{lab_order_3.id}",
    )
    dup_tx_2 = Treatment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        tooth_number=22,
        procedure="Crown",
        notes=f"Link:LabOrder:{lab_order_3.id}",
    )
    db.add_all([dup_tx_1, dup_tx_2])
    await db.commit()

    # Test Dry-Run Mode
    report_dry = await backfill_tenant(db, tenant_id=tenant.id, apply=False)
    assert report_dry.lab_orders_scanned >= 3
    assert report_dry.lab_orders_created == 1  # only lab_order_1 is exact match
    assert report_dry.lab_orders_skipped >= 2

    # Verify dry-run did not mutate DB
    await db.refresh(lab_order_1)
    assert lab_order_1.work_item_id is None

    # Test Apply Mode
    report_apply = await backfill_tenant(db, tenant_id=tenant.id, apply=True)
    assert report_apply.lab_orders_created == 1

    # Verify DB was persisted
    await db.refresh(lab_order_1)
    assert lab_order_1.work_item_id is not None

    # Verify the linked work item belongs to this patient and tooth 16
    wi = await db.get(ClinicalWorkItem, lab_order_1.work_item_id)
    assert wi is not None
    assert wi.patient_id == patient.id
    assert wi.tenant_id == tenant.id

    # Test Idempotency: re-running apply immediately reports already synced
    report_idempotent = await backfill_tenant(db, tenant_id=tenant.id, apply=True)
    assert report_idempotent.lab_orders_created == 0
    assert report_idempotent.lab_orders_already_synced >= 1


@pytest.mark.asyncio
async def test_g12_m03_native_lab_order_with_work_item(async_db_session):
    """Verify creating a LabOrder directly with work_item_id without note tokens."""
    db = async_db_session

    tenant = Tenant(name="Native Lab Clinic", is_active=True, is_deleted=False)
    db.add(tenant)
    await db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        name="Robert Brown",
        age=45,
        phone="0123456788",
        medical_history="None",
        notes="",
        is_deleted=False,
    )
    db.add(patient)
    await db.flush()

    lab = Laboratory(tenant_id=tenant.id, name="City Lab")
    db.add(lab)
    await db.flush()

    wi = ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
    )
    db.add(wi)
    await db.flush()

    # Direct native creation with work_item_id
    order = LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        laboratory_id=lab.id,
        work_item_id=wi.id,
        work_type="Crown",
        shade="A1",
        cost=Decimal("180.00"),
        status="pending",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    assert order.work_item_id == wi.id

    reloaded_wi = (
        await db.execute(
            select(ClinicalWorkItem)
            .options(selectinload(ClinicalWorkItem.lab_orders))
            .where(ClinicalWorkItem.id == wi.id)
        )
    ).scalars().first()
    assert reloaded_wi is not None
    assert any(lo.id == order.id for lo in reloaded_wi.lab_orders)


@pytest.mark.asyncio
async def test_cross_tenant_and_cross_patient_work_item_rejection(async_db_session):
    """Verify that referencing a work item from another tenant or patient is rejected."""
    from fastapi import HTTPException
    from backend.routers.laboratories import create_lab_order, update_lab_order

    db = async_db_session

    tenant_a = Tenant(name="Clinic A", is_active=True, is_deleted=False)
    tenant_b = Tenant(name="Clinic B", is_active=True, is_deleted=False)
    db.add_all([tenant_a, tenant_b])
    await db.flush()

    patient_a = Patient(
        tenant_id=tenant_a.id,
        name="Patient A",
        age=25,
        phone="0123456781",
        medical_history="None",
        notes="",
        is_deleted=False,
    )
    patient_b = Patient(
        tenant_id=tenant_a.id,
        name="Patient B",
        age=28,
        phone="0123456782",
        medical_history="None",
        notes="",
        is_deleted=False,
    )
    db.add_all([patient_a, patient_b])
    await db.flush()

    lab_a = Laboratory(tenant_id=tenant_a.id, name="Lab A")
    db.add(lab_a)
    await db.flush()

    wi_tenant_b = ClinicalWorkItem(
        tenant_id=tenant_b.id,
        patient_id=1,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
    )
    wi_patient_b = ClinicalWorkItem(
        tenant_id=tenant_a.id,
        patient_id=patient_b.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
    )
    db.add_all([wi_tenant_b, wi_patient_b])
    await db.commit()

    doctor_user = User(
        tenant_id=tenant_a.id,
        username="doc_a",
        email="doc_a@example.com",
        hashed_password="fakehash",
        role="doctor",
    )

    # Enable native writes for tenant_a so work_item_id is allowed to reach validation
    from backend.models.system import FeatureFlag
    from backend.services.feature_service import FeatureFlagService
    from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES

    stmt_ff = select(FeatureFlag).where(FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES)
    flag = (await db.execute(stmt_ff)).scalar_one_or_none()
    if not flag:
        flag = FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Clinical native writes",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        db.add(flag)
        await db.flush()
    await FeatureFlagService.set_tenant_override(db, tenant_a.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)
    await db.commit()

    # 1. Create with cross-tenant work_item_id -> 404
    order_create_cross_tenant = LabOrderCreate(
        patient_id=patient_a.id,
        laboratory_id=lab_a.id,
        work_item_id=wi_tenant_b.id,
        work_type="Crown",
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_lab_order(order=order_create_cross_tenant, db=db, current_user=doctor_user)
    assert exc_info.value.status_code == 404
    assert "work item" in exc_info.value.detail.lower()

    # 2. Create with cross-patient work_item_id -> 404
    order_create_cross_patient = LabOrderCreate(
        patient_id=patient_a.id,
        laboratory_id=lab_a.id,
        work_item_id=wi_patient_b.id,
        work_type="Crown",
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_lab_order(order=order_create_cross_patient, db=db, current_user=doctor_user)
    assert exc_info.value.status_code == 404
    assert "work item" in exc_info.value.detail.lower()

    # 3. Update with cross-tenant work_item_id -> 404
    valid_order = LabOrder(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        laboratory_id=lab_a.id,
        work_type="Crown",
    )
    db.add(valid_order)
    await db.commit()
    await db.refresh(valid_order)

    order_update = LabOrderUpdate(work_item_id=wi_tenant_b.id)
    with pytest.raises(HTTPException) as exc_info:
        await update_lab_order(order_id=valid_order.id, order_update=order_update, db=db, current_user=doctor_user)
    assert exc_info.value.status_code == 404
    assert "work item" in exc_info.value.detail.lower()


def test_alembic_s27_migration_lifecycle_sqlite(monkeypatch):
    """Rehearse Alembic migration 3c4d5e6f7a8b upgrade and downgrade on SQLite."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        engine = sa.create_engine(sqlite_url)
        alembic_cfg_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
        )
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Create base tables needed for lab_orders
        with engine.connect() as conn:
            # Head also migrates users.email; keep the legacy prerequisite schema realistic.
            conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"))
            conn.execute(sa.text("CREATE UNIQUE INDEX ix_users_email ON users(email)"))
            conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY, name VARCHAR)"))
            conn.execute(sa.text("CREATE TABLE patients (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE laboratories (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE clinical_work_items (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE treatments (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(
                sa.text(
                    """CREATE TABLE lab_orders (
                        id INTEGER PRIMARY KEY,
                        patient_id INTEGER,
                        laboratory_id INTEGER,
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

        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE user_sessions (id INTEGER PRIMARY KEY, user_id INTEGER, token_hash VARCHAR, ip_address VARCHAR, user_agent VARCHAR, device_info VARCHAR, last_active_at DATETIME, expires_at DATETIME, is_active BOOLEAN, created_at DATETIME)"))
            conn.execute(sa.text("INSERT INTO user_sessions (id, user_id, token_hash, is_active) VALUES (1, 1, 'old-session', 1)"))

        # 2. Stamp at 2b3c4d5e6f7a (parent revision)
        command.stamp(config, "2b3c4d5e6f7a")

        # 3. Upgrade to 3c4d5e6f7a8b
        command.upgrade(config, "3c4d5e6f7a8b")

        # Verify upgraded schema
        inspector = sa.inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("lab_orders")}
        assert "work_item_id" in cols, "work_item_id must be added to lab_orders"
        assert cols["work_item_id"]["nullable"] is True, "work_item_id must be nullable"

        indexes = {ix["name"] for ix in inspector.get_indexes("lab_orders")}
        assert "ix_lab_orders_work_item_id" in indexes
        assert "ix_lab_orders_tenant_work_item" in indexes

        # 4. Downgrade back to 2b3c4d5e6f7a
        command.downgrade(config, "2b3c4d5e6f7a")

        inspector = sa.inspect(engine)
        downgraded_cols = {c["name"]: c for c in inspector.get_columns("lab_orders")}
        assert "work_item_id" not in downgraded_cols, "work_item_id must be dropped on downgrade"
        downgraded_indexes = {ix["name"] for ix in inspector.get_indexes("lab_orders")}
        assert "ix_lab_orders_work_item_id" not in downgraded_indexes
        assert "ix_lab_orders_tenant_work_item" not in downgraded_indexes

        # 5. Re-upgrade to head
        command.upgrade(config, "head")
        inspector = sa.inspect(engine)
        reupgraded_cols = {c["name"] for c in inspector.get_columns("lab_orders")}
        assert "work_item_id" in reupgraded_cols

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
