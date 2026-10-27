"""
Tests for Phase G14 / Slice S32: Billing Policy Model & ``clinical_charges`` ledger table.

Verifies:
1. Billing policy constants (D1): statuses and `pending` default.
2. Table structure: non-nullable tenant_id/patient_id/work_item_id/amount, defaults.
3. Check constraints: amount >= 0, discount >= 0, discount <= amount, status allowlist.
4. Partial unique index: one non-voided charge per (tenant, work item); voided rows allowed.
5. Explicit tenant isolation: tenant-scoped queries never return another clinic's charges,
   RLS policy declared and registered in preflight, tenant/patient trigger lockstep.
6. Patient/tenant hard-delete ordering removes charges before their parents.
7. Alembic: single head 5e6f7a8b9c0d, upgrade/downgrade symmetry, ORM <-> migration parity.
8. Legacy finance tables (treatments, payments) untouched.
"""

import os
import tempfile
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import crud
from backend.models import (
    Base,
    CareSession,
    ClinicalCharge,
    ClinicalWorkItem,
    Patient,
    Tenant,
    Treatment,
    User,
)
from backend.models.clinical_core import (
    CLINICAL_CHARGE_STATUSES,
    CLINICAL_CHARGE_STATUS_PENDING,
)
from backend.scripts.preflight_migrations import (
    CHILD_TENANT_RELATIONSHIPS,
    CLINICAL_CHARGES_DIRECT_PARENT_PATIENT_RELATIONSHIPS,
    CLINICAL_G1_TABLES,
    RLS_TABLES,
    _child_patient_trigger_name,
    _child_tenant_trigger_name,
    _get_clinical_charges_patient_triggers,
)

MIGRATION_MODULE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "alembic", "versions", "5e6f7a8b9c0d_add_clinical_charges.py"
    )
)


@pytest.fixture
def charges_engine():
    eng = sa.create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    with Session(eng) as s:
        s.add_all([Tenant(id=1, name="Clinic 1"), Tenant(id=2, name="Clinic 2")])
        s.flush()
        s.add_all(
            [
                User(id=1, tenant_id=1, username="d1", email="d1@x.com", hashed_password="x", role="doctor"),
                User(id=2, tenant_id=2, username="d2", email="d2@x.com", hashed_password="x", role="doctor"),
            ]
        )
        for pid, tid in ((10, 1), (20, 2)):
            s.add(
                Patient(
                    id=pid, tenant_id=tid, name=f"P{pid}", age=30, phone=f"0100000{pid}",
                    medical_history="", notes="",
                )
            )
        s.flush()
        for wid, tid, pid in ((100, 1, 10), (101, 1, 10), (200, 2, 20)):
            s.add(
                ClinicalWorkItem(
                    id=wid, tenant_id=tid, patient_id=pid, kind="procedure",
                    code="REST_COMPOSITE", status="active",
                )
            )
        s.commit()
    yield eng
    eng.dispose()


def _charge(**overrides):
    base = dict(tenant_id=1, patient_id=10, work_item_id=100, amount=Decimal("500.00"))
    base.update(overrides)
    return ClinicalCharge(**base)


def test_billing_policy_constants_and_table_structure():
    assert CLINICAL_CHARGE_STATUSES == ("pending", "invoiced", "voided")
    assert CLINICAL_CHARGE_STATUS_PENDING == "pending"

    table = Base.metadata.tables["clinical_charges"]
    for name in ("tenant_id", "patient_id", "work_item_id", "amount", "discount", "status"):
        assert table.c[name].nullable is False, name
    for name in ("care_session_id", "doctor_id", "legacy_treatment_id", "notes"):
        assert table.c[name].nullable is True, name
    assert table.c.tenant_id.index is True
    assert {fk.column.table.name for fk in table.c.tenant_id.foreign_keys} == {"tenants"}
    assert isinstance(table.c.amount.type, sa.Numeric)
    assert (table.c.amount.type.precision, table.c.amount.type.scale) == (14, 2)
    assert (table.c.discount.type.precision, table.c.discount.type.scale) == (14, 2)


def test_defaults_status_pending_discount_zero_version_one(charges_engine):
    with Session(charges_engine) as s:
        charge = _charge()
        s.add(charge)
        s.commit()
        s.refresh(charge)
        assert charge.status == "pending"
        assert charge.discount == Decimal("0.00")
        assert charge.version_id == 1
        assert charge.care_session_id is None and charge.legacy_treatment_id is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": Decimal("-1.00")},
        {"discount": Decimal("-0.01")},
        {"amount": Decimal("100.00"), "discount": Decimal("100.01")},
        {"status": "paid"},
        {"status": ""},
    ],
)
def test_check_constraints_reject_invalid_rows(charges_engine, overrides):
    with Session(charges_engine) as s:
        s.add(_charge(**overrides))
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()


def test_check_constraints_accept_boundaries(charges_engine):
    with Session(charges_engine) as s:
        s.add(_charge(work_item_id=100, amount=Decimal("0.00"), discount=Decimal("0.00")))
        s.add(_charge(work_item_id=101, amount=Decimal("250.00"), discount=Decimal("250.00")))
        s.commit()


def test_one_active_charge_per_work_item_but_voided_allowed(charges_engine):
    with Session(charges_engine) as s:
        s.add(_charge(status="voided"))
        s.add(_charge(status="voided"))
        s.add(_charge(status="pending"))
        s.commit()

        s.add(_charge(status="invoiced"))
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()

        # Same work item id under another tenant's scope is a different (tenant, work item).
        s.add(_charge(tenant_id=2, patient_id=20, work_item_id=200))
        s.commit()


def test_tenant_scoped_queries_never_return_other_tenant_charges(charges_engine):
    """Explicit tenant isolation test for the new tenant-scoped table."""
    with Session(charges_engine) as s:
        s.add_all(
            [
                _charge(work_item_id=100, amount=Decimal("100.00")),
                _charge(tenant_id=2, patient_id=20, work_item_id=200, amount=Decimal("999.00")),
            ]
        )
        s.commit()

        t1_rows = s.execute(
            sa.select(ClinicalCharge).where(ClinicalCharge.tenant_id == 1)
        ).scalars().all()
        t2_rows = s.execute(
            sa.select(ClinicalCharge).where(ClinicalCharge.tenant_id == 2)
        ).scalars().all()
        assert [c.amount for c in t1_rows] == [Decimal("100.00")]
        assert [c.amount for c in t2_rows] == [Decimal("999.00")]
        assert all(c.patient_id == 10 for c in t1_rows)
        assert all(c.patient_id == 20 for c in t2_rows)


def test_rls_policy_and_preflight_registration():
    assert ClinicalCharge.__rls_policies__, "clinical_charges must declare a tenant RLS policy"
    assert "clinical_charges" in RLS_TABLES
    # Must NOT leak into the G1 table tuple (locked in parity with migration f4a5b6c7d8e9).
    assert "clinical_charges" not in CLINICAL_G1_TABLES


def test_preflight_relationship_lockstep_with_models_and_migration():
    table = Base.metadata.tables["clinical_charges"]
    fk_columns = {
        fk.parent.name: fk.column.table.name
        for fk in table.foreign_keys
        if fk.column.table.name != "tenants"
    }
    preflight = {
        (child, parent): allow_null
        for tbl, child, parent, allow_null in CHILD_TENANT_RELATIONSHIPS
        if tbl == "clinical_charges"
    }
    assert {(c, p) for c, p in fk_columns.items()} == set(preflight)
    for child, _ in preflight:
        assert preflight[(child, fk_columns[child])] == table.c[child].nullable

    patient_rels = {
        (child, parent, allow_null)
        for _, child, parent, allow_null in CLINICAL_CHARGES_DIRECT_PARENT_PATIENT_RELATIONSHIPS
    }
    assert patient_rels == {
        ("work_item_id", "clinical_work_items", False),
        ("care_session_id", "care_sessions", True),
    }

    assert _get_clinical_charges_patient_triggers() == {
        _child_patient_trigger_name("clinical_charges", child)
        for _, child, _, _ in CLINICAL_CHARGES_DIRECT_PARENT_PATIENT_RELATIONSHIPS
    }

    with open(MIGRATION_MODULE_PATH, "r", encoding="utf-8") as f:
        migration_src = f.read()
    for tbl, child, parent, allow_null in CHILD_TENANT_RELATIONSHIPS:
        if tbl != "clinical_charges":
            continue
        assert f'("{child}", "{parent}", {allow_null})' in migration_src
        assert _child_tenant_trigger_name(tbl, child) == f"trg_clinical_charges_{child}_parent_tenant"
    for tbl, child, parent, allow_null in CLINICAL_CHARGES_DIRECT_PARENT_PATIENT_RELATIONSHIPS:
        assert f'("{child}", "{parent}", {allow_null})' in migration_src

    for needle in (
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
        "clinical_charges_tenant_policy",
        "dentix_assert_parent_tenant",
        "dentix_assert_parent_patient",
    ):
        assert needle in migration_src or needle.replace("clinical_charges", "{TABLE}") in migration_src


def test_hard_delete_orders_remove_charges_before_parents():
    for order in (crud.patient.PATIENT_CLINICAL_DELETE_ORDER, crud.patient.TENANT_CLINICAL_DELETE_ORDER):
        idx = order.index(ClinicalCharge)
        assert idx < order.index(ClinicalWorkItem)
        assert idx < order.index(CareSession)


def test_patient_clinical_delete_clears_charges(charges_engine):
    with Session(charges_engine) as s:
        s.add(_charge())
        s.commit()
        for model in crud.patient.PATIENT_CLINICAL_DELETE_ORDER:
            s.execute(sa.delete(model).where(model.tenant_id == 1, model.patient_id == 10))
        s.execute(sa.delete(Patient).where(Patient.id == 10, Patient.tenant_id == 1))
        s.commit()
        assert s.execute(sa.select(sa.func.count(ClinicalCharge.id))).scalar_one() == 0


def test_legacy_finance_tables_unchanged():
    treatment_cols = {c.name for c in Base.metadata.tables["treatments"].columns}
    assert "clinical_charge_id" not in treatment_cols
    assert "clinical_charges" not in {fk.column.table.name for fk in Base.metadata.tables["payments"].foreign_keys}
    assert Treatment.__tablename__ == "treatments"


def test_alembic_single_head_is_s32():
    alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    script_dir = ScriptDirectory.from_config(Config(alembic_cfg_path))
    assert script_dir.get_heads() == ["d42a71e9bc83"]
    assert script_dir.get_revision("d42a71e9bc83").down_revision == "c38f91a2d47b"
    assert script_dir.get_revision("c38f91a2d47b").down_revision == "ba7526e3a901"
    assert script_dir.get_revision("ba7526e3a901").down_revision == "9ab047d5613e"
    assert script_dir.get_revision("9ab047d5613e").down_revision == "ed137fa8c304"
    assert script_dir.get_revision("ed137fa8c304").down_revision == "1e2f3a4b5c6d"
    assert script_dir.get_revision("1e2f3a4b5c6d").down_revision == "0d1e2f3a4b5c"
    assert script_dir.get_revision("0d1e2f3a4b5c").down_revision == "9c0d1e2f3a4b"
    assert script_dir.get_revision("9c0d1e2f3a4b").down_revision == "8b9c0d1e2f3a"
    assert script_dir.get_revision("8b9c0d1e2f3a").down_revision == "7a8b9c0d1e2f"
    assert script_dir.get_revision("7a8b9c0d1e2f").down_revision == "6f7a8b9c0d1e"
    assert script_dir.get_revision("6f7a8b9c0d1e").down_revision == "5e6f7a8b9c0d"
    assert script_dir.get_revision("5e6f7a8b9c0d").down_revision == "4d5e6f7a8b9c"


def test_alembic_s32_upgrade_downgrade_and_orm_parity(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name
    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        eng = sa.create_engine(sqlite_url)
        try:
            # Parent-schema baseline: every ORM table except the one S32 adds.
            Base.metadata.create_all(
                bind=eng,
                tables=[t for n, t in Base.metadata.tables.items() if n not in {"clinical_charges", "tenant_data_operations"}],
            )
            with eng.begin() as conn:
                conn.execute(sa.text("ALTER TABLE user_sessions DROP COLUMN remember_me"))
                conn.execute(sa.text("DROP INDEX uq_treatment_tenant_request_key"))
                conn.execute(sa.text("ALTER TABLE treatments DROP COLUMN request_key"))
                conn.execute(sa.text("ALTER TABLE treatments DROP COLUMN request_fingerprint"))
                conn.execute(sa.text("ALTER TABLE treatments DROP COLUMN lab_choice"))
                conn.execute(sa.text("ALTER TABLE clinical_work_items DROP COLUMN lab_choice"))
            command.stamp(config, "4d5e6f7a8b9c")
            assert "clinical_charges" not in sa.inspect(eng).get_table_names()

            command.upgrade(config, "head")
            inspector = sa.inspect(eng)
            assert "clinical_charges" in inspector.get_table_names()

            migrated = {c["name"]: c for c in inspector.get_columns("clinical_charges")}
            model_cols = {c.name: c for c in Base.metadata.tables["clinical_charges"].columns}
            assert set(migrated) == set(model_cols)
            for name, col in model_cols.items():
                assert migrated[name]["nullable"] == col.nullable, name

            index_names = {ix["name"] for ix in inspector.get_indexes("clinical_charges")}
            assert {
                "ix_cc_tenant_patient",
                "ix_cc_tenant_status",
                "ix_cc_tenant_work_item",
                "uq_cc_active_work_item",
            } <= index_names

            command.downgrade(config, "4d5e6f7a8b9c")
            assert "clinical_charges" not in sa.inspect(eng).get_table_names()

            command.upgrade(config, "head")
            assert "clinical_charges" in sa.inspect(eng).get_table_names()
        finally:
            eng.dispose()
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
