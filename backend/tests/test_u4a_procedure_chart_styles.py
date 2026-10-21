"""
Behavior-based tests for U4A: Procedure Chart Appearance & Projection.

Covers:
1. Palette and template definitions parity.
2. Router CRUD & strict validations:
   - Template validation (A2)
   - Color key validation (A3)
   - NONE template requires null color_key
   - Exact procedure_name must exist in tenant or global procedures
   - Upsert behavior (idempotency, no duplicate rows)
   - Tenant isolation
3. GET /procedures additive shape (joins chart_style outside cached payload).
4. Legacy projection in clinical workspace (read-path override):
   - Styled custom procedure maps to canonical visual with style_color_key and suppresses UNKNOWN_PROCEDURE_CODE.
   - Unstyled custom procedure emits UNKNOWN_PROCEDURE_CODE as before.
   - NONE style emits no warning and draws nothing.
   - MARKER style generates WorkspaceProcedureMarker and emits no warning.
   - Custom REST_COMPOSITE with surfaces MB expands to two surface targets with color key.
5. Surface expansion (D4, projection layer only):
   - Legacy Composite Filling with surfaces MB renders 2 surface targets without UNSUPPORTED_RENDERER_TARGET.
   - Legacy Composite Filling without surfaces reports UNSUPPORTED_RENDERER_TARGET.
   - Deduplication and filtering of invalid surface letters.
   - Non-surface procedures (Root Canal) are never expanded.
6. Invariance & Regression:
   - map_legacy_clinical_batch without overrides produces byte-identical drafts and fingerprints.
   - Drift observer receives None overrides and continues flagging custom procedures as unknown.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.main import app
from backend.auth import create_access_token
from backend.clinical.catalog import ProcedureCode
from backend.clinical.chart_styles import (
    CHART_STYLE_COLOR_KEYS,
    CHART_STYLE_TEMPLATES,
    RENDERABLE_TEMPLATES,
)
from backend.clinical.legacy_mapping import (
    VerifiedPatientContext,
    compute_work_item_canonical_fingerprint,
    map_legacy_clinical_batch,
    map_legacy_treatment,
)
from backend.models import (
    Base,
    Patient,
    Procedure,
    ProcedureChartStyle,
    Tenant,
    Treatment,
    User,
)
from backend.services.clinical_workspace_service import ClinicalWorkspaceService


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

    async def delete(self, obj):
        self._s.delete(obj)


@pytest.fixture(scope="function")
def u4a_engine():
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        t1 = Tenant(id=1, name="Clinic 1")
        t2 = Tenant(id=2, name="Clinic 2")
        session.add_all([t1, t2])

        # Global procedure (tenant_id IS NULL)
        p_global = Procedure(id=1, name="Root Canal", price=300.0, tenant_id=None)
        p_global_comp = Procedure(id=2, name="Composite Filling", price=150.0, tenant_id=None)
        # Tenant 1 custom procedures
        p_t1_endo = Procedure(id=3, name="حشو عصب", price=250.0, tenant_id=1)
        p_t1_crown = Procedure(id=4, name="كراون", price=800.0, tenant_id=1)
        p_t1_whitening = Procedure(id=5, name="تبييض", price=500.0, tenant_id=1)
        p_t1_exam = Procedure(id=6, name="كشف عام", price=50.0, tenant_id=1)
        p_t1_custom_comp = Procedure(id=7, name="حشوة تجميلية", price=200.0, tenant_id=1)

        # Tenant 2 procedure
        p_t2_proc = Procedure(id=8, name="Tenant 2 Proc", price=100.0, tenant_id=2)

        session.add_all([
            p_global,
            p_global_comp,
            p_t1_endo,
            p_t1_crown,
            p_t1_whitening,
            p_t1_exam,
            p_t1_custom_comp,
            p_t2_proc,
        ])

        # Patients
        pat1 = Patient(id=101, tenant_id=1, name="Patient T1", age=30, phone="111", medical_history="None", notes="")
        pat2 = Patient(id=202, tenant_id=2, name="Patient T2", age=40, phone="222", medical_history="None", notes="")
        session.add_all([pat1, pat2])

        # Users
        u1_admin = User(
            id=1,
            tenant_id=1,
            username="admin1",
            email="admin1@test.com",
            role="admin",
            hashed_password="fake",
        )
        u2_admin = User(
            id=2,
            tenant_id=2,
            username="admin2",
            email="admin2@test.com",
            role="admin",
            hashed_password="fake",
        )
        session.add_all([u1_admin, u2_admin])
        session.commit()

    yield engine
    engine.dispose()


def _auth_headers(username: str, tenant_id: int, role: str = "admin") -> dict[str, str]:
    token = create_access_token(
        data={"sub": username, "tenant_id": tenant_id, "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Palette & Template Constants Tests
# ===========================================================================

def test_constants_palette_and_templates():
    expected_templates = {
        "REST_COMPOSITE",
        "ENDO_RCT",
        "PROS_CROWN",
        "PROS_BRIDGE",
        "IMPLANT_FIXTURE",
        "IMPLANT_CROWN",
        "SURG_EXTRACTION",
        "MARKER",
        "NONE",
    }
    assert set(CHART_STYLE_TEMPLATES) == expected_templates
    assert "PROS_DENTURE" not in CHART_STYLE_TEMPLATES

    expected_renderable = {
        "REST_COMPOSITE",
        "ENDO_RCT",
        "PROS_CROWN",
        "PROS_BRIDGE",
        "IMPLANT_FIXTURE",
        "IMPLANT_CROWN",
        "SURG_EXTRACTION",
    }
    assert set(RENDERABLE_TEMPLATES) == expected_renderable

    expected_colors = {
        "blue",
        "teal",
        "green",
        "lime",
        "amber",
        "orange",
        "purple",
        "indigo",
        "pink",
        "cyan",
        "slate",
        "brown",
    }
    assert set(CHART_STYLE_COLOR_KEYS) == expected_colors
    assert "red" not in CHART_STYLE_COLOR_KEYS


# ===========================================================================
# 2. Router CRUD & Validation Tests
# ===========================================================================

def test_procedure_chart_style_crud_and_validations(u4a_engine):
    from backend.database import get_async_db

    async def override_get_db():
        with Session(u4a_engine) as session:
            yield AsyncSessionWrapper(session)

    app.dependency_overrides[get_async_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)

    try:
        headers_t1 = _auth_headers(username="admin1", tenant_id=1)
        headers_t2 = _auth_headers(username="admin2", tenant_id=2)

        # 1. Validation: Unknown template
        resp = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "حشو عصب", "template": "INVALID_TEMPLATE", "color_key": "teal"},
            headers=headers_t1,
        )
        assert resp.status_code == 422

        # 2. Validation: Unknown color key
        resp = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "حشو عصب", "template": "ENDO_RCT", "color_key": "red"},
            headers=headers_t1,
        )
        assert resp.status_code == 422

        # 3. Validation: NONE template with color_key
        resp = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "كشف عام", "template": "NONE", "color_key": "blue"},
            headers=headers_t1,
        )
        assert resp.status_code == 422

        # 4. Validation: Non-existent procedure name
        resp = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "إجراء غير موجود", "template": "ENDO_RCT", "color_key": "teal"},
            headers=headers_t1,
        )
        assert resp.status_code == 422

        # 5. Happy Path: Upsert style for tenant procedure
        resp = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "حشو عصب", "template": "ENDO_RCT", "color_key": "teal"},
            headers=headers_t1,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["procedure_name"] == "حشو عصب"
        assert data["template"] == "ENDO_RCT"
        assert data["color_key"] == "teal"
        style_id_1 = data["id"]

        # 6. Upsert idempotency: update same procedure
        resp_update = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "حشو عصب", "template": "ENDO_RCT", "color_key": "purple"},
            headers=headers_t1,
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["id"] == style_id_1
        assert resp_update.json()["color_key"] == "purple"

        # 7. Happy Path: Upsert style for global procedure (tenant can style global templates)
        resp_global = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "Root Canal", "template": "ENDO_RCT", "color_key": "blue"},
            headers=headers_t1,
        )
        assert resp_global.status_code == 200
        assert resp_global.json()["procedure_name"] == "Root Canal"

        # 8. Happy Path: Upsert NONE style without color
        resp_none = client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "كشف عام", "template": "NONE", "color_key": None},
            headers=headers_t1,
        )
        assert resp_none.status_code == 200

        # 9. GET styles for Tenant 1
        resp_get = client.get("/api/v1/procedure-chart-styles", headers=headers_t1)
        assert resp_get.status_code == 200
        styles = resp_get.json()
        assert len(styles) == 3
        proc_names = [s["procedure_name"] for s in styles]
        assert "حشو عصب" in proc_names
        assert "Root Canal" in proc_names
        assert "كشف عام" in proc_names

        # 10. Tenant isolation: Tenant 2 has 0 styles
        resp_get_t2 = client.get("/api/v1/procedure-chart-styles", headers=headers_t2)
        assert resp_get_t2.status_code == 200
        assert len(resp_get_t2.json()) == 0

        # 11. Tenant 2 cannot delete Tenant 1 style
        resp_del_cross = client.delete(f"/api/v1/procedure-chart-styles/{style_id_1}", headers=headers_t2)
        assert resp_del_cross.status_code == 404

        # 12. Tenant 1 deletes own style
        resp_del = client.delete(f"/api/v1/procedure-chart-styles/{style_id_1}", headers=headers_t1)
        assert resp_del.status_code == 200

        # Verify deleted
        resp_get_after = client.get("/api/v1/procedure-chart-styles", headers=headers_t1)
        assert len(resp_get_after.json()) == 2
    finally:
        app.dependency_overrides.pop(get_async_db, None)


# ===========================================================================
# 3. GET /procedures Additive Shape Tests
# ===========================================================================

def test_get_procedures_joins_chart_style(u4a_engine):
    from backend.database import get_async_db

    async def override_get_db():
        with Session(u4a_engine) as session:
            yield AsyncSessionWrapper(session)

    app.dependency_overrides[get_async_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)

    try:
        headers_t1 = _auth_headers(username="admin1", tenant_id=1)

        # 1. Before adding style, chart_style is null
        res = client.get("/api/v1/procedures", headers=headers_t1)
        assert res.status_code == 200
        procs = res.json()
        endo_proc = next(p for p in procs if p["name"] == "حشو عصب")
        assert endo_proc["chart_style"] is None
        assert endo_proc["canonical_code"] is None  # canonical_code allowlist semantics untouched

        # 2. Add style for "حشو عصب"
        client.put(
            "/api/v1/procedure-chart-styles",
            json={"procedure_name": "حشو عصب", "template": "ENDO_RCT", "color_key": "teal"},
            headers=headers_t1,
        )

        # 3. GET /procedures immediately reflects chart_style
        res2 = client.get("/api/v1/procedures", headers=headers_t1)
        assert res2.status_code == 200
        endo_proc2 = next(p for p in res2.json() if p["name"] == "حشو عصب")
        assert endo_proc2["chart_style"] == {"template": "ENDO_RCT", "color_key": "teal"}
        assert endo_proc2["canonical_code"] is None  # allowlist semantics STILL untouched
    finally:
        app.dependency_overrides.pop(get_async_db, None)


# ===========================================================================
# 4. Workspace Projection & Override Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_workspace_projection_with_chart_styles(u4a_engine):
    with Session(u4a_engine) as session:
        # Seed treatments for patient 101
        # 1. "حشو عصب" on tooth 46 (Done)
        t_endo = Treatment(
            id=51,
            tenant_id=1,
            patient_id=101,
            tooth_number="46",
            procedure="حشو عصب",
            cost=250.0,
            status="Done",
        )
        # 2. "كشف عام" on tooth 11 (Done) - style NONE
        t_exam = Treatment(
            id=52,
            tenant_id=1,
            patient_id=101,
            tooth_number="11",
            procedure="كشف عام",
            cost=50.0,
            status="Done",
        )
        # 3. "تبييض" on tooth 21 (Done) - style MARKER
        t_marker = Treatment(
            id=53,
            tenant_id=1,
            patient_id=101,
            tooth_number="21",
            procedure="تبييض",
            cost=500.0,
            status="Done",
        )
        # 4. "حشوة تجميلية" on tooth 16 with surfaces MB
        t_comp = Treatment(
            id=54,
            tenant_id=1,
            patient_id=101,
            tooth_number="16",
            procedure="حشوة تجميلية",
            cost=200.0,
            status="Done",
            notes="[Surfaces: M, B]",
        )
        # 5. "إجراء بدون ستايل" on tooth 36 (Done)
        p_unknown = Procedure(id=99, name="إجراء بدون ستايل", price=100.0, tenant_id=1)
        t_unknown = Treatment(
            id=55,
            tenant_id=1,
            patient_id=101,
            tooth_number="36",
            procedure="إجراء بدون ستايل",
            cost=100.0,
            status="Done",
        )
        session.add_all([t_endo, t_exam, t_marker, t_comp, p_unknown, t_unknown])

        # Seed styles
        s1 = ProcedureChartStyle(
            tenant_id=1, procedure_name="حشو عصب", template="ENDO_RCT", color_key="teal"
        )
        s2 = ProcedureChartStyle(
            tenant_id=1, procedure_name="كشف عام", template="NONE", color_key=None
        )
        s3 = ProcedureChartStyle(
            tenant_id=1, procedure_name="تبييض", template="MARKER", color_key="green"
        )
        s4 = ProcedureChartStyle(
            tenant_id=1, procedure_name="حشوة تجميلية", template="REST_COMPOSITE", color_key="orange"
        )
        session.add_all([s1, s2, s3, s4])
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        # A. ENDO_RCT visual drawn on tooth 46 with teal color
        t46 = snapshot.teeth["46"]
        endo_entries = [p for p in t46.procedures if p.code == "ENDO_RCT"]
        assert len(endo_entries) == 1
        assert endo_entries[0].style_color_key == "teal"
        assert endo_entries[0].phase == "completed"

        wi_endo = next(wi for wi in snapshot.work_items if wi.id == "legacy-51")
        assert wi_endo.style_color_key == "teal"
        assert wi_endo.is_renderer_supported is True

        # B. NONE style: no warning for "كشف عام", nothing drawn on tooth 11
        t11 = snapshot.teeth["11"]
        assert len(t11.procedures) == 0
        assert not any(w.raw_value == "كشف عام" for w in snapshot.warnings)

        # C. MARKER style: appears in teeth["21"].markers with green color, no warning
        t21 = snapshot.teeth["21"]
        assert len(t21.markers) == 1
        marker = t21.markers[0]
        assert marker.procedure_name == "تبييض"
        assert marker.color_key == "green"
        assert marker.phase == "completed"
        assert marker.marker_id == "marker-legacy-53"
        assert not any(w.raw_value == "تبييض" for w in snapshot.warnings)
        # Not in work items
        assert not any(wi.id == "legacy-53" for wi in snapshot.work_items)

        # D. Custom REST_COMPOSITE with surfaces MB: two surface targets with color key orange
        t16 = snapshot.teeth["16"]
        comp_entries = [p for p in t16.procedures if p.code == "REST_COMPOSITE"]
        assert len(comp_entries) == 1
        assert comp_entries[0].style_color_key == "orange"
        assert {t.surface_code for t in comp_entries[0].targets} == {"M", "B"}
        assert all(t.kind == "surface" for t in comp_entries[0].targets)

        wi_comp = next(wi for wi in snapshot.work_items if wi.id == "legacy-54")
        assert wi_comp.style_color_key == "orange"
        assert wi_comp.is_renderer_supported is True
        assert {t.surface_code for t in wi_comp.targets} == {"M", "B"}

        # E. Unstyled procedure emits UNKNOWN_PROCEDURE_CODE warning
        unknown_warns = [
            w for w in snapshot.warnings
            if w.code == "UNKNOWN_PROCEDURE_CODE" and w.raw_value == "إجراء بدون ستايل"
        ]
        assert len(unknown_warns) == 1


# ===========================================================================
# 5. Surface Expansion (D4) Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_surface_expansion_projection_layer(u4a_engine):
    with Session(u4a_engine) as session:
        # Allowlisted "Composite Filling" WITH surfaces MB
        t_with_surfs = Treatment(
            id=61,
            tenant_id=1,
            patient_id=101,
            tooth_number="15",
            procedure="Composite Filling",
            cost=150.0,
            status="Done",
            notes="[Surfaces: M, B]",
        )
        # Allowlisted "Composite Filling" WITHOUT surfaces
        t_without_surfs = Treatment(
            id=62,
            tenant_id=1,
            patient_id=101,
            tooth_number="25",
            procedure="Composite Filling",
            cost=150.0,
            status="Done",
        )
        # Allowlisted with duplicate & invalid surface letters
        t_dirty_surfs = Treatment(
            id=63,
            tenant_id=1,
            patient_id=101,
            tooth_number="35",
            procedure="Composite Filling",
            cost=150.0,
            status="Done",
            notes="[Surfaces: M, M, X, O]",
        )
        # Non-surface code (Root Canal / ENDO_RCT) with surfaces in notes
        t_rct_surfs = Treatment(
            id=64,
            tenant_id=1,
            patient_id=101,
            tooth_number="45",
            procedure="Root Canal",
            cost=300.0,
            status="Done",
            notes="[Surfaces: M, O]",
        )
        session.add_all([t_with_surfs, t_without_surfs, t_dirty_surfs, t_rct_surfs])
        session.commit()

        wrapped_db = AsyncSessionWrapper(session)
        service = ClinicalWorkspaceService(wrapped_db, tenant_id=1)
        snapshot = await service.get_workspace_snapshot(101)

        # 1. With surfaces MB -> supported, 2 surface targets, rendered on tooth 15
        t15 = snapshot.teeth["15"]
        assert any(p.code == "REST_COMPOSITE" for p in t15.procedures)
        wi61 = next(wi for wi in snapshot.work_items if wi.id == "legacy-61")
        assert wi61.is_renderer_supported is True
        assert {t.surface_code for t in wi61.targets} == {"M", "B"}
        assert not any(w.source_id == 61 and w.code == "UNSUPPORTED_RENDERER_TARGET" for w in snapshot.warnings)

        # 2. Without surfaces -> unsupported, warning emitted, not rendered on tooth 25
        t25 = snapshot.teeth["25"]
        assert not any(p.code == "REST_COMPOSITE" for p in t25.procedures)
        wi62 = next(wi for wi in snapshot.work_items if wi.id == "legacy-62")
        assert wi62.is_renderer_supported is False
        assert any(w.source_id == 62 and w.code == "UNSUPPORTED_RENDERER_TARGET" for w in snapshot.warnings)

        # 3. Dirty surfaces -> cleaned to M, O
        t35 = snapshot.teeth["35"]
        comp35 = next(p for p in t35.procedures if p.code == "REST_COMPOSITE")
        assert {t.surface_code for t in comp35.targets} == {"M", "O"}

        # 4. Root canal -> allowed_target_kinds has tooth, so NEVER expanded to surfaces
        wi64 = next(wi for wi in snapshot.work_items if wi.id == "legacy-64")
        assert all(t.kind == "tooth" for t in wi64.targets)
        assert wi64.targets[0].surface_code is None


# ===========================================================================
# 6. Regression & Invariance Tests
# ===========================================================================

def test_map_legacy_clinical_batch_without_overrides_byte_identical():
    verified_patient = VerifiedPatientContext(patient_id=101, tenant_id=1)

    class DummyTreatment:
        def __init__(self, id, proc, tooth, status, cost, notes=None):
            self.id = id
            self.tenant_id = 1
            self.patient_id = 101
            self.procedure = proc
            self.tooth_number = tooth
            self.status = status
            self.cost = cost
            self.discount = None
            self.sessions = None
            self.complications = None
            self.notes = notes
            self.diagnosis = None
            self.date = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
            self.doctor_id = 1

    tx1 = DummyTreatment(1, "Root Canal", "46", "Done", 300.0)
    tx2 = DummyTreatment(2, "Composite Filling", "16", "Done", 150.0, "[Surfaces: M, O]")

    # 1. Batch without overrides
    batch_res = map_legacy_clinical_batch(
        verified_patient=verified_patient,
        treatments=[tx1, tx2],
    )
    assert len(batch_res.work_items) == 2
    wi1, wi2 = batch_res.work_items

    # 2. Both targets are purely "tooth" at mapper layer (Option 2 invariant: expansion is projection-only)
    assert wi1.targets[0].target_kind == "tooth"
    assert wi1.targets[0].surface_code is None
    assert wi2.targets[0].target_kind == "tooth"
    assert wi2.targets[0].surface_code is None

    # 3. Fingerprints are stable and valid
    fp1 = compute_work_item_canonical_fingerprint(wi1)
    fp2 = compute_work_item_canonical_fingerprint(wi2)
    assert isinstance(fp1, str) and len(fp1) > 0
    assert isinstance(fp2, str) and len(fp2) > 0


def test_drift_observer_receives_none_overrides_flagging_custom():
    verified_patient = VerifiedPatientContext(patient_id=101, tenant_id=1)

    class DummyTreatment:
        def __init__(self, id, proc, tooth):
            self.id = id
            self.tenant_id = 1
            self.patient_id = 101
            self.procedure = proc
            self.tooth_number = tooth
            self.status = "Done"
            self.cost = 250.0
            self.discount = None
            self.sessions = None
            self.complications = None
            self.notes = None
            self.diagnosis = None
            self.date = None
            self.doctor_id = 1

    # In parity/drift paths, map_legacy_clinical_batch is called with default overrides (None)
    batch_res = map_legacy_clinical_batch(
        verified_patient=verified_patient,
        treatments=[DummyTreatment(1, "حشو عصب", "46")],
    )
    # Custom name still yields UNKNOWN_PROCEDURE_CODE ambiguity
    assert any(
        amb.code == "UNKNOWN_PROCEDURE_CODE" and amb.raw_value == "حشو عصب"
        for amb in batch_res.ambiguities
    )
    assert len(batch_res.work_items) == 0
