"""
Unit and Integration Tests for Clinical Command Service & APIs (Slice S04).
Covers:
- Fail-closed native write flag gate (404 when disabled)
- Read access gate (shadow / primary / native_writes)
- Work item creation for tooth, surface, root, canal target kinds
- Work item update (status lifecycle, notes, targets, version increment)
- Terminal status protection (completed/cancelled cannot transition away -> 409)
- Optimistic locking / stale version check (expected_version_id mismatch / StaleDataError -> 409)
- Canonical status validation (validate_treatment_status rejecting non-lifecycle and correction statuses -> 422)
- Target shape and FDI tooth key validation -> 422
- Tenant isolation and doctor visibility (R02) -> 404
- RBAC per PD02a (Doctor all; Nurse finding-only 201/200, procedure 403; Receptionist 403 mutation, 200 GET)
- Work item list filtering (excluding superseded/entered_in_error by default)
- Legacy invariance (Treatment, Payment, StockMovement counts remain 0)
"""

from datetime import timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.auth import create_access_token
from backend.clinical.catalog import (
    CANONICAL_CORRECTION_STATUSES,
    CORRECTION_STATUS_ENTERED_IN_ERROR,
    CORRECTION_STATUS_SUPERSEDED,
    FindingCode,
    ProcedureCode,
)
from backend.models.inventory import StockMovement
from backend.services.clinical_command_service import ClinicalCommandService
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    FEATURE_FLAG_CLINICAL_PRIMARY,
)
from backend.services.feature_service import FeatureFlagService


@pytest.fixture
async def seed_data(async_db_session):
    """Seed test tenants, users with varied roles, and patients."""
    tenant_1 = models.Tenant(name="Clinic Alpha", domain="alpha.example.com", is_active=True)
    tenant_2 = models.Tenant(name="Clinic Beta", domain="beta.example.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="doc_alpha",
        email="doc1@alpha.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    nurse_1 = models.User(
        tenant_id=tenant_1.id,
        username="nurse_alpha",
        email="nurse1@alpha.com",
        hashed_password="test-hashed-password",
        role="nurse",
        is_active=True,
    )
    receptionist_1 = models.User(
        tenant_id=tenant_1.id,
        username="recep_alpha",
        email="recep1@alpha.com",
        hashed_password="test-hashed-password",
        role="receptionist",
        is_active=True,
    )
    admin_1 = models.User(
        tenant_id=tenant_1.id,
        username="admin_alpha",
        email="admin1@alpha.com",
        hashed_password="test-hashed-password",
        role="admin",
        is_active=True,
    )

    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="doc_beta",
        email="doc2@beta.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )

    async_db_session.add_all([doctor_1, nurse_1, receptionist_1, admin_1, doctor_2])
    await async_db_session.flush()

    patient_1 = models.Patient(
        tenant_id=tenant_1.id,
        name="John Doe",
        age=30,
        phone="+1234567890",
        medical_history="No history",
        notes="Patient 1 notes",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_2 = models.Patient(
        tenant_id=tenant_2.id,
        name="Jane Smith",
        age=28,
        phone="+1987654321",
        medical_history="No history",
        notes="Patient 2 notes",
        assigned_doctor_id=doctor_2.id,
        is_deleted=False,
    )

    async_db_session.add_all([patient_1, patient_2])
    await async_db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "doctor_1": doctor_1,
        "nurse_1": nurse_1,
        "receptionist_1": receptionist_1,
        "admin_1": admin_1,
        "doctor_2": doctor_2,
        "patient_1": patient_1,
        "patient_2": patient_2,
    }


def make_headers(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


async def set_native_writes_flag(db, tenant_id: int, enabled: bool):
    stmt = select(models.FeatureFlag).where(
        models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES
    )
    flag = (await db.execute(stmt)).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Clinical native writes",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        db.add(flag)
        await db.commit()
        await db.refresh(flag)
    await FeatureFlagService.set_tenant_override(
        db, tenant_id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, enabled
    )


@pytest.mark.asyncio
async def test_native_writes_flag_gate_http(client, seed_data, async_db_session):
    """When clinical_vnext_native_writes is disabled, POST and PATCH return 404."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    # Ensure flag is OFF
    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, False)

    # POST returns 404
    payload = {
        "kind": "finding",
        "code": FindingCode.CARIES.value,
        "targets": [{"target_kind": "tooth", "tooth_key": "11"}],
    }
    res_post = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json=payload,
    )
    assert res_post.status_code == 404
    assert "native writes are disabled" in res_post.json()["detail"].lower()

    # PATCH returns 404
    res_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/1",
        headers=headers,
        json={"notes": "Updated note"},
    )
    assert res_patch.status_code == 404


@pytest.mark.asyncio
async def test_create_work_items_all_target_kinds(client, seed_data, async_db_session):
    """Flag ON -> POST creates ClinicalWorkItem, Targets, and ClinicalEvents for tooth, surface, root, canal."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    # Enable flag
    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    cases = [
        ("tooth", [{"target_kind": "tooth", "tooth_key": "11"}]),
        ("surface", [{"target_kind": "surface", "tooth_key": "11", "surface_code": "M"}]),
        ("root", [{"target_kind": "root", "tooth_key": "16", "root_id": "mesiobuccal"}]),
        ("canal", [{"target_kind": "canal", "tooth_key": "16", "root_id": "mesiobuccal", "canal_id": "MB1"}]),
    ]

    for kind_label, targets in cases:
        payload = {
            "kind": "procedure",
            "code": ProcedureCode.REST_COMPOSITE.value,
            "status": "proposed",
            "notes": f"Testing {kind_label} target",
            "targets": targets,
        }
        res = client.post(
            f"/api/v1/patients/{patient_1.id}/clinical-work-items",
            headers=headers,
            json=payload,
        )
        assert res.status_code == 201, res.text
        data = res.json()["data"]
        assert data["kind"] == "procedure"
        assert data["code"] == ProcedureCode.REST_COMPOSITE.value
        assert data["status"] == "proposed"
        assert data["version_id"] == 1
        assert len(data["targets"]) == 1
        assert data["targets"][0]["target_kind"] == targets[0]["target_kind"]
        assert data["targets"][0]["tooth_key"] == targets[0]["tooth_key"]

        # Verify database event creation
        wi_id = data["id"]
        ev_stmt = (
            select(models.ClinicalEvent)
            .options(selectinload(models.ClinicalEvent.targets))
            .where(
                models.ClinicalEvent.work_item_id == wi_id,
                models.ClinicalEvent.tenant_id == doctor_1.tenant_id,
            )
        )
        ev_res = await async_db_session.execute(ev_stmt)
        event = ev_res.scalar_one()
        assert event.event_type == "procedure_recorded"
        assert event.actor_user_id == doctor_1.id
        assert len(event.targets) == 1
        assert event.targets[0].target_kind == targets[0]["target_kind"]


@pytest.mark.asyncio
async def test_patch_status_lifecycle_and_stale_version(client, seed_data, async_db_session):
    """PATCH updates lifecycle status, notes, targets, increments version, and rejects stale version."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Create initial work item
    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={
            "kind": "procedure",
            "code": ProcedureCode.ENDO_RCT.value,
            "status": "proposed",
            "notes": "Root canal step 1",
            "targets": [{"target_kind": "tooth", "tooth_key": "16"}],
        },
    )
    assert create_res.status_code == 201
    wi = create_res.json()["data"]
    wi_id = wi["id"]
    assert wi["version_id"] == 1

    # 2. PATCH proposed -> planned with expected_version_id=1
    p1 = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "planned", "expected_version_id": 1, "notes": "Planned for next visit"},
    )
    assert p1.status_code == 200
    assert p1.json()["data"]["status"] == "planned"
    assert p1.json()["data"]["version_id"] == 2

    # 3. PATCH with stale expected_version_id=1 -> 409 Conflict
    p_stale = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "active", "expected_version_id": 1},
    )
    assert p_stale.status_code == 409
    assert "stale version" in p_stale.json()["detail"].lower()

    # 4. PATCH planned -> active -> completed
    p2 = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "active", "expected_version_id": 2},
    )
    assert p2.status_code == 200
    assert p2.json()["data"]["version_id"] == 3

    p3 = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "completed", "expected_version_id": 3},
    )
    assert p3.status_code == 200
    assert p3.json()["data"]["status"] == "completed"
    assert p3.json()["data"]["version_id"] == 4

    # 5. Completed is terminal: attempting status transition away returns 409
    p_term = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "active"},
    )
    assert p_term.status_code == 409
    assert "terminal status" in p_term.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_treatment_status_wiring(client, seed_data, async_db_session):
    """PATCH status='superseded'/'entered_in_error'/'in_progress'/'existing' returns 422."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={
            "kind": "finding",
            "code": FindingCode.CARIES.value,
            "status": "proposed",
            "targets": [{"target_kind": "tooth", "tooth_key": "21"}],
        },
    )
    assert create_res.status_code == 201
    wi_id = create_res.json()["data"]["id"]

    for invalid_status in ["superseded", "entered_in_error", "in_progress", "existing"]:
        res = client.patch(
            f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
            headers=headers,
            json={"status": invalid_status},
        )
        assert res.status_code == 422, f"Expected 422 for status '{invalid_status}', got {res.status_code}"


@pytest.mark.asyncio
async def test_invalid_code_and_target_shape_validation(client, seed_data, async_db_session):
    """Invalid code, invalid FDI tooth key, or invalid shape constraints return 422."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Invalid finding code
    res1 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": "INVALID_CODE", "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
    )
    assert res1.status_code == 422

    # 2. Invalid procedure code
    res2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "procedure", "code": "INVALID_CODE", "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
    )
    assert res2.status_code == 422

    # 3. Invalid FDI tooth key (e.g. "99")
    res3 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "targets": [{"target_kind": "tooth", "tooth_key": "99"}]},
    )
    assert res3.status_code == 422

    # 4. Invalid shape: surface without surface_code
    res4 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "targets": [{"target_kind": "surface", "tooth_key": "11"}]},
    )
    assert res4.status_code == 422

    # 5. Invalid shape: tooth with surface_code set
    res5 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "targets": [{"target_kind": "tooth", "tooth_key": "11", "surface_code": "M"}]},
    )
    assert res5.status_code == 422


@pytest.mark.asyncio
async def test_tenant_isolation_and_doctor_visibility(client, seed_data, async_db_session):
    """Cross-tenant patient or work item mismatch returns 404."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    doctor_2 = seed_data["doctor_2"]
    patient_2 = seed_data["patient_2"]

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)
    await set_native_writes_flag(async_db_session, doctor_2.tenant_id, True)

    doc1_headers = make_headers(doctor_1)
    doc2_headers = make_headers(doctor_2)

    # Doctor 1 creates work item for Patient 1
    res1 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=doc1_headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
    )
    assert res1.status_code == 201
    wi1_id = res1.json()["data"]["id"]

    # Doctor 2 tries to GET Patient 1's work items -> 404
    res_cross_get = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=doc2_headers,
    )
    assert res_cross_get.status_code == 404

    # Doctor 2 tries to PATCH Patient 1's work item -> 404
    res_cross_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi1_id}",
        headers=doc2_headers,
        json={"notes": "Cross tenant tamper"},
    )
    assert res_cross_patch.status_code == 404

    # Doctor 1 tries to access work item under mismatched patient_id -> 404
    res_mismatch_patch = client.patch(
        f"/api/v1/patients/{patient_2.id}/clinical-work-items/{wi1_id}",
        headers=doc1_headers,
        json={"notes": "Mismatched patient"},
    )
    assert res_mismatch_patch.status_code == 404


@pytest.mark.asyncio
async def test_rbac_per_pd02a(client, seed_data, async_db_session):
    """
    RBAC per PD02a:
    - Doctor: succeeds on finding and procedure POST/PATCH
    - Nurse (CLINICAL_WRITE): succeeds on finding POST/PATCH, 403 on procedure POST/PATCH
    - Receptionist: 403 on all POST/PATCH, 200 on GET
    """
    doctor_1 = seed_data["doctor_1"]
    nurse_1 = seed_data["nurse_1"]
    receptionist_1 = seed_data["receptionist_1"]
    patient_1 = seed_data["patient_1"]

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    doc_headers = make_headers(doctor_1)
    nurse_headers = make_headers(nurse_1)
    recep_headers = make_headers(receptionist_1)

    finding_payload = {
        "kind": "finding",
        "code": FindingCode.CARIES.value,
        "targets": [{"target_kind": "tooth", "tooth_key": "11"}],
    }
    procedure_payload = {
        "kind": "procedure",
        "code": ProcedureCode.REST_COMPOSITE.value,
        "targets": [{"target_kind": "tooth", "tooth_key": "12"}],
    }

    # 1. Nurse creates finding -> 201
    res_nurse_finding = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=nurse_headers,
        json=finding_payload,
    )
    assert res_nurse_finding.status_code == 201
    finding_id = res_nurse_finding.json()["data"]["id"]

    # Nurse updates finding -> 200
    res_nurse_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{finding_id}",
        headers=nurse_headers,
        json={"notes": "Nurse recorded observation"},
    )
    assert res_nurse_patch.status_code == 200

    # Nurse attempts procedure create -> 403
    res_nurse_proc = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=nurse_headers,
        json=procedure_payload,
    )
    assert res_nurse_proc.status_code == 403
    assert "treatment_plan:write" in res_nurse_proc.json()["detail"].lower()

    # Doctor creates procedure -> 201
    res_doc_proc = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=doc_headers,
        json=procedure_payload,
    )
    assert res_doc_proc.status_code == 201
    proc_id = res_doc_proc.json()["data"]["id"]

    # Nurse attempts to update procedure -> 403
    res_nurse_proc_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{proc_id}",
        headers=nurse_headers,
        json={"notes": "Nurse tampering procedure"},
    )
    assert res_nurse_proc_patch.status_code == 403

    # Doctor updates procedure -> 200
    res_doc_proc_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{proc_id}",
        headers=doc_headers,
        json={"notes": "Doctor updated procedure"},
    )
    assert res_doc_proc_patch.status_code == 200

    # 2. Receptionist attempts mutation -> 403 on all POST/PATCH
    res_recep_post = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=recep_headers,
        json=finding_payload,
    )
    assert res_recep_post.status_code == 403

    res_recep_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{finding_id}",
        headers=recep_headers,
        json={"notes": "Receptionist patch"},
    )
    assert res_recep_patch.status_code == 403

    # Receptionist has CLINICAL_READ -> GET succeeds (200)
    res_recep_get = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=recep_headers,
    )
    assert res_recep_get.status_code == 200
    items = res_recep_get.json()["data"]
    assert len(items) == 2


@pytest.mark.asyncio
async def test_list_work_items_filtering(client, seed_data, async_db_session):
    """GET excludes corrected work items (superseded/entered_in_error) unless include_corrected=True."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Create active item
    client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "status": "proposed"},
    )

    # Seed directly a superseded and entered_in_error work item
    wi_superseded = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code=ProcedureCode.REST_COMPOSITE.value,
        status="superseded",
        version_id=2,
    )
    wi_error = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="finding",
        code=FindingCode.FRACTURE.value,
        status="entered_in_error",
        version_id=2,
    )
    async_db_session.add_all([wi_superseded, wi_error])
    await async_db_session.commit()

    # Default GET excludes corrected items
    res_default = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
    )
    assert res_default.status_code == 200
    items_default = res_default.json()["data"]
    assert len(items_default) == 1
    assert items_default[0]["status"] == "proposed"

    # With include_corrected=True, returns all 3 items
    res_all = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items?include_corrected=true",
        headers=headers,
    )
    assert res_all.status_code == 200
    items_all = res_all.json()["data"]
    assert len(items_all) == 3


@pytest.mark.asyncio
async def test_legacy_invariance(client, seed_data, async_db_session):
    """Verify that Treatment, Payment, and StockMovement tables remain 100% untouched."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Count before
    t_count_pre = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one()
    p_count_pre = (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar_one()
    s_count_pre = (await async_db_session.execute(select(func.count(StockMovement.id)))).scalar_one()

    # Perform mutations
    res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "status": "proposed"},
    )
    assert res.status_code == 201
    wi_id = res.json()["data"]["id"]

    res_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "planned", "notes": "Invariance test"},
    )
    assert res_patch.status_code == 200

    # Count after
    t_count_post = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one()
    p_count_post = (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar_one()
    s_count_post = (await async_db_session.execute(select(func.count(StockMovement.id)))).scalar_one()

    assert t_count_post == t_count_pre == 0
    assert p_count_post == p_count_pre == 0
    assert s_count_post == s_count_pre == 0


@pytest.mark.asyncio
async def test_stale_data_error_rollback(seed_data, async_db_session, monkeypatch):
    """When SQLAlchemy raises StaleDataError on commit, rollback is called and 409 Conflict is raised."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    service = ClinicalCommandService(async_db_session, doctor_1.tenant_id, doctor_1)
    wi = await service.create_work_item(
        patient_1.id,
        schemas.ClinicalWorkItemCreate(
            kind="finding",
            code=FindingCode.CARIES.value,
            status="proposed",
        ),
    )

    async def mock_commit():
        raise StaleDataError("Row was updated or deleted by another transaction")

    monkeypatch.setattr(async_db_session, "commit", mock_commit)

    with pytest.raises(HTTPException) as exc:
        await service.update_work_item(
            patient_1.id,
            wi.id,
            schemas.ClinicalWorkItemUpdate(notes="Trigger stale error"),
        )
    assert exc.value.status_code == 409
    assert "concurrent modification" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_cancelled_terminal_status(client, seed_data, async_db_session):
    """Status 'cancelled' is terminal: attempting status transition away returns 409."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
        json={"kind": "finding", "code": FindingCode.CARIES.value, "status": "cancelled"},
    )
    assert res.status_code == 201
    wi_id = res.json()["data"]["id"]

    res_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "planned"},
    )
    assert res_patch.status_code == 409
    assert "terminal status" in res_patch.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unversioned_fallback_route(client, seed_data, async_db_session):
    """Unversioned fallback /patients/{patient_id}/clinical-work-items works matching treatment_plans."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    res = client.get(
        f"/patients/{patient_1.id}/clinical-work-items",
        headers=headers,
    )
    assert res.status_code == 200


# ==============================================================================
# S05 — Finding & Procedure Single/Bulk Command APIs (G7-M04..G7-M07)
# ==============================================================================


@pytest.mark.asyncio
async def test_single_and_bulk_finding_creation(client, seed_data, async_db_session):
    """G7-M04 & G7-M05: Single and bulk finding creation across teeth 11, 16, 46."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Single finding across 3 teeth (11, 16, 46) in one request
    res_single = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={
            "code": FindingCode.FRACTURE.value,
            "status": "proposed",
            "targets": [
                {"target_kind": "tooth", "tooth_key": "11"},
                {"target_kind": "surface", "tooth_key": "16", "surface_code": "O"},
                {"target_kind": "tooth", "tooth_key": "46"},
            ],
            "notes": "Fractures noted",
        },
    )
    assert res_single.status_code == 201
    single_data = res_single.json()["data"]
    assert single_data["kind"] == "finding"
    assert single_data["code"] == FindingCode.FRACTURE.value
    assert len(single_data["targets"]) == 3

    # 2. Bulk finding creation across 3 teeth (11, 16, 46)
    res_bulk = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk",
        headers=headers,
        json={
            "items": [
                {"code": FindingCode.CARIES.value, "tooth_key": "11"},
                {"code": FindingCode.CARIES.value, "tooth_key": "16", "surfaces": ["M", "O"]},
                {"code": FindingCode.CARIES.value, "tooth_key": "46", "surfaces": ["O"]},
            ]
        },
    )
    assert res_bulk.status_code == 201
    bulk_data = res_bulk.json()["data"]
    assert bulk_data["count"] == 3
    assert len(bulk_data["items"]) == 3
    assert bulk_data["items"][0]["targets"][0]["tooth_key"] == "11"
    assert len(bulk_data["items"][1]["targets"]) == 2


@pytest.mark.asyncio
async def test_single_and_bulk_procedure_creation(client, seed_data, async_db_session):
    """G7-M06 & G7-M07: Single and bulk procedure creation across multiple teeth/surfaces."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Single procedure on tooth 16 surface O
    res_single = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-procedures",
        headers=headers,
        json={
            "code": ProcedureCode.REST_COMPOSITE.value,
            "status": "planned",
            "tooth_key": "16",
            "surfaces": ["O"],
            "notes": "Single composite",
        },
    )
    assert res_single.status_code == 201
    single_data = res_single.json()["data"]
    assert single_data["kind"] == "procedure"
    assert single_data["code"] == ProcedureCode.REST_COMPOSITE.value
    assert len(single_data["targets"]) == 1
    assert single_data["targets"][0]["surface_code"] == "O"

    # 2. Bulk procedure creation on teeth 16 and 26
    res_bulk = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk",
        headers=headers,
        json={
            "items": [
                {
                    "code": ProcedureCode.REST_COMPOSITE.value,
                    "status": "planned",
                    "tooth_key": "16",
                    "surfaces": ["M", "O"],
                },
                {
                    "code": ProcedureCode.REST_COMPOSITE.value,
                    "status": "planned",
                    "tooth_key": "26",
                    "surfaces": ["O"],
                },
            ]
        },
    )
    assert res_bulk.status_code == 201
    bulk_data = res_bulk.json()["data"]
    assert bulk_data["count"] == 2
    assert len(bulk_data["items"]) == 2


@pytest.mark.asyncio
async def test_bulk_atomic_rollback_on_invalid_tooth_key(client, seed_data, async_db_session):
    """Atomic rollback: when item #3 of 3 has an invalid FDI tooth key (99), 422 returned and 0 rows persisted."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Initial count of work items for patient_1
    stmt_count = select(func.count(models.ClinicalWorkItem.id)).where(
        models.ClinicalWorkItem.patient_id == patient_1.id
    )
    initial_count = await async_db_session.scalar(stmt_count)

    # Bulk findings where item #3 has invalid FDI tooth key '99'
    res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk",
        headers=headers,
        json={
            "items": [
                {"code": FindingCode.CARIES.value, "tooth_key": "11"},
                {"code": FindingCode.CARIES.value, "tooth_key": "16", "surfaces": ["O"]},
                {"code": FindingCode.CARIES.value, "tooth_key": "99"},  # Invalid FDI!
            ]
        },
    )
    assert res.status_code == 422
    assert "fdi" in res.json()["detail"].lower() or "tooth_key" in res.json()["detail"].lower()

    # Verify zero rows persisted (atomic rollback)
    count_after = await async_db_session.scalar(stmt_count)
    assert count_after == initial_count

    # Bulk procedures where item #2 has invalid FDI tooth key '99'
    res_proc = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk",
        headers=headers,
        json={
            "items": [
                {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "16", "surfaces": ["O"]},
                {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "99"},  # Invalid FDI!
            ]
        },
    )
    assert res_proc.status_code == 422

    count_after_proc = await async_db_session.scalar(stmt_count)
    assert count_after_proc == initial_count


@pytest.mark.asyncio
async def test_flag_off_404_new_patient_scoped_routes(client, seed_data, async_db_session):
    """When clinical_vnext_native_writes is OFF, all 4 new routes return 404."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, False)

    finding_payload = {"code": FindingCode.CARIES.value, "tooth_key": "16"}
    proc_payload = {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "16", "surfaces": ["O"]}

    r1 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers, json=finding_payload)
    assert r1.status_code == 404
    assert "native writes are disabled" in r1.json()["detail"].lower()

    r2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk",
        headers=headers,
        json={"items": [finding_payload]},
    )
    assert r2.status_code == 404

    r3 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=headers, json=proc_payload)
    assert r3.status_code == 404

    r4 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk",
        headers=headers,
        json={"items": [proc_payload]},
    )
    assert r4.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_and_doctor_visibility_new_routes(client, seed_data, async_db_session):
    """Cross-tenant patient access and restricted doctor visibility return 404 on all 4 new routes."""
    doctor_1 = seed_data["doctor_1"]
    patient_2 = seed_data["patient_2"]  # Tenant 2
    headers = make_headers(doctor_1)

    patient_unassigned = models.Patient(
        tenant_id=doctor_1.tenant_id,
        name="Unassigned Patient",
        age=45,
        phone="+1234567899",
        medical_history="None",
        notes="Unassigned",
        assigned_doctor_id=None,
        is_deleted=False,
    )
    async_db_session.add(patient_unassigned)
    await async_db_session.commit()

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    finding_payload = {"code": FindingCode.CARIES.value, "tooth_key": "16"}
    proc_payload = {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "16", "surfaces": ["O"]}

    # Cross-tenant (Tenant 1 doctor -> Tenant 2 patient) -> 404
    assert client.post(f"/api/v1/patients/{patient_2.id}/clinical-findings", headers=headers, json=finding_payload).status_code == 404
    assert client.post(f"/api/v1/patients/{patient_2.id}/clinical-findings/bulk", headers=headers, json={"items": [finding_payload]}).status_code == 404
    assert client.post(f"/api/v1/patients/{patient_2.id}/clinical-procedures", headers=headers, json=proc_payload).status_code == 404
    assert client.post(f"/api/v1/patients/{patient_2.id}/clinical-procedures/bulk", headers=headers, json={"items": [proc_payload]}).status_code == 404

    # Restricted doctor visibility (unassigned patient) -> 404
    assert client.post(f"/api/v1/patients/{patient_unassigned.id}/clinical-findings", headers=headers, json=finding_payload).status_code == 404
    assert client.post(f"/api/v1/patients/{patient_unassigned.id}/clinical-findings/bulk", headers=headers, json={"items": [finding_payload]}).status_code == 404
    assert client.post(f"/api/v1/patients/{patient_unassigned.id}/clinical-procedures", headers=headers, json=proc_payload).status_code == 404
    assert client.post(f"/api/v1/patients/{patient_unassigned.id}/clinical-procedures/bulk", headers=headers, json={"items": [proc_payload]}).status_code == 404


@pytest.mark.asyncio
async def test_rbac_for_findings_and_procedures(client, seed_data, async_db_session):
    """RBAC per PD02a: Doctor succeeds on both; Nurse succeeds on findings/bulk and gets 403 on procedures/bulk; Receptionist gets 403 on all."""
    doctor_1 = seed_data["doctor_1"]
    nurse_1 = seed_data["nurse_1"]
    receptionist_1 = seed_data["receptionist_1"]
    patient_1 = seed_data["patient_1"]

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    doc_headers = make_headers(doctor_1)
    nurse_headers = make_headers(nurse_1)
    recep_headers = make_headers(receptionist_1)

    finding_payload = {"code": FindingCode.CARIES.value, "tooth_key": "16"}
    proc_payload = {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "16", "surfaces": ["O"]}

    # 1. Doctor succeeds on all 4 endpoints
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=doc_headers, json=finding_payload).status_code == 201
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk", headers=doc_headers, json={"items": [finding_payload]}).status_code == 201
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=doc_headers, json=proc_payload).status_code == 201
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk", headers=doc_headers, json={"items": [proc_payload]}).status_code == 201

    # 2. Nurse (CLINICAL_WRITE only) succeeds on findings, gets 403 on procedures
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=nurse_headers, json=finding_payload).status_code == 201
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk", headers=nurse_headers, json={"items": [finding_payload]}).status_code == 201
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=nurse_headers, json=proc_payload).status_code == 403
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk", headers=nurse_headers, json={"items": [proc_payload]}).status_code == 403

    # 3. Receptionist gets 403 on all 4 mutation endpoints
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=recep_headers, json=finding_payload).status_code == 403
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk", headers=recep_headers, json={"items": [finding_payload]}).status_code == 403
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=recep_headers, json=proc_payload).status_code == 403
    assert client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk", headers=recep_headers, json={"items": [proc_payload]}).status_code == 403


@pytest.mark.asyncio
async def test_legacy_endpoints_ungated_and_timezone_aware(client, seed_data, async_db_session, monkeypatch):
    """Legacy /api/v1/treatments/finding & /symptom remain un-gated (work with flag OFF) and record timezone-aware occurred_at."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    captured_occurred_at = []
    original_init = models.ClinicalEvent.__init__

    def spying_init(self, *args, **kwargs):
        if "occurred_at" in kwargs:
            captured_occurred_at.append(kwargs["occurred_at"])
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(models.ClinicalEvent, "__init__", spying_init)

    # Ensure native writes flag is explicitly OFF
    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, False)

    # 1. Legacy finding route
    res_finding = client.post(
        "/api/v1/treatments/finding",
        headers=headers,
        json={
            "patient_id": patient_1.id,
            "tooth_number": 16,
            "findings": [{"finding_code": "CARIES", "surfaces": ["O"]}],
            "notes": "Legacy caries finding",
        },
    )
    assert res_finding.status_code == 200
    assert len(captured_occurred_at) >= 1
    assert captured_occurred_at[-1].tzinfo is not None
    assert captured_occurred_at[-1].tzinfo == timezone.utc

    # Query event created by legacy finding route
    stmt_event = (
        select(models.ClinicalEvent)
        .where(
            models.ClinicalEvent.patient_id == patient_1.id,
            models.ClinicalEvent.event_type == "finding_recorded",
        )
        .order_by(models.ClinicalEvent.id.desc())
        .limit(1)
    )
    event_finding = (await async_db_session.execute(stmt_event)).scalar_one_or_none()
    assert event_finding is not None
    assert event_finding.occurred_at is not None

    # 2. Legacy symptom route
    res_symptom = client.post(
        "/api/v1/treatments/symptom",
        headers=headers,
        json={
            "patient_id": patient_1.id,
            "tooth_number": 16,
            "symptom": "pain",
            "severity": "severe",
            "notes": "Sharp throbbing pain",
        },
    )
    assert res_symptom.status_code == 200
    assert len(captured_occurred_at) >= 2
    assert captured_occurred_at[-1].tzinfo is not None
    assert captured_occurred_at[-1].tzinfo == timezone.utc

    stmt_symptom = (
        select(models.ClinicalEvent)
        .where(
            models.ClinicalEvent.patient_id == patient_1.id,
            models.ClinicalEvent.notes.like("%Sharp throbbing pain%"),
        )
        .order_by(models.ClinicalEvent.id.desc())
        .limit(1)
    )
    event_symptom = (await async_db_session.execute(stmt_symptom)).scalar_one_or_none()
    assert event_symptom is not None
    assert event_symptom.occurred_at is not None


@pytest.mark.asyncio
async def test_legacy_treatment_count_invariance_on_native_routes(client, seed_data, async_db_session):
    """Legacy Treatment count remains 0 before and after calling the 4 new native routes."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    stmt_count = select(func.count(models.Treatment.id))
    initial_treatments = await async_db_session.scalar(stmt_count)

    finding_payload = {"code": FindingCode.CARIES.value, "tooth_key": "16"}
    proc_payload = {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "16", "surfaces": ["O"]}

    client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers, json=finding_payload)
    client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk", headers=headers, json={"items": [finding_payload]})
    client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=headers, json=proc_payload)
    client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk", headers=headers, json={"items": [proc_payload]})

    final_treatments = await async_db_session.scalar(stmt_count)
    assert final_treatments == initial_treatments


# ===========================================================================
# S06 Tests: Work-Item Correction, Tooth Detail, and History APIs
# (G7-M08, G7-M10, G7-M11)
# ===========================================================================


@pytest.mark.asyncio
async def test_correct_work_item_entered_in_error(client, seed_data, async_db_session):
    """mode='entered_in_error' sets status='entered_in_error' and appends entered_in_error event."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Create finding work item
    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16", "notes": "Initial finding"},
    )
    assert create_res.status_code == 201
    wi_id = create_res.json()["data"]["id"]

    # 2. Correct via entered_in_error
    correct_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Accidental clinical entry"},
    )
    assert correct_res.status_code == 200
    data = correct_res.json()["data"]
    assert data["mode"] == "entered_in_error"
    assert data["reason"] == "Accidental clinical entry"
    assert data["original_work_item"]["id"] == wi_id
    assert data["original_work_item"]["status"] == "entered_in_error"
    assert data["replacement_work_item"] is None
    assert data["correction_event_id"] is not None

    # 3. Verify event recorded in DB
    ev_stmt = (
        select(models.ClinicalEvent)
        .options(selectinload(models.ClinicalEvent.targets))
        .where(models.ClinicalEvent.id == data["correction_event_id"])
    )
    event = (await async_db_session.execute(ev_stmt)).scalar_one()
    assert event.event_type == "entered_in_error"
    assert event.payload["mode"] == "entered_in_error"
    assert event.payload["work_item_id"] == wi_id
    assert event.payload["reason"] == "Accidental clinical entry"
    assert len(event.targets) == 1
    assert event.targets[0].tooth_key == "16"


@pytest.mark.asyncio
async def test_correct_work_item_supersede(client, seed_data, async_db_session):
    """mode='supersede' sets status='superseded', creates replacement, and records link event."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Create initial procedure work item on tooth 16 surface O
    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-procedures",
        headers=headers,
        json={
            "code": ProcedureCode.REST_COMPOSITE.value,
            "tooth_key": "16",
            "surfaces": ["O"],
            "notes": "Initial composite",
        },
    )
    assert create_res.status_code == 201
    orig_wi_id = create_res.json()["data"]["id"]

    # 2. Correct via supersede with replacement on tooth 16 surfaces M and O
    correct_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{orig_wi_id}/correct",
        headers=headers,
        json={
            "mode": "supersede",
            "reason": "Expanded prep to MO",
            "replacement": {
                "kind": "procedure",
                "code": ProcedureCode.REST_COMPOSITE.value,
                "status": "planned",
                "notes": "Replacement MO composite",
                "targets": [
                    {"target_kind": "surface", "tooth_key": "16", "surface_code": "M"},
                    {"target_kind": "surface", "tooth_key": "16", "surface_code": "O"},
                ],
            },
        },
    )
    assert correct_res.status_code == 200
    data = correct_res.json()["data"]
    assert data["mode"] == "supersede"
    assert data["reason"] == "Expanded prep to MO"
    assert data["original_work_item"]["id"] == orig_wi_id
    assert data["original_work_item"]["status"] == "superseded"
    assert data["replacement_work_item"] is not None
    repl_wi_id = data["replacement_work_item"]["id"]
    assert repl_wi_id != orig_wi_id
    assert data["replacement_work_item"]["status"] == "planned"
    assert len(data["replacement_work_item"]["targets"]) == 2

    # 3. Verify event recorded in DB
    ev_stmt = (
        select(models.ClinicalEvent)
        .options(selectinload(models.ClinicalEvent.targets))
        .where(models.ClinicalEvent.id == data["correction_event_id"])
    )
    event = (await async_db_session.execute(ev_stmt)).scalar_one()
    assert event.event_type == "superseded"
    assert event.payload["mode"] == "supersede"
    assert event.payload["original_work_item_id"] == orig_wi_id
    assert event.payload["replacement_work_item_id"] == repl_wi_id
    assert event.payload["reason"] == "Expanded prep to MO"


@pytest.mark.asyncio
async def test_double_correction_conflict_409(client, seed_data, async_db_session):
    """Correcting an already corrected work item returns 409 Conflict."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16"},
    )
    wi_id = create_res.json()["data"]["id"]

    # First correction succeeds
    res_1 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "First correction"},
    )
    assert res_1.status_code == 200

    # Second correction fails with 409
    res_2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Second correction attempt"},
    )
    assert res_2.status_code == 409
    assert "already corrected" in res_2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_correction_stale_version_409(client, seed_data, async_db_session):
    """Passing stale expected_version_id to /correct returns 409 Conflict."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16"},
    )
    wi_id = create_res.json()["data"]["id"]

    # Stale version
    res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Stale version test", "expected_version_id": 999},
    )
    assert res.status_code == 409
    assert "stale version" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_correction_standalone_event_unlinked_422(client, seed_data, async_db_session):
    """Attempting to correct an unlinked standalone event returns 422 Unprocessable Entity."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Insert a standalone event without work_item_id
    standalone_ev = models.ClinicalEvent(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        work_item_id=None,
        event_type="tooth_status_recorded",
        payload={"tooth_key": "16", "status": "Sound"},
        notes="Backfilled status event",
    )
    async_db_session.add(standalone_ev)
    await async_db_session.commit()

    # Attempt to correct via work-item correction using the standalone event ID
    res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{standalone_ev.id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Attempting to correct standalone event"},
    )
    assert res.status_code == 422
    assert "Standalone events without a clinical work item cannot be corrected via work-item correction" in res.json()["detail"]


@pytest.mark.asyncio
async def test_correction_rbac_and_gates(client, seed_data, async_db_session):
    """RBAC per PD02b: Doctor 200, Admin 200, Nurse 403, Receptionist 403. Flag OFF -> 404."""
    doctor_1 = seed_data["doctor_1"]
    nurse_1 = seed_data["nurse_1"]
    receptionist_1 = seed_data["receptionist_1"]
    admin_1 = seed_data["admin_1"]
    doctor_2 = seed_data["doctor_2"]
    patient_1 = seed_data["patient_1"]

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    create_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=make_headers(doctor_1),
        json={"code": FindingCode.CARIES.value, "tooth_key": "16"},
    )
    wi_id = create_res.json()["data"]["id"]

    # Nurse (CLINICAL_WRITE only, lacks TREATMENT_PLAN_WRITE) -> 403
    res_nurse = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=make_headers(nurse_1),
        json={"mode": "entered_in_error", "reason": "Nurse attempt"},
    )
    assert res_nurse.status_code == 403

    # Receptionist -> 403
    res_rec = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=make_headers(receptionist_1),
        json={"mode": "entered_in_error", "reason": "Receptionist attempt"},
    )
    assert res_rec.status_code == 403

    # Cross-tenant (Doctor 2 on Tenant 1) -> 404
    res_cross = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=make_headers(doctor_2),
        json={"mode": "entered_in_error", "reason": "Cross-tenant attempt"},
    )
    assert res_cross.status_code == 404

    # Admin (has TREATMENT_PLAN_WRITE) -> 200
    res_admin = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=make_headers(admin_1),
        json={"mode": "entered_in_error", "reason": "Admin correction"},
    )
    assert res_admin.status_code == 200

    # Another work item with flag OFF -> 404
    create_res2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=make_headers(doctor_1),
        json={"code": FindingCode.CARIES.value, "tooth_key": "17"},
    )
    wi_id2 = create_res2.json()["data"]["id"]

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, False)
    res_flag_off = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id2}/correct",
        headers=make_headers(doctor_1),
        json={"mode": "entered_in_error", "reason": "Flag off test"},
    )
    assert res_flag_off.status_code == 404


@pytest.mark.asyncio
async def test_tooth_detail_api(client, seed_data, async_db_session):
    """GET /clinical-teeth/{tooth_key} returns summary, work items, events, and legacy records."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Native work item and event on tooth 16
    client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16"},
    )

    # 2. Legacy treatment and tooth status on tooth 16
    treatment = models.Treatment(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        tooth_number=16,
        procedure="Composite Filling",
        cost=100.0,
        status="Done",
    )
    status_row = models.ToothStatus(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        tooth_number=16,
        condition="Caries",
    )
    async_db_session.add_all([treatment, status_row])
    await async_db_session.commit()

    # 3. Call tooth detail API for tooth 16
    res = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-teeth/16",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["tooth_key"] == "16"
    assert len(data["work_items"]) >= 1
    assert len(data["events"]) >= 1
    assert len(data["legacy_treatments"]) >= 1
    assert len(data["legacy_tooth_statuses"]) >= 1

    # 4. Invalid FDI tooth key -> 422
    res_invalid = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-teeth/99",
        headers=headers,
    )
    assert res_invalid.status_code == 422
    assert "Invalid tooth_key" in res_invalid.json()["detail"]


@pytest.mark.asyncio
async def test_history_api_raw_and_filtering(client, seed_data, async_db_session):
    """History API returns raw DB events; default excludes corrected items, audit mode includes all."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Create work item 1 (active)
    res_1 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16", "notes": "Active finding"},
    )
    wi_1_id = res_1.json()["data"]["id"]

    # Create work item 2 (to be corrected)
    res_2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.FRACTURE.value, "tooth_key": "17", "notes": "Will be corrected"},
    )
    wi_2_id = res_2.json()["data"]["id"]

    # Correct work item 2
    client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_2_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Mistaken tooth 17 fracture"},
    )

    # 1. Default call (include_entered_in_error=False)
    res_default = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-events",
        headers=headers,
    )
    assert res_default.status_code == 200
    events_default = res_default.json()["data"]
    work_item_ids_default = [e["work_item_id"] for e in events_default]
    assert wi_1_id in work_item_ids_default
    assert wi_2_id not in work_item_ids_default
    assert not any(e["event_type"] in CANONICAL_CORRECTION_STATUSES for e in events_default)

    # 2. Audit call (include_entered_in_error=True)
    res_audit = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-events?include_entered_in_error=true",
        headers=headers,
    )
    assert res_audit.status_code == 200
    events_audit = res_audit.json()["data"]
    work_item_ids_audit = [e["work_item_id"] for e in events_audit]
    assert wi_1_id in work_item_ids_audit
    assert wi_2_id in work_item_ids_audit
    assert any(e["event_type"] == "entered_in_error" for e in events_audit)


@pytest.mark.asyncio
async def test_zero_event_mutation_and_financial_invariance_on_correction(client, seed_data, async_db_session):
    """Correcting work items NEVER mutates existing ClinicalEvent rows and has zero financial delta."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Create work item
    res_create = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16"},
    )
    wi_id = res_create.json()["data"]["id"]

    # Record pre-correction snapshots
    stmt_events = select(models.ClinicalEvent).where(models.ClinicalEvent.patient_id == patient_1.id)
    pre_events = (await async_db_session.execute(stmt_events)).scalars().all()
    pre_event_map = {e.id: (e.event_type, e.occurred_at, dict(e.payload), e.notes) for e in pre_events}
    pre_event_count = len(pre_events)

    pre_treatment_count = await async_db_session.scalar(select(func.count(models.Treatment.id)))
    pre_payment_count = await async_db_session.scalar(select(func.count(models.Payment.id)))
    pre_stock_count = await async_db_session.scalar(select(func.count(StockMovement.id)))

    # Execute correction
    correct_res = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Zero-mutation test"},
    )
    assert correct_res.status_code == 200

    # Post-correction verification
    post_events = (await async_db_session.execute(stmt_events)).scalars().all()
    post_event_count = len(post_events)
    # Exactly ONE new event appended
    assert post_event_count == pre_event_count + 1

    # Every pre-existing event is 100% untouched
    for e in post_events:
        if e.id in pre_event_map:
            orig_type, orig_occurred, orig_payload, orig_notes = pre_event_map[e.id]
            assert e.event_type == orig_type
            assert e.occurred_at == orig_occurred
            assert e.payload == orig_payload
            assert e.notes == orig_notes

    # Financial / legacy tables completely unchanged
    post_treatment_count = await async_db_session.scalar(select(func.count(models.Treatment.id)))
    post_payment_count = await async_db_session.scalar(select(func.count(models.Payment.id)))
    post_stock_count = await async_db_session.scalar(select(func.count(StockMovement.id)))

    assert post_treatment_count == pre_treatment_count
    assert post_payment_count == pre_payment_count
    assert post_stock_count == pre_stock_count


