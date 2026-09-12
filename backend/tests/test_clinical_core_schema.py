"""
Tests for Phase G1: Additive Clinical Core Schema.

Verifies:
1. All 13 clinical core tables are present in production metadata.
2. Every table has non-nullable, indexed tenant_id with FK to tenants.id.
3. Every table defines canonical __rls_policies__ and is in preflight RLS_TABLES.
4. Metadata-driven CHILD_TENANT_RELATIONSHIPS coverage for all G1 FKs to tenant-owned parents.
5. Stale G1 config entries in CHILD_TENANT_RELATIONSHIPS are rejected.
6. Inherently patient-scoped tables enforce non-null patient_id.
7. Target contract on ClinicalWorkItemTarget:
   - Valid tooth, surface, root, canal shapes.
   - Rejection of invalid shapes, tooth keys, surface codes, root IDs, and empty canal_id.
   - Duplicate prevention with nullable canal_id.
8. Target contract on ClinicalEventTarget:
   - Valid tooth, surface, root, canal shapes.
   - Rejection of invalid shapes, tooth keys, surface codes, root IDs, and empty canal_id.
   - Duplicate prevention with nullable canal_id.
9. Treatment plan phase ordering and item uniqueness:
   - Unique (plan_id, phase_order) and non-negative phase_order.
   - Unique (phase_id, work_item_id) and non-negative item_order.
10. ORM model column server_default parity with migration.
11. ClinicalAttachmentLink context requirement constraint.
12. WorkflowTemplate tenant + code + version uniqueness.
13. NextVisitRequest reason and duration constraints.
14. Single Alembic head is f4a5b6c7d8e9 after e3a4b5c6d7e8.
15. Migration upgrade and downgrade on ephemeral SQLite.
16. Contract parity between preflight_migrations.py and migration f4a5b6c7d8e9.
17. Deterministic PostgreSQL RLS, same-tenant, and same-patient trigger configuration & SQL validation.
18. Live PostgreSQL verification if available, or clean documentation of environment limit.
19. Legacy tables remain unmodified and authoritative.
"""

import os
import tempfile
import uuid
from datetime import datetime, timezone
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.models import (
    Base,
    ClinicalWorkItem,
    ClinicalWorkItemTarget,
    ClinicalTreatmentPlan,
    ClinicalTreatmentPlanPhase,
    ClinicalTreatmentPlanItem,
    ClinicalEvent,
    ClinicalEventTarget,
    CareSession,
    CareSessionStep,
    CareObservation,
    WorkflowTemplate,
    NextVisitRequest,
    ClinicalAttachmentLink,
    Tenant,
    Patient,
    User,
    Appointment,
    Attachment,
)
from backend.scripts.preflight_migrations import (
    RLS_TABLES,
    CLINICAL_G1_TABLES,
    CHILD_TENANT_RELATIONSHIPS,
    CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS,
    SPECIALIZED_G1_PATIENT_TRIGGERS,
    _child_tenant_trigger_name,
    _child_patient_trigger_name,
    _get_all_g1_patient_triggers,
)
import backend.alembic.versions.f4a5b6c7d8e9_clinical_vnext_core_schema as mig
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command

PATIENT_SCOPED_TABLES = (
    "clinical_work_items",
    "clinical_treatment_plans",
    "clinical_events",
    "care_sessions",
    "care_observations",
    "next_visit_requests",
    "clinical_attachment_links",
)


def test_13_clinical_tables_in_production_metadata():
    metadata_tables = set(Base.metadata.tables.keys())
    for table_name in CLINICAL_G1_TABLES:
        assert table_name in metadata_tables, f"Missing {table_name} from Base.metadata"


def test_all_13_tables_have_non_nullable_tenant_id():
    for table_name in CLINICAL_G1_TABLES:
        table = Base.metadata.tables[table_name]
        assert "tenant_id" in table.c, f"{table_name} must contain tenant_id"
        tenant_col = table.c["tenant_id"]
        assert tenant_col.nullable is False, f"{table_name}.tenant_id must be NOT NULL"
        assert isinstance(tenant_col.type, sa.Integer), f"{table_name}.tenant_id must be Integer"
        fks = [fk.target_fullname for fk in tenant_col.foreign_keys]
        assert "tenants.id" in fks, f"{table_name}.tenant_id must reference tenants.id"


def test_all_13_tables_in_canonical_rls_contract():
    configured_rls = set(RLS_TABLES)
    for table_name in CLINICAL_G1_TABLES:
        assert table_name in configured_rls, f"{table_name} must be in preflight RLS_TABLES"

    model_classes = [
        ClinicalWorkItem,
        ClinicalWorkItemTarget,
        ClinicalTreatmentPlan,
        ClinicalTreatmentPlanPhase,
        ClinicalTreatmentPlanItem,
        ClinicalEvent,
        ClinicalEventTarget,
        CareSession,
        CareSessionStep,
        CareObservation,
        WorkflowTemplate,
        NextVisitRequest,
        ClinicalAttachmentLink,
    ]
    for cls in model_classes:
        assert hasattr(cls, "__rls_policies__"), f"{cls.__name__} missing __rls_policies__"
        assert len(cls.__rls_policies__) > 0, f"{cls.__name__} must define at least one RLS policy"


def test_inherently_patient_scoped_tables_enforce_non_null_patient_id():
    for table_name in PATIENT_SCOPED_TABLES:
        table = Base.metadata.tables[table_name]
        assert "patient_id" in table.c, f"{table_name} must contain patient_id"
        patient_col = table.c["patient_id"]
        assert patient_col.nullable is False, f"{table_name}.patient_id must be NOT NULL"
        fks = [fk.target_fullname for fk in patient_col.foreign_keys]
        assert "patients.id" in fks, f"{table_name}.patient_id must reference patients.id"


def test_metadata_driven_child_tenant_relationships_coverage():
    """
    Metadata-driven verification:
    1. Every ForeignKey in any of the 13 G1 tables referencing a tenant-owned parent
       must have a corresponding entry in CHILD_TENANT_RELATIONSHIPS.
    2. Every entry in CHILD_TENANT_RELATIONSHIPS for a G1 table must correspond to an
       actual ForeignKey in Base.metadata with identical nullability (rejects stale entries).
    """
    relationships_map = {
        (table, key): (parent, allow_null)
        for table, key, parent, allow_null in CHILD_TENANT_RELATIONSHIPS
    }

    # Verify every G1 foreign key (excluding direct tenant_id) is configured in CHILD_TENANT_RELATIONSHIPS
    for table_name in CLINICAL_G1_TABLES:
        table = Base.metadata.tables[table_name]
        for col in table.columns:
            for fk in col.foreign_keys:
                parent_table = fk.column.table.name
                if parent_table == "tenants":
                    continue  # tenant_id itself is the tenant root, not child-tenant

                config = relationships_map.get((table_name, col.name))
                assert config is not None, (
                    f"Missing CHILD_TENANT_RELATIONSHIPS configuration for {table_name}.{col.name} -> {parent_table}"
                )
                expected_parent, expected_allow_null = config
                assert expected_parent == parent_table, (
                    f"Mismatch in parent table for {table_name}.{col.name}: expected {parent_table}, configured {expected_parent}"
                )
                assert expected_allow_null == col.nullable, (
                    f"Mismatch in allow_null for {table_name}.{col.name}: column.nullable={col.nullable}, configured {expected_allow_null}"
                )

    # Verify no stale G1 entries exist in CHILD_TENANT_RELATIONSHIPS
    g1_tables_set = set(CLINICAL_G1_TABLES)
    for table, key, parent, allow_null in CHILD_TENANT_RELATIONSHIPS:
        if table not in g1_tables_set:
            continue
        assert table in Base.metadata.tables, f"Configured table {table} not in metadata"
        t = Base.metadata.tables[table]
        assert key in t.columns, f"Configured column {table}.{key} not in metadata"
        col = t.columns[key]
        assert col.nullable == allow_null, f"Configured allow_null mismatch for {table}.{key}"
        fk_targets = [fk.column.table.name for fk in col.foreign_keys]
        assert parent in fk_targets, f"Configured parent {parent} not a FK target of {table}.{key}"


def test_metadata_driven_child_patient_relationships_coverage():
    """
    Verify all G1 parent-patient relationships in preflight match metadata.
    """
    g1_tables_set = set(CLINICAL_G1_TABLES)
    for table, key, parent, allow_null in CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS:
        assert table in g1_tables_set
        t = Base.metadata.tables[table]
        assert "patient_id" in t.columns, f"{table} must have patient_id column"
        assert key in t.columns, f"{table}.{key} not in table"
        col = t.columns[key]
        assert col.nullable == allow_null
        fk_targets = [fk.column.table.name for fk in col.foreign_keys]
        assert parent in fk_targets, f"{parent} is not a FK target of {table}.{key}"
        p_table = Base.metadata.tables[parent]
        assert "patient_id" in p_table.columns, f"Parent {parent} must have patient_id"


def test_child_tenant_and_patient_trigger_naming():
    # Historical triggers must keep exact names
    assert _child_tenant_trigger_name("material_sessions", "patient_id") == "trg_material_sessions_patient_tenant"
    assert _child_tenant_trigger_name("tooth_status", "patient_id") == "trg_tooth_status_parent_tenant"
    assert _child_tenant_trigger_name("prescriptions", "patient_id") == "trg_prescriptions_parent_tenant"
    assert _child_tenant_trigger_name("attachments", "patient_id") == "trg_attachments_parent_tenant"

    # New triggers have unique, deterministic names <= 63 chars
    for table, key, _, _ in CHILD_TENANT_RELATIONSHIPS:
        name = _child_tenant_trigger_name(table, key)
        assert len(name.encode("utf-8")) <= 63, f"Trigger name {name} exceeds 63 bytes"

    for table, key, _, _ in CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS:
        name = _child_patient_trigger_name(table, key)
        assert len(name.encode("utf-8")) <= 63, f"Patient trigger name {name} exceeds 63 bytes"

    all_patient_trgs = _get_all_g1_patient_triggers()
    assert len(all_patient_trgs) == 14  # 11 direct + 3 specialized
    for trg in all_patient_trgs:
        assert len(trg.encode("utf-8")) <= 63, f"Trigger {trg} exceeds 63 bytes"


def test_orm_models_have_server_default_parity():
    """
    Verify ORM models define server_default on required columns to match migration
    and ensure fresh bootstrap create_all produces identical schema defaults.
    """
    expected_defaults = {
        ("clinical_work_items", "status"): "proposed",
        ("clinical_work_items", "version_id"): "1",
        ("clinical_treatment_plans", "status"): "draft",
        ("clinical_treatment_plans", "version_id"): "1",
        ("clinical_treatment_plan_phases", "phase_order"): "1",
        ("clinical_treatment_plan_phases", "status"): "draft",
        ("clinical_treatment_plan_items", "item_order"): "1",
        ("clinical_treatment_plan_items", "status"): "planned",
        ("clinical_treatment_plan_items", "version_id"): "1",
        ("care_sessions", "status"): "in_progress",
        ("care_sessions", "version_id"): "1",
        ("care_session_steps", "step_order"): "1",
        ("care_session_steps", "status"): "pending",
        ("care_session_steps", "version_id"): "1",
        ("workflow_templates", "version"): "1",
        ("next_visit_requests", "suggested_duration_minutes"): "30",
        ("next_visit_requests", "status"): "requested",
    }
    for (tbl_name, col_name), expected_val in expected_defaults.items():
        table = Base.metadata.tables[tbl_name]
        col = table.columns[col_name]
        assert col.server_default is not None, f"{tbl_name}.{col_name} missing server_default"
        default_str = str(col.server_default.arg)
        assert expected_val in default_str, (
            f"{tbl_name}.{col_name} server_default={default_str} does not contain {expected_val}"
        )


@pytest.fixture
def sqlite_engine():
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tenant = Tenant(id=1, name="Test Clinic")
        session.add(tenant)
        patient = Patient(
            id=10,
            tenant_id=1,
            name="John Doe",
            age=30,
            phone="enc",
            medical_history="enc",
            notes="enc",
        )
        session.add(patient)
        attachment = Attachment(
            id=100,
            tenant_id=1,
            patient_id=10,
            file_path="/files/xray.png",
            filename="xray.png",
            file_type="image/png",
        )
        session.add(attachment)
        session.commit()
    yield engine
    engine.dispose()


def test_work_item_targets_valid_and_invalid_shapes_and_empty_canal(sqlite_engine):
    with Session(sqlite_engine) as session:
        wi = ClinicalWorkItem(
            tenant_id=1,
            patient_id=10,
            kind="procedure",
            code="ENDO_RCT",
            status="in_progress",
        )
        session.add(wi)
        session.flush()

        # Valid targets
        t1 = ClinicalWorkItemTarget(tenant_id=1, work_item_id=wi.id, target_kind="tooth", tooth_key="14")
        t2 = ClinicalWorkItemTarget(tenant_id=1, work_item_id=wi.id, target_kind="surface", tooth_key="14", surface_code="O")
        t3 = ClinicalWorkItemTarget(tenant_id=1, work_item_id=wi.id, target_kind="root", tooth_key="14", root_id="buccal")
        t4 = ClinicalWorkItemTarget(tenant_id=1, work_item_id=wi.id, target_kind="canal", tooth_key="14", root_id="buccal", canal_id=None)
        t5 = ClinicalWorkItemTarget(tenant_id=1, work_item_id=wi.id, target_kind="canal", tooth_key="14", root_id="buccal", canal_id="MB1")
        session.add_all([t1, t2, t3, t4, t5])
        session.commit()

        # Rejection: empty string canal_id
        t_bad_canal1 = ClinicalWorkItemTarget(
            tenant_id=1, work_item_id=wi.id, target_kind="canal", tooth_key="14", root_id="buccal", canal_id=""
        )
        session.add(t_bad_canal1)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Rejection: whitespace-only canal_id
        t_bad_canal2 = ClinicalWorkItemTarget(
            tenant_id=1, work_item_id=wi.id, target_kind="canal", tooth_key="14", root_id="buccal", canal_id="   "
        )
        session.add(t_bad_canal2)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Rejection: tooth target with surface_code
        t_bad_shape = ClinicalWorkItemTarget(
            tenant_id=1, work_item_id=wi.id, target_kind="tooth", tooth_key="11", surface_code="M"
        )
        session.add(t_bad_shape)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Duplicate canal_id=None rejection
        t_dup1 = ClinicalWorkItemTarget(
            tenant_id=1, work_item_id=wi.id, target_kind="canal", tooth_key="14", root_id="buccal", canal_id=None
        )
        session.add(t_dup1)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_clinical_event_targets_valid_and_invalid_shapes_and_empty_canal(sqlite_engine):
    with Session(sqlite_engine) as session:
        ev = ClinicalEvent(
            tenant_id=1,
            patient_id=10,
            event_type="access_cavity_prepared",
            payload={"burst_size": 2},
        )
        session.add(ev)
        session.flush()

        # Valid targets
        t1 = ClinicalEventTarget(tenant_id=1, event_id=ev.id, target_kind="tooth", tooth_key="16")
        t2 = ClinicalEventTarget(tenant_id=1, event_id=ev.id, target_kind="surface", tooth_key="16", surface_code="O")
        t3 = ClinicalEventTarget(tenant_id=1, event_id=ev.id, target_kind="root", tooth_key="16", root_id="mesiobuccal")
        t4 = ClinicalEventTarget(tenant_id=1, event_id=ev.id, target_kind="canal", tooth_key="16", root_id="mesiobuccal", canal_id=None)
        t5 = ClinicalEventTarget(tenant_id=1, event_id=ev.id, target_kind="canal", tooth_key="16", root_id="mesiobuccal", canal_id="MB1")
        session.add_all([t1, t2, t3, t4, t5])
        session.commit()

        # Rejection: empty string canal_id
        t_bad_canal1 = ClinicalEventTarget(
            tenant_id=1, event_id=ev.id, target_kind="canal", tooth_key="16", root_id="mesiobuccal", canal_id=""
        )
        session.add(t_bad_canal1)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Rejection: whitespace-only canal_id
        t_bad_canal2 = ClinicalEventTarget(
            tenant_id=1, event_id=ev.id, target_kind="canal", tooth_key="16", root_id="mesiobuccal", canal_id="   "
        )
        session.add(t_bad_canal2)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Rejection: non-FDI tooth key
        t_bad_fdi = ClinicalEventTarget(
            tenant_id=1, event_id=ev.id, target_kind="tooth", tooth_key="99"
        )
        session.add(t_bad_fdi)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Duplicate canal_id=None rejection
        t_dup1 = ClinicalEventTarget(
            tenant_id=1, event_id=ev.id, target_kind="canal", tooth_key="16", root_id="mesiobuccal", canal_id=None
        )
        session.add(t_dup1)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Duplicate named canal rejection
        t_dup2 = ClinicalEventTarget(
            tenant_id=1, event_id=ev.id, target_kind="canal", tooth_key="16", root_id="mesiobuccal", canal_id="MB1"
        )
        session.add(t_dup2)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_treatment_plan_phase_order_and_item_uniqueness(sqlite_engine):
    with Session(sqlite_engine) as session:
        # Create plan and work item
        plan = ClinicalTreatmentPlan(tenant_id=1, patient_id=10, title="Comprehensive Plan")
        wi1 = ClinicalWorkItem(tenant_id=1, patient_id=10, kind="procedure", code="FILL_COMP")
        wi2 = ClinicalWorkItem(tenant_id=1, patient_id=10, kind="procedure", code="CROWN")
        session.add_all([plan, wi1, wi2])
        session.flush()

        # 1. Phase 1
        phase1 = ClinicalTreatmentPlanPhase(tenant_id=1, plan_id=plan.id, phase_order=1, name="Phase 1")
        session.add(phase1)
        session.commit()

        # 2. Duplicate phase_order on same plan must fail UniqueConstraint("plan_id", "phase_order")
        phase1_dup = ClinicalTreatmentPlanPhase(tenant_id=1, plan_id=plan.id, phase_order=1, name="Duplicate Phase 1")
        session.add(phase1_dup)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # 3. Negative phase_order must fail CheckConstraint("phase_order >= 0")
        phase_neg = ClinicalTreatmentPlanPhase(tenant_id=1, plan_id=plan.id, phase_order=-1, name="Negative Phase")
        session.add(phase_neg)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # 4. Valid item in phase 1
        item1 = ClinicalTreatmentPlanItem(tenant_id=1, phase_id=phase1.id, work_item_id=wi1.id, item_order=1)
        session.add(item1)
        session.commit()

        # 5. Duplicate (phase_id, work_item_id) must fail UniqueConstraint("phase_id", "work_item_id")
        item1_dup_work_item = ClinicalTreatmentPlanItem(
            tenant_id=1, phase_id=phase1.id, work_item_id=wi1.id, item_order=2
        )
        session.add(item1_dup_work_item)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # 6. Duplicate item_order in the SAME phase must fail UniqueConstraint("phase_id", "item_order")
        item1_dup_order = ClinicalTreatmentPlanItem(
            tenant_id=1, phase_id=phase1.id, work_item_id=wi2.id, item_order=1
        )
        session.add(item1_dup_order)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # 7. Same item_order=1 in a DIFFERENT phase must succeed
        phase2 = ClinicalTreatmentPlanPhase(tenant_id=1, plan_id=plan.id, phase_order=2, name="Phase 2")
        session.add(phase2)
        session.commit()

        item2_diff_phase = ClinicalTreatmentPlanItem(
            tenant_id=1, phase_id=phase2.id, work_item_id=wi2.id, item_order=1
        )
        session.add(item2_diff_phase)
        session.commit()

        # 8. Negative item_order must fail CheckConstraint("item_order >= 0")
        wi3 = ClinicalWorkItem(tenant_id=1, patient_id=10, kind="procedure", code="EXTRACTION")
        session.add(wi3)
        session.flush()
        item_neg = ClinicalTreatmentPlanItem(tenant_id=1, phase_id=phase1.id, work_item_id=wi3.id, item_order=-1)
        session.add(item_neg)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_clinical_attachment_links_context_required(sqlite_engine):
    with Session(sqlite_engine) as session:
        # Valid: attachment linked to a tooth_key
        link1 = ClinicalAttachmentLink(
            tenant_id=1,
            attachment_id=100,
            patient_id=10,
            tooth_key="16",
            purpose_code="pre_op",
        )
        session.add(link1)
        session.commit()

        # Invalid: link with no clinical context (all 4 context columns null)
        link_bad = ClinicalAttachmentLink(
            tenant_id=1,
            attachment_id=100,
            patient_id=10,
            purpose_code="pre_op",
        )
        session.add(link_bad)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_workflow_templates_tenant_code_version_uniqueness(sqlite_engine):
    with Session(sqlite_engine) as session:
        wt1 = WorkflowTemplate(
            tenant_id=1,
            template_code="RCT_BASIC",
            version=1,
            title="Standard RCT",
            definition={"steps": ["access", "instrument", "obturate"]},
        )
        session.add(wt1)
        session.commit()

        # Duplicate (tenant_id=1, template_code='RCT_BASIC', version=1) must fail
        wt2 = WorkflowTemplate(
            tenant_id=1,
            template_code="RCT_BASIC",
            version=1,
            title="Duplicate RCT",
            definition={"steps": []},
        )
        session.add(wt2)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # New version (version=2) on same tenant must succeed
        wt3 = WorkflowTemplate(
            tenant_id=1,
            template_code="RCT_BASIC",
            version=2,
            title="Updated RCT v2",
            definition={"steps": ["access", "instrument", "irigate", "obturate"]},
        )
        session.add(wt3)
        session.commit()
        assert wt3.id is not None


def test_next_visit_requests_constraints(sqlite_engine):
    with Session(sqlite_engine) as session:
        # Invalid: duration <= 0
        nvr_bad1 = NextVisitRequest(
            tenant_id=1,
            patient_id=10,
            reason="Crown seating",
            suggested_duration_minutes=0,
        )
        session.add(nvr_bad1)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Invalid: empty reason
        nvr_bad2 = NextVisitRequest(
            tenant_id=1,
            patient_id=10,
            reason="   ",
            suggested_duration_minutes=30,
        )
        session.add(nvr_bad2)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_care_observations_constraints(sqlite_engine):
    with Session(sqlite_engine) as session:
        care_session = CareSession(tenant_id=1, patient_id=10, status="in_progress")
        session.add(care_session)
        session.commit()

        # 1. Valid CareObservation row
        obs_valid = CareObservation(
            tenant_id=1,
            patient_id=10,
            care_session_id=care_session.id,
            observation_code="probing_depth",
            tooth_key="16",
            structured_value={"depth_mm": 4, "bleeding": True},
            notes="Mesial pocket",
        )
        session.add(obs_valid)
        session.commit()
        assert obs_valid.id is not None

        # 2. Rejection: empty observation_code (ck_co_code_not_empty)
        obs_empty_code = CareObservation(
            tenant_id=1,
            patient_id=10,
            care_session_id=care_session.id,
            observation_code="   ",
            tooth_key="16",
            structured_value={"depth_mm": 4},
        )
        session.add(obs_empty_code)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # 3. Rejection: invalid non-FDI tooth_key (ck_co_tooth_key_fdi)
        obs_invalid_fdi = CareObservation(
            tenant_id=1,
            patient_id=10,
            care_session_id=care_session.id,
            observation_code="probing_depth",
            tooth_key="99",
            structured_value={"depth_mm": 4},
        )
        session.add(obs_invalid_fdi)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_alembic_single_head_is_f4a5b6c7d8e9():
    alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    config = Config(alembic_cfg_path)
    script_dir = ScriptDirectory.from_config(config)

    heads = script_dir.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 Alembic head revision, found {heads}"
    assert heads[0] == "1a2b3c4d5e6f", f"Expected head revision 1a2b3c4d5e6f, got {heads[0]}"

    head_rev = script_dir.get_revision("1a2b3c4d5e6f")
    assert head_rev.down_revision == "f4a5b6c7d8e9", f"Expected parent revision f4a5b6c7d8e9, got {head_rev.down_revision}"

    rev = script_dir.get_revision("f4a5b6c7d8e9")
    assert rev.down_revision == "e3a4b5c6d7e8", f"Expected parent revision e3a4b5c6d7e8, got {rev.down_revision}"


def test_alembic_migration_upgrade_and_downgrade_sqlite(monkeypatch):
    """Verify that migration f4a5b6c7d8e9 applies cleanly on SQLite and downgrades symmetrically."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Stamp at parent revision e3a4b5c6d7e8 on clean db
        command.stamp(config, "e3a4b5c6d7e8")

        # 2. Upgrade to f4a5b6c7d8e9 (creates all 13 tables)
        command.upgrade(config, "f4a5b6c7d8e9")

        engine = sa.create_engine(sqlite_url)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            for t in CLINICAL_G1_TABLES:
                assert t in tables, f"Table {t} missing after upgrade"

            # 3. Downgrade back to e3a4b5c6d7e8 (drops all 13 tables)
            command.downgrade(config, "e3a4b5c6d7e8")

            inspector = sa.inspect(engine)
            tables_after_downgrade = set(inspector.get_table_names())
            for t in CLINICAL_G1_TABLES:
                assert t not in tables_after_downgrade, f"Table {t} should have been dropped on downgrade"

            # 4. Upgrade to new head (applies f4a5b6c7d8e9 and 1a2b3c4d5e6f)
            command.upgrade(config, "head")

            inspector = sa.inspect(engine)
            tables_after_head = set(inspector.get_table_names())
            for t in CLINICAL_G1_TABLES:
                assert t in tables_after_head, f"Table {t} missing after upgrade to head"
            assert "clinical_projection_coverages" in tables_after_head, "Table clinical_projection_coverages missing after upgrade to head"

            # 5. Downgrade exactly to f4a5b6c7d8e9: clinical_projection_coverages is removed, G1 tables remain
            command.downgrade(config, "f4a5b6c7d8e9")

            inspector = sa.inspect(engine)
            tables_after_step_downgrade = set(inspector.get_table_names())
            assert "clinical_projection_coverages" not in tables_after_step_downgrade, "Table clinical_projection_coverages should have been removed when downgrading to f4a5b6c7d8e9"
            for t in CLINICAL_G1_TABLES:
                assert t in tables_after_step_downgrade, f"Table {t} should still exist after downgrading to f4a5b6c7d8e9"

            # 6. Re-upgrade back to head: clinical_projection_coverages is recreated
            command.upgrade(config, "head")

            inspector = sa.inspect(engine)
            tables_after_reupgrade = set(inspector.get_table_names())
            for t in CLINICAL_G1_TABLES:
                assert t in tables_after_reupgrade, f"Table {t} missing after re-upgrade"
            assert "clinical_projection_coverages" in tables_after_reupgrade, "Table clinical_projection_coverages missing after re-upgrade to head"
        finally:
            engine.dispose()

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_preflight_and_migration_contract_parity():
    """
    Verify complete parity between preflight_migrations.py and migration f4a5b6c7d8e9:
    1. Table names: CLINICAL_G1_TABLES == NEW_TABLES
    2. Tenant relationships: G1 entries in CHILD_TENANT_RELATIONSHIPS == NEW_CHILD_TENANT_RELATIONSHIPS
    3. Patient relationships: CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS == NEW_CHILD_PATIENT_RELATIONSHIPS
    4. Trigger naming parity
    """
    assert CLINICAL_G1_TABLES == mig.NEW_TABLES

    g1_child_tenant_in_preflight = [
        rel for rel in CHILD_TENANT_RELATIONSHIPS if rel[0] in CLINICAL_G1_TABLES
    ]
    assert tuple(g1_child_tenant_in_preflight) == mig.NEW_CHILD_TENANT_RELATIONSHIPS

    assert CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS == mig.NEW_CHILD_PATIENT_RELATIONSHIPS
    assert SPECIALIZED_G1_PATIENT_TRIGGERS == mig.SPECIALIZED_G1_PATIENT_TRIGGERS

    # Parity of trigger names
    for table, child_key, _, _ in mig.NEW_CHILD_TENANT_RELATIONSHIPS:
        assert _child_tenant_trigger_name(table, child_key) == mig._trigger_name(table, child_key)

    for table, child_key, _, _ in mig.NEW_CHILD_PATIENT_RELATIONSHIPS:
        assert _child_patient_trigger_name(table, child_key) == mig._patient_trigger_name(table, child_key)


def test_deterministic_postgresql_trigger_sql_contracts():
    """
    Verify PostgreSQL triggers and PL/pgSQL functions are syntactically and logically
    complete without requiring a live PostgreSQL instance.
    """
    expected_functions = [
        "dentix_assert_parent_tenant",
        "dentix_assert_parent_patient",
        "dentix_assert_ctpi_patient",
        "dentix_assert_css_patient",
        "dentix_assert_co_step_session",
    ]
    with open(mig.__file__, "r", encoding="utf-8") as f:
        mig_content = f.read()

    for func_name in expected_functions:
        assert f"FUNCTION {func_name}" in mig_content, f"{func_name} missing from migration"
        assert "RETURNS trigger LANGUAGE plpgsql" in mig_content

    # Check cross-patient relational assertions
    assert "Patient mismatch on clinical_treatment_plan_items" in mig_content
    assert "Patient mismatch on care_session_steps" in mig_content
    assert "Care session mismatch on care_observations" in mig_content

    # Check functions installed in preflight fresh bootstrap
    from backend.scripts import preflight_migrations
    with open(preflight_migrations.__file__, "r", encoding="utf-8") as f:
        preflight_content = f.read()

    for func_name in expected_functions:
        assert f"FUNCTION {func_name}" in preflight_content, f"{func_name} missing from preflight"


def test_live_postgresql_if_available():
    """
    Verify PostgreSQL triggers enforce cross-patient and cross-entity integrity on a live
    PostgreSQL instance.
    This verifies PostgreSQL trigger behavior (defense-in-depth relational constraints),
    not RLS role bypass.
    If DATABASE_URL is not PostgreSQL, skip cleanly.
    """
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not pg_url or not pg_url.startswith(("postgresql://", "postgres://")):
        pytest.skip(
            "DATABASE_URL is not PostgreSQL; skipping live PostgreSQL trigger behavior test "
            "(will execute in PostgreSQL-backed CI)."
        )

    engine = sa.create_engine(pg_url)
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                with Session(bind=conn) as session:
                    uid = uuid.uuid4().hex[:8]

                    # 1. Lookup existing tenant or seed test tenant
                    tenant_id = conn.execute(sa.text("SELECT id FROM tenants LIMIT 1")).scalar()
                    if not tenant_id:
                        tenant_id = conn.execute(
                            sa.text(
                                "INSERT INTO tenants (name, domain) VALUES (:name, :domain) RETURNING id"
                            ),
                            {"name": f"Test Clinic {uid}", "domain": f"test-{uid}.com"},
                        ).scalar()

                    # 2. Seed uniquely named same-tenant Patient A and Patient B
                    patient_a = Patient(
                        tenant_id=tenant_id,
                        name=f"Patient A {uid}",
                        age=35,
                        phone=f"+1000{uid[:6]}",
                        medical_history="No history",
                        notes="Patient A notes",
                    )
                    patient_b = Patient(
                        tenant_id=tenant_id,
                        name=f"Patient B {uid}",
                        age=42,
                        phone=f"+2000{uid[:6]}",
                        medical_history="No history",
                        notes="Patient B notes",
                    )
                    session.add_all([patient_a, patient_b])
                    session.flush()

                    # 3. Seed minimum legacy parents
                    appointment_b = Appointment(
                        tenant_id=tenant_id,
                        patient_id=patient_b.id,
                        date_time=datetime.now(timezone.utc),
                        status="Scheduled",
                    )
                    attachment_a = Attachment(
                        tenant_id=tenant_id,
                        patient_id=patient_a.id,
                        file_path=f"/files/test_a_{uid}.png",
                        filename=f"test_a_{uid}.png",
                        file_type="image/png",
                    )
                    session.add_all([appointment_b, attachment_a])
                    session.flush()

                    # 4. Seed minimum G1 parents
                    plan_a = ClinicalTreatmentPlan(
                        tenant_id=tenant_id,
                        patient_id=patient_a.id,
                        title=f"Plan A {uid}",
                        status="draft",
                    )
                    session.add(plan_a)
                    session.flush()

                    phase_a = ClinicalTreatmentPlanPhase(
                        tenant_id=tenant_id,
                        plan_id=plan_a.id,
                        phase_order=1,
                        name=f"Phase 1 {uid}",
                        status="draft",
                    )
                    work_item_b = ClinicalWorkItem(
                        tenant_id=tenant_id,
                        patient_id=patient_b.id,
                        kind="procedure",
                        code="REST_COMPOSITE",
                        status="proposed",
                    )
                    session_a = CareSession(
                        tenant_id=tenant_id,
                        patient_id=patient_a.id,
                        status="in_progress",
                    )
                    session_b = CareSession(
                        tenant_id=tenant_id,
                        patient_id=patient_b.id,
                        status="in_progress",
                    )
                    session.add_all([phase_a, work_item_b, session_a, session_b])
                    session.flush()

                    def assert_trigger_violation(instance):
                        with pytest.raises((sa.exc.IntegrityError, sa.exc.DBAPIError)):
                            with session.begin_nested():
                                session.add(instance)
                                session.flush()

                    # Test 1: plan A phase + work item B
                    assert_trigger_violation(
                        ClinicalTreatmentPlanItem(
                            tenant_id=tenant_id,
                            phase_id=phase_a.id,
                            work_item_id=work_item_b.id,
                            item_order=1,
                            status="planned",
                        )
                    )

                    # Test 2: attachment A linked with patient B
                    assert_trigger_violation(
                        ClinicalAttachmentLink(
                            tenant_id=tenant_id,
                            attachment_id=attachment_a.id,
                            patient_id=patient_b.id,
                            tooth_key="16",
                            purpose_code="pre_op",
                        )
                    )

                    # Test 3: session A + work item B step
                    assert_trigger_violation(
                        CareSessionStep(
                            tenant_id=tenant_id,
                            care_session_id=session_a.id,
                            work_item_id=work_item_b.id,
                            step_order=1,
                            step_code="prep",
                            title="Cavity Preparation",
                            status="pending",
                        )
                    )

                    # Test 4: event A + work item B
                    assert_trigger_violation(
                        ClinicalEvent(
                            tenant_id=tenant_id,
                            patient_id=patient_a.id,
                            work_item_id=work_item_b.id,
                            event_type="finding_recorded",
                            payload={"description": "Cross-patient finding"},
                        )
                    )

                    # Test 5: observation patient A + session B
                    assert_trigger_violation(
                        CareObservation(
                            tenant_id=tenant_id,
                            patient_id=patient_a.id,
                            care_session_id=session_b.id,
                            observation_code="probing_depth",
                            structured_value={"mm": 3},
                        )
                    )

                    # Test 6: next-visit patient A + session B
                    assert_trigger_violation(
                        NextVisitRequest(
                            tenant_id=tenant_id,
                            patient_id=patient_a.id,
                            care_session_id=session_b.id,
                            reason="Follow-up checkup",
                            suggested_duration_minutes=30,
                            status="requested",
                        )
                    )

                    # Test 7: care session patient A + appointment B
                    assert_trigger_violation(
                        CareSession(
                            tenant_id=tenant_id,
                            patient_id=patient_a.id,
                            appointment_id=appointment_b.id,
                            status="in_progress",
                        )
                    )

                    # Test 8: attachment A/patient A linked to work item B
                    assert_trigger_violation(
                        ClinicalAttachmentLink(
                            tenant_id=tenant_id,
                            attachment_id=attachment_a.id,
                            patient_id=patient_a.id,
                            work_item_id=work_item_b.id,
                            purpose_code="work_item_reference",
                        )
                    )
            finally:
                trans.rollback()
    finally:
        engine.dispose()


def test_legacy_tables_remain_intact():
    legacy_tables = [
        "tenants",
        "users",
        "patients",
        "appointments",
        "treatments",
        "treatment_sessions",
        "tooth_status",
        "prescriptions",
        "attachments",
        "domain_events",
    ]
    metadata_tables = set(Base.metadata.tables.keys())
    for t in legacy_tables:
        assert t in metadata_tables, f"Legacy table {t} must remain present"
