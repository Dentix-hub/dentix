"""
Tests for Phase G13 / Slice S26: Inventory Usage care_session_id Schema & History Preservation.

Covers:
- G13-M01: Distinguish material session from care session
- G13-M02: Add care_session_id and work_item_id to TreatmentMaterialUsage model
- G13-M03: Preserve legacy usage data with nullable care_session_id
- PD07: CheckConstraint ck_tmu_treatment_or_care_session_required
- Schema relationship integrity between CareSession and TreatmentMaterialUsage
- Preflight CHILD_TENANT_RELATIONSHIPS configuration and lockstep trigger definitions
- Migration upgrade and downgrade on ephemeral SQLite database
"""

import os
import tempfile
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from decimal import Decimal

from backend.models import (
    Base,
    Tenant,
    Patient,
    User,
    CareSession,
    ClinicalWorkItem,
    Treatment,
    Material,
    MaterialSession,
    TreatmentMaterialUsage,
    Warehouse,
    StockItem,
)
from backend.scripts.preflight_migrations import (
    CHILD_TENANT_RELATIONSHIPS,
    _child_tenant_trigger_name,
)
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command


@pytest.fixture
def db_session(engine):
    """Sync session for model contract tests."""
    with Session(engine) as session:
        yield session


def test_child_tenant_relationships_lockstep_configuration():
    """Verify preflight CHILD_TENANT_RELATIONSHIPS config for treatment_material_usages."""
    tmu_relationships = [
        (table, col, parent, allow_null)
        for table, col, parent, allow_null in CHILD_TENANT_RELATIONSHIPS
        if table == "treatment_material_usages"
    ]

    expected = {
        ("treatment_material_usages", "care_session_id", "care_sessions", True),
        ("treatment_material_usages", "work_item_id", "clinical_work_items", True),
    }

    assert expected.issubset(set(tmu_relationships)), (
        f"CHILD_TENANT_RELATIONSHIPS must contain care_session_id and work_item_id links. Found: {tmu_relationships}"
    )

    # Verify trigger names match canonical naming
    cs_trg = _child_tenant_trigger_name("treatment_material_usages", "care_session_id")
    wi_trg = _child_tenant_trigger_name("treatment_material_usages", "work_item_id")
    assert cs_trg == "trg_treatment_material_usages_care_session_id_parent_tenant"
    assert wi_trg == "trg_treatment_material_usages_work_item_id_parent_tenant"


def test_g13_m01_distinguish_material_session_from_care_session():
    """G13-M01: Verify architectural distinction between MaterialSession and CareSession."""
    # MaterialSession: inventory domain grouping for divisible material weights
    assert MaterialSession.__tablename__ == "material_sessions"
    assert hasattr(MaterialSession, "stock_item_id")
    assert hasattr(MaterialSession, "opened_at")
    assert hasattr(MaterialSession, "closed_at")

    # CareSession: clinical chairside care encounter
    assert CareSession.__tablename__ == "care_sessions"
    assert hasattr(CareSession, "started_at")
    assert hasattr(CareSession, "finished_at")
    assert hasattr(CareSession, "steps")
    assert hasattr(CareSession, "observations")

    # TreatmentMaterialUsage links to both distinctly
    tmu_table = Base.metadata.tables["treatment_material_usages"]
    assert "session_id" in tmu_table.c, "session_id (MaterialSession) must exist"
    assert "care_session_id" in tmu_table.c, "care_session_id (CareSession) must exist"

    session_fk = [fk.target_fullname for fk in tmu_table.c["session_id"].foreign_keys]
    assert "material_sessions.id" in session_fk

    care_session_fk = [fk.target_fullname for fk in tmu_table.c["care_session_id"].foreign_keys]
    assert "care_sessions.id" in care_session_fk


def test_g13_m02_native_care_session_usage_creation(db_session: Session):
    """G13-M02: Creating TreatmentMaterialUsage with care_session_id without legacy treatment."""
    tenant = Tenant(name="S26 Care Session Clinic")
    db_session.add(tenant)
    db_session.flush()

    patient = Patient(
        tenant_id=tenant.id,
        name="S26 Patient CS",
        age=30,
        phone="01012345678",
        medical_history="None",
        notes="",
    )
    material = Material(
        tenant_id=tenant.id,
        name="Composite Resin A2",
        type="DIVISIBLE",
        base_unit="g",
        standard_price=Decimal("150.00"),
    )
    db_session.add_all([patient, material])
    db_session.flush()

    care_session = CareSession(
        tenant_id=tenant.id,
        patient_id=patient.id,
        status="in_progress",
        notes="Session with material consumption",
    )
    db_session.add(care_session)
    db_session.flush()

    work_item = ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
    )
    db_session.add(work_item)
    db_session.flush()

    # Create usage linked to native CareSession and WorkItem with treatment_id=None
    usage = TreatmentMaterialUsage(
        tenant_id=tenant.id,
        treatment_id=None,
        care_session_id=care_session.id,
        work_item_id=work_item.id,
        material_id=material.id,
        weight_score=1.5,
        quantity_used=0.75,
        cost_calculated=Decimal("112.50"),
    )
    db_session.add(usage)
    db_session.commit()

    # Verify persistence and relationships
    saved_usage = db_session.get(TreatmentMaterialUsage, usage.id)
    assert saved_usage is not None
    assert saved_usage.treatment_id is None
    assert saved_usage.care_session_id == care_session.id
    assert saved_usage.work_item_id == work_item.id
    assert saved_usage.cost_calculated == Decimal("112.50")
    assert saved_usage.care_session.id == care_session.id
    assert saved_usage.work_item.id == work_item.id

    # Verify back-populated relationship on CareSession
    db_session.refresh(care_session)
    assert len(care_session.material_usages) >= 1
    assert saved_usage in care_session.material_usages


def test_g13_m03_legacy_usage_history_preservation(db_session: Session):
    """G13-M03: Legacy usage rows with treatment_id and care_session_id=None remain valid."""
    tenant = Tenant(name="S26 Legacy Clinic")
    db_session.add(tenant)
    db_session.flush()

    patient = Patient(
        tenant_id=tenant.id,
        name="S26 Legacy Patient",
        age=45,
        phone="01098765432",
        medical_history="None",
        notes="",
    )
    material = Material(
        tenant_id=tenant.id,
        name="Amalgam Alloy",
        type="NON_DIVISIBLE",
        base_unit="capsule",
        standard_price=Decimal("50.00"),
    )
    treatment = Treatment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        procedure="Amalgam Restoration",
        cost=Decimal("200.00"),
        status="Completed",
    )
    db_session.add_all([patient, material, treatment])
    db_session.flush()

    # Legacy usage: treatment_id set, care_session_id None, work_item_id None
    legacy_usage = TreatmentMaterialUsage(
        tenant_id=tenant.id,
        treatment_id=treatment.id,
        care_session_id=None,
        work_item_id=None,
        material_id=material.id,
        weight_score=1.0,
        quantity_used=1.0,
        cost_calculated=Decimal("50.00"),
    )
    db_session.add(legacy_usage)
    db_session.commit()

    saved_legacy = db_session.get(TreatmentMaterialUsage, legacy_usage.id)
    assert saved_legacy is not None
    assert saved_legacy.treatment_id == treatment.id
    assert saved_legacy.care_session_id is None
    assert saved_legacy.work_item_id is None
    assert saved_legacy.treatment.id == treatment.id


def test_pd07_check_constraint_rejects_both_null(db_session: Session):
    """PD07: ck_tmu_treatment_or_care_session_required rejects rows where both are NULL."""
    tenant = Tenant(name="S26 Constraint Clinic")
    db_session.add(tenant)
    db_session.flush()

    material = Material(
        tenant_id=tenant.id,
        name="Etching Gel",
        type="DIVISIBLE",
        base_unit="ml",
    )
    db_session.add(material)
    db_session.flush()

    invalid_usage = TreatmentMaterialUsage(
        tenant_id=tenant.id,
        treatment_id=None,
        care_session_id=None,
        material_id=material.id,
        weight_score=1.0,
    )
    db_session.add(invalid_usage)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    db_session.rollback()
    assert "ck_tmu_treatment_or_care_session_required" in str(exc_info.value).lower() or (
        "check constraint" in str(exc_info.value).lower()
    )


def test_alembic_s26_migration_lifecycle_sqlite(monkeypatch):
    """Rehearse Alembic migration 2b3c4d5e6f7a upgrade and downgrade on SQLite."""
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

        # 1. Create base tables needed for treatment_material_usages
        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY, name VARCHAR)"))
            conn.execute(sa.text("CREATE TABLE treatments (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE materials (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE material_sessions (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE care_sessions (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE clinical_work_items (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(
                sa.text(
                    """CREATE TABLE treatment_material_usages (
                        id INTEGER PRIMARY KEY,
                        treatment_id INTEGER NOT NULL,
                        material_id INTEGER NOT NULL,
                        session_id INTEGER,
                        weight_score FLOAT DEFAULT 1.0,
                        quantity_used FLOAT,
                        cost_calculated NUMERIC(18, 6),
                        is_manual_override BOOLEAN DEFAULT 0,
                        tenant_id INTEGER NOT NULL,
                        created_at TIMESTAMP
                    )"""
                )
            )
            conn.commit()

        # 2. Stamp at 1a2b3c4d5e6f (parent revision)
        command.stamp(config, "1a2b3c4d5e6f")

        # 3. Upgrade to 2b3c4d5e6f7a
        command.upgrade(config, "2b3c4d5e6f7a")

        # Verify upgraded schema
        inspector = sa.inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("treatment_material_usages")}
        assert "care_session_id" in cols, "care_session_id must be added"
        assert "work_item_id" in cols, "work_item_id must be added"
        assert cols["treatment_id"]["nullable"] is True, "treatment_id must be nullable"

        # 4. Downgrade back to 1a2b3c4d5e6f
        command.downgrade(config, "1a2b3c4d5e6f")

        inspector = sa.inspect(engine)
        downgraded_cols = {c["name"]: c for c in inspector.get_columns("treatment_material_usages")}
        assert "care_session_id" not in downgraded_cols, "care_session_id must be dropped on downgrade"
        assert "work_item_id" not in downgraded_cols, "work_item_id must be dropped on downgrade"
        assert downgraded_cols["treatment_id"]["nullable"] is False, "treatment_id must revert to NOT NULL"

        # 5. Re-upgrade to head
        command.upgrade(config, "head")
        inspector = sa.inspect(engine)
        reupgraded_cols = {c["name"] for c in inspector.get_columns("treatment_material_usages")}
        assert "care_session_id" in reupgraded_cols
        assert "work_item_id" in reupgraded_cols

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
