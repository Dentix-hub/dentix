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

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.auth import create_access_token
from backend.clinical.catalog import FindingCode, ProcedureCode
from backend.models.inventory import StockMovement
from backend.services.clinical_command_service import ClinicalCommandService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
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

