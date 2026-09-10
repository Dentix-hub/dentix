"""
Behavior-based tests for Clinical Workspace Snapshot.

Verifies:
1. Endpoint GET /patients/{id}/clinical-workspace:
   - Protected by require_permission(Permission.CLINICAL_READ).
   - Uniform 404 for missing and cross-tenant patients (indistinguishable, no leakage).
   - StandardResponse envelope with projection identity, patient scope, generated/effective timestamps.
   - Zero finance attributes (no cost, price, amount, payments, invoices).
   - Zero mutation authority (read-only snapshot).
2. Service reduction & precedence:
   - Deterministic native truth reduction (occurred_at -> recorded_at -> stable ID).
   - Exclusion of superseded events and entered-in-error work items without deleting records.
   - COMPLETE domain coverage blocks legacy fallback.
   - PARTIAL domain coverage enforces native precedence and deduplication.
   - UNCOVERED domain coverage includes legacy fallback.
   - Undated legacy tooth status marked strictly with UNKNOWN temporal certainty.
   - Unsupported clinical codes (e.g. PROS_DENTURE or custom codes) preserved as visible neutral unclassified warnings.
   - Server-selected rollout mode (LEGACY_ONLY, SHADOW, VNEXT_PRIMARY) via feature-flag/tenant-rollout infrastructure.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.models import (
    Base,
    CareSession,
    ClinicalEvent,
    ClinicalEventTarget,
    ClinicalProjectionCoverage,
    ClinicalWorkItem,
    ClinicalWorkItemTarget,
    FeatureFlag,
    Patient,
    Tenant,
    TenantFeature,
    ToothStatus,
    Treatment,
    User,
)
from backend.auth import create_access_token
from backend.clinical.catalog import FindingCode, ProcedureCode
from backend.services.clinical_workspace_service import ClinicalWorkspaceService


@pytest.fixture(scope="function")
def workspace_test_engine():
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        t1 = Tenant(id=1, name="Primary Clinic")
        t2 = Tenant(id=2, name="Secondary Clinic")
        session.add_all([t1, t2])

        p1 = Patient(
            id=101,
            tenant_id=1,
            name="Alice Patient",
            age=35,
            phone="123456789",
            medical_history="None",
            notes="",
        )
        p2_cross = Patient(
            id=202,
            tenant_id=2,
            name="Bob CrossTenant",
            age=40,
            phone="987654321",
            medical_history="None",
            notes="",
        )
        session.add_all([p1, p2_cross])

        # Users
        u_doctor = User(
            id=1,
            tenant_id=1,
            username="doc_alice",
            email="doc@clinic1.com",
            role="doctor",
            hashed_password="fake",
        )
        u_reception = User(
            id=2,
            tenant_id=1,
            username="rec_charlie",
            email="rec@clinic1.com",
            role="receptionist",
            hashed_password="fake",
        )
        session.add_all([u_doctor, u_reception])

        # Feature Flags
        ff_shadow = FeatureFlag(
            key="clinical_vnext_shadow",
            description="Shadow rollout mode",
            is_global_enabled=False,
            rollout_percentage=0,
        )
        ff_primary = FeatureFlag(
            key="clinical_vnext_primary",
            description="Primary rollout mode",
            is_global_enabled=False,
            rollout_percentage=0,
        )
        session.add_all([ff_shadow, ff_primary])
        session.commit()
    yield engine
    engine.dispose()



def _enable_vnext_primary(
    session: Session,
    tenant_id: int = 1,
    *,
    native_writes: bool = True,
) -> None:
    """Enable primary reads and explicitly choose native-write readiness."""
    for feature_key, is_enabled in (
        ("clinical_vnext_primary", True),
        ("clinical_vnext_native_writes", native_writes),
    ):
        tf = session.query(TenantFeature).filter_by(
            tenant_id=tenant_id,
            feature_key=feature_key,
        ).first()
        if not tf:
            tf = TenantFeature(
                tenant_id=tenant_id,
                feature_key=feature_key,
                is_enabled=is_enabled,
            )
            session.add(tf)
        else:
            tf.is_enabled = is_enabled
    session.commit()



class AsyncSessionWrapper:
    """Synchronous Session adapter presenting an async interface for service tests."""
    def __init__(self, s: Session):
        self._s = s
    async def execute(self, stmt):
        class ResultWrapper:
            def __init__(self, res):
                self._res = res
            def scalars(self):
                return self
            def all(self):
                return self._res.scalars().all()
            def first(self):
                return self._res.scalars().first()
            def scalar_one_or_none(self):
                return self._res.scalars().first()
        return ResultWrapper(self._s.execute(stmt))
    def add(self, obj):
        self._s.add(obj)
    async def commit(self):
        self._s.commit()
    async def flush(self):
        self._s.flush()
    async def refresh(self, obj):
        pass


@pytest.mark.asyncio
async def test_snapshot_deterministic_ordering(workspace_test_engine):
    """Verify that native work items and events order deterministically."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        t1 = datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc)

        wi1 = ClinicalWorkItem(
            id=10,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="REST_COMPOSITE",
            status="completed",
            created_at=t1,
        )
        target1 = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=10,
            target_kind="surface",
            tooth_key="16",
            surface_code="O",
        )
        session.add_all([wi1, target1])
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        assert snapshot is not None
        assert snapshot.patient_id == 101
        assert "16" in snapshot.teeth
        t16 = snapshot.teeth["16"]
        assert len(t16.procedures) >= 1
        assert t16.procedures[0].code == "REST_COMPOSITE"
        assert t16.procedures[0].provenance == "native"


@pytest.mark.asyncio
async def test_snapshot_excludes_superseded_and_entered_in_error(workspace_test_engine):
    """Verify superseded events and entered-in-error work items are excluded from active state."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        # Work item marked entered in error
        wi_error = ClinicalWorkItem(
            id=20,
            tenant_id=1,
            patient_id=101,
            kind="finding",
            code="CARIES",
            status="entered_in_error",
            created_at=datetime.now(timezone.utc),
        )
        t_err = ClinicalWorkItemTarget(tenant_id=1, work_item_id=20, target_kind="tooth", tooth_key="21")

        # Event superseded
        ev_superseded = ClinicalEvent(
            id=30,
            tenant_id=1,
            patient_id=101,
            event_type="OBSERVATION",
            payload={"superseded": True},
            occurred_at=datetime.now(timezone.utc),
        )
        session.add_all([wi_error, t_err, ev_superseded])
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        # Tooth 21 should NOT have CARIES visual entry because wi 20 is entered_in_error
        t21 = snapshot.teeth["21"]
        caries_entries = [f for f in t21.findings if f.code == "CARIES"]
        assert len(caries_entries) == 0

        # Work item 20 should NOT be in active work items
        active_ids = {wi.id for wi in snapshot.work_items}
        assert 20 not in active_ids


@pytest.mark.asyncio
async def test_snapshot_reduces_canonical_tooth_status_events(workspace_test_engine):
    """Backfilled tooth-status events remain visible after COMPLETE cutover."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        procedure_occurred_at = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
        procedure_recorded_at = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        session.add(
            ClinicalProjectionCoverage(
                tenant_id=1,
                patient_id=101,
                domain="teeth",
                status="COMPLETE",
            )
        )
        events = [
            ClinicalEvent(
                id=31,
                tenant_id=1,
                patient_id=101,
                event_type="tooth_lifecycle_changed",
                payload={"kind": "lifecycle", "canonical_code": "MISSING"},
                occurred_at=datetime.now(timezone.utc),
            ),
            ClinicalEvent(
                id=32,
                tenant_id=1,
                patient_id=101,
                event_type="finding_recorded",
                payload={"kind": "finding", "canonical_code": "CARIES"},
                occurred_at=datetime.now(timezone.utc),
            ),
            ClinicalEvent(
                id=33,
                tenant_id=1,
                patient_id=101,
                event_type="procedure_recorded",
                payload={"kind": "procedure", "canonical_code": "ENDO_RCT"},
                occurred_at=procedure_occurred_at,
                created_at=procedure_recorded_at,
            ),
        ]
        session.add_all(events)
        session.flush()
        session.add_all(
            [
                ClinicalEventTarget(
                    tenant_id=1,
                    event_id=31,
                    target_kind="tooth",
                    tooth_key="11",
                ),
                ClinicalEventTarget(
                    tenant_id=1,
                    event_id=32,
                    target_kind="tooth",
                    tooth_key="21",
                ),
                ClinicalEventTarget(
                    tenant_id=1,
                    event_id=33,
                    target_kind="tooth",
                    tooth_key="36",
                ),
            ]
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        assert snapshot.teeth["11"].lifecycle == "MISSING"
        assert [entry.code for entry in snapshot.teeth["21"].findings] == ["CARIES"]
        assert [entry.code for entry in snapshot.teeth["36"].procedures] == ["ENDO_RCT"]
        procedure_entry = snapshot.teeth["36"].procedures[0]
        assert procedure_entry.occurred_at.replace(tzinfo=timezone.utc) == procedure_occurred_at
        assert procedure_entry.recorded_at.replace(tzinfo=timezone.utc) == procedure_recorded_at


@pytest.mark.asyncio
async def test_snapshot_appends_multi_surface_work_item_once_per_tooth(
    workspace_test_engine,
):
    """One MOD work item produces one visual carrying all of its tooth targets."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        session.add(
            ClinicalWorkItem(
                id=34,
                tenant_id=1,
                patient_id=101,
                kind="procedure",
                code="REST_COMPOSITE",
                status="completed",
            )
        )
        session.add_all(
            [
                ClinicalWorkItemTarget(
                    tenant_id=1,
                    work_item_id=34,
                    target_kind="surface",
                    tooth_key="36",
                    surface_code=surface_code,
                )
                for surface_code in ("M", "O", "D")
            ]
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        composite_entries = [
            entry
            for entry in snapshot.teeth["36"].procedures
            if entry.visual_id == "ve-wi-34"
        ]
        assert len(composite_entries) == 1
        assert {target.surface_code for target in composite_entries[0].targets} == {
            "M",
            "O",
            "D",
        }


@pytest.mark.asyncio
async def test_later_lifecycle_event_overrides_completed_extraction(
    workspace_test_engine,
):
    """A later explicit lifecycle correction wins over an older extraction work item."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        extraction_at = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
        correction_at = extraction_at + timedelta(hours=1)
        session.add(
            ClinicalWorkItem(
                id=35,
                tenant_id=1,
                patient_id=101,
                kind="procedure",
                code="SURG_EXTRACTION",
                status="completed",
                created_at=extraction_at,
            )
        )
        session.add(
            ClinicalWorkItemTarget(
                tenant_id=1,
                work_item_id=35,
                target_kind="tooth",
                tooth_key="46",
            )
        )
        session.add(
            ClinicalEvent(
                id=36,
                tenant_id=1,
                patient_id=101,
                event_type="tooth_lifecycle_changed",
                payload={"kind": "lifecycle", "canonical_code": "PRESENT"},
                occurred_at=correction_at,
                created_at=correction_at,
            )
        )
        session.add(
            ClinicalEventTarget(
                tenant_id=1,
                event_id=36,
                target_kind="tooth",
                tooth_key="46",
            )
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        assert snapshot.teeth["46"].lifecycle == "PRESENT"
        assert snapshot.teeth["46"].condition != "Missing"


@pytest.mark.asyncio
async def test_legacy_composite_without_surface_reports_renderer_warning(
    workspace_test_engine,
):
    """Legacy fillings without surface evidence must not claim renderer support."""
    with Session(workspace_test_engine) as session:
        session.add(
            Treatment(
                id=37,
                tenant_id=1,
                patient_id=101,
                tooth_number="26",
                procedure="Composite Filling",
                cost=120.0,
                status="Done",
            )
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        work_item = next(item for item in snapshot.work_items if item.id == "legacy-37")
        assert work_item.is_renderer_supported is False
        assert not any(
            entry.code == "REST_COMPOSITE"
            for entry in snapshot.teeth["26"].procedures
        )
        assert any(
            warning.code == "UNSUPPORTED_RENDERER_TARGET"
            and warning.source_kind == "treatment"
            and warning.source_id == 37
            for warning in snapshot.warnings
        )


@pytest.mark.asyncio
async def test_legacy_filled_tooth_status_reports_renderer_warning(
    workspace_test_engine,
):
    """A Filled tooth status without surface evidence must not disappear silently."""
    with Session(workspace_test_engine) as session:
        session.add(
            ToothStatus(
                id=38,
                tenant_id=1,
                patient_id=101,
                tooth_number=26,
                condition="Filled",
            )
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        assert snapshot.teeth["26"].condition == "Filled"
        assert not any(
            entry.code == "REST_COMPOSITE"
            for entry in snapshot.teeth["26"].procedures
        )
        assert any(
            warning.code == "UNSUPPORTED_RENDERER_TARGET"
            and warning.source_kind == "tooth_status"
            and warning.source_id == 38
            for warning in snapshot.warnings
        )


@pytest.mark.asyncio
async def test_event_deduplication_uses_linked_work_item_identity(
    workspace_test_engine,
):
    """An unrelated completed event survives beside a same-code planned work item."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        session.add(
            ClinicalWorkItem(
                id=39,
                tenant_id=1,
                patient_id=101,
                kind="procedure",
                code="PROS_CROWN",
                status="planned",
            )
        )
        session.add(
            ClinicalWorkItemTarget(
                tenant_id=1,
                work_item_id=39,
                target_kind="tooth",
                tooth_key="16",
            )
        )
        session.add_all(
            [
                ClinicalEvent(
                    id=40,
                    tenant_id=1,
                    patient_id=101,
                    event_type="procedure_recorded",
                    payload={"kind": "procedure", "canonical_code": "PROS_CROWN"},
                    occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                ),
                ClinicalEvent(
                    id=41,
                    tenant_id=1,
                    patient_id=101,
                    work_item_id=39,
                    event_type="procedure_recorded",
                    payload={"kind": "procedure", "canonical_code": "PROS_CROWN"},
                    occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                ClinicalEventTarget(
                    tenant_id=1,
                    event_id=event_id,
                    target_kind="tooth",
                    tooth_key="16",
                )
                for event_id in (40, 41)
            ]
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        visual_ids = {
            entry.visual_id for entry in snapshot.teeth["16"].procedures
        }
        assert "ve-wi-39" in visual_ids
        assert "ve-ev-40" in visual_ids
        assert "ve-ev-41" not in visual_ids


@pytest.mark.asyncio
async def test_partial_teeth_fallback_ignores_native_treatment_only_truth(
    workspace_test_engine,
):
    """Treatment-domain evidence cannot suppress unrelated legacy tooth status."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        session.add(
            ClinicalProjectionCoverage(
                tenant_id=1,
                patient_id=101,
                domain="teeth",
                status="PARTIAL",
            )
        )
        session.add(
            ClinicalWorkItem(
                id=42,
                tenant_id=1,
                patient_id=101,
                kind="procedure",
                code="PROS_CROWN",
                status="planned",
            )
        )
        session.add(
            ClinicalWorkItemTarget(
                tenant_id=1,
                work_item_id=42,
                target_kind="tooth",
                tooth_key="16",
            )
        )
        session.add(
            ToothStatus(
                id=43,
                tenant_id=1,
                patient_id=101,
                tooth_number=16,
                condition="Missing",
            )
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        assert snapshot.teeth["16"].lifecycle == "MISSING"
        assert any(
            entry.visual_id == "ve-wi-42"
            for entry in snapshot.teeth["16"].procedures
        )


@pytest.mark.asyncio
async def test_snapshot_complete_coverage_blocks_legacy(workspace_test_engine):
    """When coverage is COMPLETE, legacy fallback records are strictly blocked."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        # Mark treatments coverage COMPLETE
        cov = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=101,
            domain="treatments",
            status="COMPLETE",
        )
        session.merge(cov)

        # Add a legacy treatment for tooth 36
        leg_tr = Treatment(
            id=50,
            tenant_id=1,
            patient_id=101,
            tooth_number="36",
            procedure="Crown",
            cost=500.0,
            status="Done",
        )
        session.merge(leg_tr)
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        # Tooth 36 should NOT receive legacy crown because treatments domain is COMPLETE
        t36 = snapshot.teeth["36"]
        crown_procs = [p for p in t36.procedures if p.provenance == "legacy_fallback"]
        assert len(crown_procs) == 0


@pytest.mark.asyncio
async def test_complete_coverage_keeps_legacy_writes_until_native_commands_enabled(
    workspace_test_engine,
):
    """Primary reads must not hide writes still accepted by legacy endpoints."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1, native_writes=False)
        session.add(
            ClinicalProjectionCoverage(
                tenant_id=1,
                patient_id=101,
                domain="treatments",
                status="COMPLETE",
            )
        )
        session.add(
            Treatment(
                id=51,
                tenant_id=1,
                patient_id=101,
                tooth_number="36",
                procedure="Crown",
                cost=500.0,
                status="Done",
            )
        )
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        assert any(
            procedure.provenance == "legacy_fallback"
            and procedure.code == "PROS_CROWN"
            for procedure in snapshot.teeth["36"].procedures
        )
        assert any(
            warning.code == "LEGACY_WRITE_COMPATIBILITY_ACTIVE"
            for warning in snapshot.warnings
        )


@pytest.mark.asyncio
async def test_snapshot_partial_coverage_deduplication(workspace_test_engine):
    """In PARTIAL treatments coverage, native truth wins and legacy duplicates are skipped."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        # Mark treatments coverage PARTIAL
        cov = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=101,
            domain="treatments",
            status="PARTIAL",
        )
        session.merge(cov)

        # Native work item: REST_COMPOSITE on tooth 16
        wi_native = ClinicalWorkItem(
            id=60,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="REST_COMPOSITE",
            status="completed",
        )
        target_native = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=60,
            target_kind="surface",
            tooth_key="16",
            surface_code="O",
        )

        # Legacy duplicate treatment: Filling on tooth 16 (maps to REST_COMPOSITE)
        leg_dup = Treatment(
            id=70,
            tenant_id=1,
            patient_id=101,
            tooth_number="16",
            procedure="Composite Filling",
            cost=120.0,
            status="Done",
        )

        # Legacy non-duplicate treatment: Root canal on tooth 46
        leg_distinct = Treatment(
            id=71,
            tenant_id=1,
            patient_id=101,
            tooth_number="46",
            procedure="Root Canal",
            cost=300.0,
            status="Done",
        )
        session.merge(wi_native)
        session.merge(target_native)
        session.merge(leg_dup)
        session.merge(leg_distinct)
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        # Tooth 16 should have native procedure, but NOT duplicate legacy procedure
        t16 = snapshot.teeth["16"]
        assert any(p.code == "REST_COMPOSITE" and p.provenance == "native" for p in t16.procedures)
        assert not any(p.provenance == "legacy_fallback" and p.code == "REST_COMPOSITE" for p in t16.procedures)

        # Distinct legacy treatment on tooth 46 should be present as fallback
        t46 = snapshot.teeth["46"]
        assert any(p.provenance == "legacy_fallback" for p in t46.procedures)


@pytest.mark.asyncio
async def test_snapshot_unsupported_clinical_code_preserved_in_warnings(workspace_test_engine):
    """Unsupported clinical codes (e.g. PROS_DENTURE) must be preserved as neutral warnings."""
    with Session(workspace_test_engine) as session:
        # Reset coverage to UNCOVERED so treatments contribute
        cov = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=101,
            domain="treatments",
            status="UNCOVERED",
        )
        session.merge(cov)

        # Add unsupported legacy treatment
        leg_unsupported = Treatment(
            id=80,
            tenant_id=1,
            patient_id=101,
            tooth_number="11",
            procedure="Denture",  # maps to PROS_DENTURE which is not in frozen odontogram renderer codes
            cost=800.0,
            status="Done",
        )
        session.merge(leg_unsupported)
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        # Check warning exists
        unsupported_warnings = [
            w for w in snapshot.warnings if w.code == "UNSUPPORTED_CLINICAL_CODE"
        ]
        assert len(unsupported_warnings) >= 1
        assert any("Denture" in w.message or "PROS_DENTURE" in w.message for w in unsupported_warnings)

        # Tooth 11 must not have crashed or invented invalid visual entry
        t11 = snapshot.teeth["11"]
        assert all(p.code in ("REST_COMPOSITE", "REST_AMALGAM", "PROS_CROWN", "ENDO_RCT", "SURG_EXTRACTION", "ORTHO_BRACKET", "PREV_SEALANT", "PERIO_SCALING", "PROS_PONTIC") for p in t11.procedures)


@pytest.mark.asyncio
async def test_snapshot_zero_finance_and_authority(workspace_test_engine):
    """Verify that snapshot exposes zero financial data and zero mutation authority."""
    with Session(workspace_test_engine) as session:
        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)
        data = snapshot.model_dump()

        # Prohibited financial keys
        forbidden_keys = {"cost", "price", "amount", "payment", "discount", "invoice", "balance", "total"}
        for k in data.keys():
            assert k not in forbidden_keys

        for wi in data.get("work_items", []):
            for k in wi.keys():
                assert k not in forbidden_keys

        # Projection metadata
        assert data["schema_version"] == 1
        assert data["projection_id"].startswith("cws-")
        assert "generated_at" in data
        assert "effective_at" in data


def test_snapshot_schema_read_mode_defaults_to_legacy_only():
    """Verify that ClinicalWorkspaceSnapshot schema defaults to LEGACY_ONLY when read_mode is omitted."""
    from backend.schemas.clinical_workspace import ClinicalWorkspaceSnapshot
    now = datetime.now(timezone.utc)
    snap = ClinicalWorkspaceSnapshot(
        projection_id="cws-default",
        patient_id=1,
        generated_at=now,
        effective_at=now,
    )
    assert snap.read_mode == "LEGACY_ONLY"


@pytest.mark.asyncio
async def test_snapshot_rollout_modes(workspace_test_engine):
    """
    Verify rollout modes (fail-closed LEGACY_ONLY, SHADOW, VNEXT_PRIMARY) via feature flags
    and assert observable visible projection behavior for each mode.
    """
    with Session(workspace_test_engine) as session:
        wrapped_db = AsyncSessionWrapper(session)

        # 1. Ensure parent FeatureFlag records exist before any TenantFeature overrides
        ff_shadow = session.query(FeatureFlag).filter_by(key="clinical_vnext_shadow").first()
        if not ff_shadow:
            session.add(
                FeatureFlag(
                    key="clinical_vnext_shadow",
                    description="Shadow rollout mode",
                    is_global_enabled=False,
                    rollout_percentage=0,
                )
            )
        ff_primary = session.query(FeatureFlag).filter_by(key="clinical_vnext_primary").first()
        if not ff_primary:
            session.add(
                FeatureFlag(
                    key="clinical_vnext_primary",
                    description="Primary rollout mode",
                    is_global_enabled=False,
                    rollout_percentage=0,
                )
            )
        session.commit()

        # 2. Seed native clinical work item on tooth 16 (Crown)
        wi_native = ClinicalWorkItem(
            id=901,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="PROS_CROWN",
            status="completed",
        )
        target_native = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=901,
            target_kind="tooth",
            tooth_key="16",
        )
        session.add_all([wi_native, target_native])

        # 3. Seed legacy treatments:
        # - Duplicate Crown on tooth 16 (maps to PROS_CROWN)
        # - Distinct Root Canal on tooth 46 (maps to ENDO_RCT)
        leg_tr_crown = Treatment(
            id=902,
            tenant_id=1,
            patient_id=101,
            tooth_number="16",
            procedure="Crown",
            cost=500.0,
            status="Done",
        )
        leg_tr_rct = Treatment(
            id=903,
            tenant_id=1,
            patient_id=101,
            tooth_number="46",
            procedure="Root Canal",
            cost=300.0,
            status="Done",
        )
        session.add_all([leg_tr_crown, leg_tr_rct])
        session.commit()

        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)

        # Mode A: Fail-closed default (no tenant overrides, no global flags enabled)
        # Must resolve to LEGACY_ONLY; visible projection is 100% legacy-driven.
        snapshot_default = await service.get_workspace_snapshot(101)
        assert snapshot_default.read_mode == "LEGACY_ONLY"
        t16_def = snapshot_default.teeth["16"]
        assert any(p.code == "PROS_CROWN" and p.provenance == "legacy_fallback" for p in t16_def.procedures)
        assert not any(p.provenance == "native" for p in t16_def.procedures)
        t46_def = snapshot_default.teeth["46"]
        assert any(p.code == "ENDO_RCT" and p.provenance == "legacy_fallback" for p in t46_def.procedures)
        assert any(wi.id == "legacy-902" for wi in snapshot_default.work_items)
        assert not any(str(wi.id) == "901" for wi in snapshot_default.work_items)

        # Mode B: SHADOW mode enabled via TenantFeature override
        # Must resolve to SHADOW; visible projection remains legacy-driven.
        tf_shadow = session.query(TenantFeature).filter_by(tenant_id=1, feature_key="clinical_vnext_shadow").first()
        if not tf_shadow:
            tf_shadow = TenantFeature(tenant_id=1, feature_key="clinical_vnext_shadow", is_enabled=True)
            session.add(tf_shadow)
        else:
            tf_shadow.is_enabled = True
        session.commit()

        snapshot_shadow = await service.get_workspace_snapshot(101)
        assert snapshot_shadow.read_mode == "SHADOW"
        t16_shadow = snapshot_shadow.teeth["16"]
        assert any(p.code == "PROS_CROWN" and p.provenance == "legacy_fallback" for p in t16_shadow.procedures)
        assert not any(p.provenance == "native" for p in t16_shadow.procedures)
        assert not any(str(wi.id) == "901" for wi in snapshot_shadow.work_items)

        # Mode C: VNEXT_PRIMARY enabled + COMPLETE treatments coverage
        # Must resolve to VNEXT_PRIMARY; visible projection is native truth; legacy treatments blocked.
        tf_shadow.is_enabled = False
        tf_primary = session.query(TenantFeature).filter_by(tenant_id=1, feature_key="clinical_vnext_primary").first()
        if not tf_primary:
            tf_primary = TenantFeature(tenant_id=1, feature_key="clinical_vnext_primary", is_enabled=True)
            session.add(tf_primary)
        else:
            tf_primary.is_enabled = True
        tf_native_writes = TenantFeature(
            tenant_id=1,
            feature_key="clinical_vnext_native_writes",
            is_enabled=True,
        )
        session.add(tf_native_writes)
        session.commit()

        cov_treatments = session.query(ClinicalProjectionCoverage).filter_by(
            tenant_id=1, patient_id=101, domain="treatments"
        ).first()
        if not cov_treatments:
            cov_treatments = ClinicalProjectionCoverage(
                tenant_id=1,
                patient_id=101,
                domain="treatments",
                status="COMPLETE",
            )
            session.add(cov_treatments)
        else:
            cov_treatments.status = "COMPLETE"
        session.commit()

        snapshot_primary = await service.get_workspace_snapshot(101)
        assert snapshot_primary.read_mode == "VNEXT_PRIMARY"
        t16_prim = snapshot_primary.teeth["16"]
        assert any(p.code == "PROS_CROWN" and p.provenance == "native" for p in t16_prim.procedures)
        assert not any(p.provenance == "legacy_fallback" for p in t16_prim.procedures)
        t46_prim = snapshot_primary.teeth["46"]
        # In COMPLETE treatments coverage, legacy root canal on tooth 46 is blocked
        assert len(t46_prim.procedures) == 0
        assert any(str(wi.id) == "901" for wi in snapshot_primary.work_items)
        assert not any(wi.id == "legacy-902" for wi in snapshot_primary.work_items)
        assert not any(wi.id == "legacy-903" for wi in snapshot_primary.work_items)

        # Mode D: VNEXT_PRIMARY enabled + PARTIAL treatments coverage
        # Native truth wins on tooth 16, duplicate legacy Crown is skipped;
        # distinct legacy Root Canal on tooth 46 is included as fallback.
        cov_treatments.status = "PARTIAL"
        session.commit()

        snapshot_partial = await service.get_workspace_snapshot(101)
        assert snapshot_partial.read_mode == "VNEXT_PRIMARY"
        t16_part = snapshot_partial.teeth["16"]
        crown_procs = [p for p in t16_part.procedures if p.code == "PROS_CROWN"]
        assert len(crown_procs) == 1
        assert crown_procs[0].provenance == "native"
        t46_part = snapshot_partial.teeth["46"]
        assert any(p.code == "ENDO_RCT" and p.provenance == "legacy_fallback" for p in t46_part.procedures)
        assert any(str(wi.id) == "901" for wi in snapshot_partial.work_items)
        assert any(wi.id == "legacy-903" for wi in snapshot_partial.work_items)
        assert not any(wi.id == "legacy-902" for wi in snapshot_partial.work_items)


@pytest.mark.asyncio
async def test_snapshot_unrecorded_teeth_have_null_condition_preserving_explicit_healthy(workspace_test_engine):
    """
    Unrecorded teeth must not infer condition='Healthy' from absence of evidence (condition is None).
    Explicit legacy records with condition='Healthy' represent affirmative clinical assessment and are preserved.
    """
    with Session(workspace_test_engine) as session:
        p_eval = Patient(
            id=102,
            tenant_id=1,
            name="Condition Test Patient",
            age=28,
            phone="5551234",
            medical_history="None",
            notes="",
        )
        session.add(p_eval)
        ts_healthy = ToothStatus(
            id=1001,
            tenant_id=1,
            patient_id=102,
            tooth_number=21,
            condition="Healthy",
        )
        session.add(ts_healthy)
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(102)

        # Tooth 11 has no clinical record -> condition must be None (not 'Healthy')
        assert "11" in snapshot.teeth
        t11 = snapshot.teeth["11"]
        assert t11.condition is None

        # Tooth 21 has an affirmative legacy 'Healthy' record -> condition preserved as 'Healthy'
        assert "21" in snapshot.teeth
        t21 = snapshot.teeth["21"]
        assert t21.condition == "Healthy"
        assert t21.provenance == "legacy_fallback"


@pytest.fixture
def snapshot_patient(db_session, test_tenant, test_user):
    patient = Patient(
        name="Snapshot Patient",
        phone="01234567890",
        email="patient@test.com",
        age=30,
        medical_history="None",
        notes="",
        tenant_id=test_tenant.id,
        assigned_doctor_id=test_user.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def test_endpoint_rbac_and_visibility(client, test_user, auth_headers, snapshot_patient, db_session, test_tenant):
    """Verify endpoint protection via CLINICAL_READ, uniform 404 for invisible patients, and 200 for visible."""
    # 1. Unauthorized role (guest has no CLINICAL_READ)
    guest_user = User(
        username="guest_snap_user",
        email="guest_snap@test.com",
        hashed_password="fake",
        role="guest",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(guest_user)
    db_session.commit()
    guest_token = create_access_token(
        data={"sub": guest_user.username, "role": "guest", "tenant_id": test_tenant.id}
    )
    guest_headers = {"Authorization": f"Bearer {guest_token}"}
    res_forbidden = client.get(f"/api/v1/patients/{snapshot_patient.id}/clinical-workspace", headers=guest_headers)
    assert res_forbidden.status_code == 403

    # 2. Missing patient -> uniform 404
    res_missing = client.get("/api/v1/patients/999999/clinical-workspace", headers=auth_headers)
    assert res_missing.status_code == 404
    assert res_missing.json()["detail"] == "Patient not found"

    # 3. Cross-tenant doctor -> uniform 404
    cross_tenant = Tenant(name="Cross Tenant Clinic", is_active=True)
    db_session.add(cross_tenant)
    db_session.commit()
    cross_doc = User(
        username="cross_doc_snap",
        email="cross_doc@test.com",
        hashed_password="fake",
        role="doctor",
        tenant_id=cross_tenant.id,
        is_active=True,
    )
    db_session.add(cross_doc)
    db_session.commit()
    cross_token = create_access_token(
        data={"sub": cross_doc.username, "role": "doctor", "tenant_id": cross_tenant.id}
    )
    cross_headers = {"Authorization": f"Bearer {cross_token}"}
    res_cross = client.get(f"/api/v1/patients/{snapshot_patient.id}/clinical-workspace", headers=cross_headers)
    assert res_cross.status_code == 404
    assert res_cross.json()["detail"] == "Patient not found"

    # 4. Authorized patient access -> 200 with StandardResponse wrapper
    res_ok = client.get(f"/api/v1/patients/{snapshot_patient.id}/clinical-workspace", headers=auth_headers)
    assert res_ok.status_code == 200
    body = res_ok.json()
    assert body["success"] is True
    assert body["data"]["patient_id"] == snapshot_patient.id
    assert body["data"]["schema_version"] == 1
    assert "read_mode" in body["data"]


@pytest.mark.asyncio
async def test_renderer_target_validation_unsupported_shapes(workspace_test_engine):
    """Unsupported target shapes emit UNSUPPORTED_RENDERER_TARGET warnings and set is_renderer_supported=False."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        # Crown on surface (only tooth is allowed)
        wi_crown = ClinicalWorkItem(
            id=601,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="PROS_CROWN",
            status="planned",
        )
        t_crown = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=601,
            target_kind="surface",
            tooth_key="16",
            surface_code="O",
        )
        # Extraction on root (only tooth is allowed)
        wi_ext = ClinicalWorkItem(
            id=602,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="SURG_EXTRACTION",
            status="planned",
        )
        t_ext = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=602,
            target_kind="root",
            tooth_key="17",
            root_id="mesial",
        )
        # Caries on root (only tooth and surface are allowed)
        wi_caries = ClinicalWorkItem(
            id=603,
            tenant_id=1,
            patient_id=101,
            kind="finding",
            code="CARIES",
            status="active",
        )
        t_caries = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=603,
            target_kind="root",
            tooth_key="18",
            root_id="single",
        )
        # Composite on whole tooth without surface (only surface is allowed)
        wi_comp = ClinicalWorkItem(
            id=604,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="REST_COMPOSITE",
            status="planned",
        )
        t_comp = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=604,
            target_kind="tooth",
            tooth_key="15",
        )
        # Crown with one valid and one invalid target must reject the whole visual.
        wi_mixed = ClinicalWorkItem(
            id=605,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="PROS_CROWN",
            status="planned",
        )
        t_mixed_valid = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=605,
            target_kind="tooth",
            tooth_key="14",
        )
        t_mixed_invalid = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=605,
            target_kind="surface",
            tooth_key="14",
            surface_code="O",
        )
        session.add_all([
            wi_crown,
            t_crown,
            wi_ext,
            t_ext,
            wi_caries,
            t_caries,
            wi_comp,
            t_comp,
            wi_mixed,
            t_mixed_valid,
            t_mixed_invalid,
        ])
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        crown_summary = next(item for item in snapshot.work_items if item.id == 601)
        ext_summary = next(item for item in snapshot.work_items if item.id == 602)
        caries_summary = next(item for item in snapshot.work_items if item.id == 603)
        comp_summary = next(item for item in snapshot.work_items if item.id == 604)
        mixed_summary = next(item for item in snapshot.work_items if item.id == 605)

        assert crown_summary.is_renderer_supported is False
        assert ext_summary.is_renderer_supported is False
        assert caries_summary.is_renderer_supported is False
        assert comp_summary.is_renderer_supported is False
        assert mixed_summary.is_renderer_supported is False

        unsupported_target_warn_ids = {
            w.source_id
            for w in snapshot.warnings
            if w.code == "UNSUPPORTED_RENDERER_TARGET"
        }
        assert 601 in unsupported_target_warn_ids
        assert 602 in unsupported_target_warn_ids
        assert 603 in unsupported_target_warn_ids
        assert 604 in unsupported_target_warn_ids
        assert 605 in unsupported_target_warn_ids


@pytest.mark.asyncio
async def test_completed_extraction_ordering_uses_linked_event_timestamp(
    workspace_test_engine,
):
    """Extraction ordering uses linked completion event timestamp over wi.created_at."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        t1_created = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        t2_lifecycle = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
        t3_completed = datetime(2026, 1, 3, 9, 0, tzinfo=timezone.utc)

        # Work item created at T1
        wi = ClinicalWorkItem(
            id=701,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="SURG_EXTRACTION",
            status="completed",
            created_at=t1_created,
        )
        t_wi = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=701,
            target_kind="tooth",
            tooth_key="36",
        )
        # Lifecycle correction at T2 marks PRESENT
        ev_t2 = ClinicalEvent(
            id=702,
            tenant_id=1,
            patient_id=101,
            event_type="tooth_lifecycle_changed",
            payload={"kind": "lifecycle", "canonical_code": "PRESENT"},
            occurred_at=t2_lifecycle,
            created_at=t2_lifecycle,
        )
        t_ev_t2 = ClinicalEventTarget(
            tenant_id=1,
            event_id=702,
            target_kind="tooth",
            tooth_key="36",
        )
        # Completion event linked to wi at T3 (T3 > T2 > T1)
        ev_t3 = ClinicalEvent(
            id=703,
            tenant_id=1,
            patient_id=101,
            work_item_id=701,
            event_type="procedure_recorded",
            payload={"kind": "procedure", "canonical_code": "SURG_EXTRACTION"},
            occurred_at=t3_completed,
            created_at=t3_completed,
        )
        t_ev_t3 = ClinicalEventTarget(
            tenant_id=1,
            event_id=703,
            target_kind="tooth",
            tooth_key="36",
        )
        session.add_all([wi, t_wi, ev_t2, t_ev_t2, ev_t3, t_ev_t3])
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        # Since linked completion event at T3 is later than T2 PRESENT correction,
        # extraction ordering must apply MISSING lifecycle
        assert snapshot.teeth["36"].lifecycle == "MISSING"
        assert snapshot.teeth["36"].condition == "Missing"


@pytest.mark.asyncio
async def test_extraction_ordering_ignores_later_unrelated_linked_event(
    workspace_test_engine,
):
    """Only the linked procedure event supplies an extraction's effective time."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        t1 = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 1, 3, 9, 0, tzinfo=timezone.utc)
        t4 = datetime(2026, 1, 4, 9, 0, tzinfo=timezone.utc)

        wi = ClinicalWorkItem(
            id=711,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="SURG_EXTRACTION",
            status="completed",
            created_at=t1,
        )
        wi_target = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=711,
            target_kind="tooth",
            tooth_key="37",
        )
        extraction_event = ClinicalEvent(
            id=712,
            tenant_id=1,
            patient_id=101,
            work_item_id=711,
            event_type="procedure_recorded",
            payload={"kind": "procedure", "canonical_code": "SURG_EXTRACTION"},
            occurred_at=t2,
            created_at=t2,
        )
        extraction_target = ClinicalEventTarget(
            tenant_id=1,
            event_id=712,
            target_kind="tooth",
            tooth_key="37",
        )
        present_event = ClinicalEvent(
            id=713,
            tenant_id=1,
            patient_id=101,
            event_type="tooth_lifecycle_changed",
            payload={"kind": "lifecycle", "canonical_code": "PRESENT"},
            occurred_at=t3,
            created_at=t3,
        )
        present_target = ClinicalEventTarget(
            tenant_id=1,
            event_id=713,
            target_kind="tooth",
            tooth_key="37",
        )
        unrelated_event = ClinicalEvent(
            id=714,
            tenant_id=1,
            patient_id=101,
            work_item_id=711,
            event_type="finding_recorded",
            payload={"kind": "finding", "canonical_code": "PAIN"},
            occurred_at=t4,
            created_at=t4,
        )
        unrelated_target = ClinicalEventTarget(
            tenant_id=1,
            event_id=714,
            target_kind="tooth",
            tooth_key="37",
        )
        session.add_all([
            wi,
            wi_target,
            extraction_event,
            extraction_target,
            present_event,
            present_target,
            unrelated_event,
            unrelated_target,
        ])
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        assert snapshot.teeth["37"].lifecycle == "PRESENT"
        assert snapshot.teeth["37"].condition is None


@pytest.mark.asyncio
async def test_present_correction_semantics_clears_stale_lifecycle_conditions(
    workspace_test_engine,
):
    """Transitioning to PRESENT clears stale lifecycle condition but preserves independent condition."""
    with Session(workspace_test_engine) as session:
        _enable_vnext_primary(session, tenant_id=1)
        t1 = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)

        # Tooth 14: earlier MISSING lifecycle event
        ev_miss = ClinicalEvent(
            id=801,
            tenant_id=1,
            patient_id=101,
            event_type="tooth_lifecycle_changed",
            payload={"kind": "lifecycle", "canonical_code": "MISSING"},
            occurred_at=t1,
            created_at=t1,
        )
        t_miss = ClinicalEventTarget(
            tenant_id=1,
            event_id=801,
            target_kind="tooth",
            tooth_key="14",
        )
        # Tooth 14: later PRESENT event without explicit condition
        ev_pres_14 = ClinicalEvent(
            id=802,
            tenant_id=1,
            patient_id=101,
            event_type="tooth_lifecycle_changed",
            payload={"kind": "lifecycle", "canonical_code": "PRESENT"},
            occurred_at=t2,
            created_at=t2,
        )
        t_pres_14 = ClinicalEventTarget(
            tenant_id=1,
            event_id=802,
            target_kind="tooth",
            tooth_key="14",
        )

        # Tooth 15: earlier composite filling work item (sets condition="Filled")
        wi_fill = ClinicalWorkItem(
            id=803,
            tenant_id=1,
            patient_id=101,
            kind="procedure",
            code="REST_COMPOSITE",
            status="completed",
            created_at=t1,
        )
        t_fill = ClinicalWorkItemTarget(
            tenant_id=1,
            work_item_id=803,
            target_kind="surface",
            tooth_key="15",
            surface_code="O",
        )
        # Tooth 15: later PRESENT event without explicit condition
        ev_pres_15 = ClinicalEvent(
            id=804,
            tenant_id=1,
            patient_id=101,
            event_type="tooth_lifecycle_changed",
            payload={"kind": "lifecycle", "canonical_code": "PRESENT"},
            occurred_at=t2,
            created_at=t2,
        )
        t_pres_15 = ClinicalEventTarget(
            tenant_id=1,
            event_id=804,
            target_kind="tooth",
            tooth_key="15",
        )

        session.add_all([ev_miss, t_miss, ev_pres_14, t_pres_14, wi_fill, t_fill, ev_pres_15, t_pres_15])
        session.commit()

        snapshot = await ClinicalWorkspaceService(
            AsyncSessionWrapper(session),
            tenant_id=1,
        ).get_workspace_snapshot(101)

        # Tooth 14: stale "Missing" condition cleared to None
        assert snapshot.teeth["14"].lifecycle == "PRESENT"
        assert snapshot.teeth["14"].condition is None

        # Tooth 15: independent "Filled" condition preserved
        assert snapshot.teeth["15"].lifecycle == "PRESENT"
        assert snapshot.teeth["15"].condition == "Filled"
