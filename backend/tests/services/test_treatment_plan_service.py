"""
Unit and Integration Tests for Clinical Treatment Plans (Slice G9a).

Tests required:
- Tenant isolation
- Patient scoping (404 on mismatch / non-existent)
- Flag-off -> 404 on create and list
- RBAC permissions (create requires doctor/admin, read requires clinical read)
- Default phase created (phase_order 0, name "Phase 1", status "draft")
- Creator attribution (created_by_user_id)
- Empty list returns []
- Status strictly 'draft'
"""

import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, func

from backend import models, schemas
from backend.services.treatment_plan_service import TreatmentPlanService
from backend.routers.treatment_plans import (
    create_patient_clinical_plan,
    list_patient_clinical_plans,
)
from backend.services.feature_service import FeatureFlagService
from backend.auth import create_access_token


@pytest.fixture
async def seed_data(async_db_session):
    """Seed two tenants with users and patients for isolation testing."""
    # Tenant 1
    tenant_1 = models.Tenant(name="Clinic Alpha", domain="alpha.example.com", is_active=True)
    tenant_2 = models.Tenant(name="Clinic Beta", domain="beta.example.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    # Users in Tenant 1
    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="doc_alpha",
        email="doc1@alpha.com",
        hashed_password="test-hashed-password",
        role="doctor",
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
    receptionist_1 = models.User(
        tenant_id=tenant_1.id,
        username="recep_alpha",
        email="recep1@alpha.com",
        hashed_password="test-hashed-password",
        role="receptionist",
        is_active=True,
    )

    # Users in Tenant 2
    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="doc_beta",
        email="doc2@beta.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )


    async_db_session.add_all([doctor_1, admin_1, receptionist_1, doctor_2])
    await async_db_session.flush()

    # Patients
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
        "admin_1": admin_1,
        "receptionist_1": receptionist_1,
        "doctor_2": doctor_2,
        "patient_1": patient_1,
        "patient_2": patient_2,
    }


@pytest.mark.asyncio
async def test_flag_off_returns_404(async_db_session, seed_data, monkeypatch):
    """When the feature flag is off, both create and list endpoints return 404."""
    monkeypatch.delenv("CLINICAL_TREATMENT_PLANS_ENABLED", raising=False)

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    # Flag is disabled by default
    assert await service.is_enabled() is False

    # Create raises 404
    payload = schemas.ClinicalTreatmentPlanCreate(title="Test Plan", notes="Notes")
    with pytest.raises(HTTPException) as exc_create:
        await service.create_plan(patient_1.id, payload)
    assert exc_create.value.status_code == 404
    assert "disabled" in exc_create.value.detail.lower()

    # List raises 404
    with pytest.raises(HTTPException) as exc_list:
        await service.list_plans(patient_1.id)
    assert exc_list.value.status_code == 404
    assert "disabled" in exc_list.value.detail.lower()


@pytest.mark.asyncio
async def test_empty_list_returns_empty_array(async_db_session, seed_data, monkeypatch):
    """When enabled and patient has no plans, list_plans returns []."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    assert await service.is_enabled() is True
    plans = await service.list_plans(patient_1.id)
    assert plans == []


@pytest.mark.asyncio
async def test_create_plan_creates_default_phase_and_creator_attribution(
    async_db_session, seed_data, monkeypatch
):
    """Creating a plan creates 1 default phase (phase_order 0, 'Phase 1', draft) and attributes creator."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    payload = schemas.ClinicalTreatmentPlanCreate(
        title="Comprehensive Rehabilitation",
        notes="Initial consultation recommendations",
    )
    plan = await service.create_plan(patient_1.id, payload)

    # Assert plan properties
    assert plan.id is not None
    assert plan.tenant_id == doctor_1.tenant_id
    assert plan.patient_id == patient_1.id
    assert plan.title == "Comprehensive Rehabilitation"
    assert plan.status == "draft"
    assert plan.notes == "Initial consultation recommendations"
    assert plan.created_by_user_id == doctor_1.id  # Creator attribution
    assert plan.version_id == 1

    # Assert default phase properties (Decision 2)
    assert len(plan.phases) == 1
    phase = plan.phases[0]
    assert phase.id is not None
    assert phase.plan_id == plan.id
    assert phase.tenant_id == doctor_1.tenant_id
    assert phase.phase_order == 0  # phase_order 0
    assert phase.name == "Phase 1"  # "Phase 1"
    assert phase.status == "draft"  # 'draft'
    assert phase.notes is None

    # List plans returns this plan
    listed_plans = await service.list_plans(patient_1.id)
    assert len(listed_plans) == 1
    assert listed_plans[0].id == plan.id
    assert len(listed_plans[0].phases) == 1


@pytest.mark.asyncio
async def test_tenant_isolation(async_db_session, seed_data, monkeypatch):
    """Tenant A plans cannot be accessed or listed by Tenant B, cross-tenant returns 404."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    doctor_2 = seed_data["doctor_2"]

    service_1 = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    service_2 = TreatmentPlanService(async_db_session, doctor_2.tenant_id, doctor_2)

    # Create plan in Tenant 1
    plan_1 = await service_1.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Plan T1")
    )
    assert plan_1.tenant_id == doctor_1.tenant_id

    # Doctor 2 (Tenant 2) tries to list plans for Patient 1 -> 404
    with pytest.raises(HTTPException) as exc_cross_list:
        await service_2.list_plans(patient_1.id)
    assert exc_cross_list.value.status_code == 404

    # Doctor 2 (Tenant 2) tries to create plan for Patient 1 -> 404
    with pytest.raises(HTTPException) as exc_cross_create:
        await service_2.create_plan(
            patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Plan T2 Attack")
        )
    assert exc_cross_create.value.status_code == 404

    # Direct query for Tenant 2 confirms no cross-tenant leakage
    stmt = select(models.ClinicalTreatmentPlan).where(
        models.ClinicalTreatmentPlan.tenant_id == doctor_2.tenant_id
    )
    t2_plans = (await async_db_session.execute(stmt)).scalars().all()
    assert len(t2_plans) == 0


@pytest.mark.asyncio
async def test_patient_scoping_nonexistent_returns_404(
    async_db_session, seed_data, monkeypatch
):
    """Non-existent patient ID returns 404 for both create and list."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)
    non_existent_id = 999999

    with pytest.raises(HTTPException) as exc_create:
        await service.create_plan(
            non_existent_id, schemas.ClinicalTreatmentPlanCreate(title="Test")
        )
    assert exc_create.value.status_code == 404

    with pytest.raises(HTTPException) as exc_list:
        await service.list_plans(non_existent_id)
    assert exc_list.value.status_code == 404


@pytest.mark.asyncio
async def test_title_validation(async_db_session, seed_data, monkeypatch):
    """Whitespace or empty title cannot be created."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    # Empty string is rejected by Pydantic schema Field(min_length=1)
    with pytest.raises(Exception):
        schemas.ClinicalTreatmentPlanCreate(title="")

    # All whitespace is rejected by service
    payload = schemas.ClinicalTreatmentPlanCreate(title="   ")
    with pytest.raises(HTTPException) as exc:
        await service.create_plan(patient_1.id, payload)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_per_tenant_feature_flag_override(async_db_session, seed_data, monkeypatch):
    """Feature flag works via TenantFeature override without env var."""
    monkeypatch.delenv("CLINICAL_TREATMENT_PLANS_ENABLED", raising=False)

    tenant_1 = seed_data["tenant_1"]
    tenant_2 = seed_data["tenant_2"]
    doctor_1 = seed_data["doctor_1"]
    doctor_2 = seed_data["doctor_2"]
    patient_1 = seed_data["patient_1"]
    patient_2 = seed_data["patient_2"]

    # Enable flag for tenant 1 only in DB
    tf = models.TenantFeature(
        tenant_id=tenant_1.id,
        feature_key="clinical_treatment_plans",
        is_enabled=True,
    )
    async_db_session.add(tf)
    await async_db_session.commit()

    service_1 = TreatmentPlanService(async_db_session, tenant_1.id, doctor_1)
    service_2 = TreatmentPlanService(async_db_session, tenant_2.id, doctor_2)

    # Tenant 1 is enabled
    assert await service_1.is_enabled() is True
    plans_1 = await service_1.list_plans(patient_1.id)
    assert plans_1 == []

    # Tenant 2 is still disabled (returns 404)
    assert await service_2.is_enabled() is False
    with pytest.raises(HTTPException) as exc:
        await service_2.list_plans(patient_2.id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_router_http_endpoints(client, seed_data, monkeypatch):
    """Test router endpoints with TestClient covering RBAC, flag-off, and creation."""
    patient_1 = seed_data["patient_1"]
    doctor_1 = seed_data["doctor_1"]
    receptionist_1 = seed_data["receptionist_1"]

    doc_token = create_access_token(
        data={"sub": doctor_1.username, "tenant_id": doctor_1.tenant_id, "role": "doctor"}
    )
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    recep_token = create_access_token(
        data={"sub": receptionist_1.username, "tenant_id": receptionist_1.tenant_id, "role": "receptionist"}
    )
    recep_headers = {"Authorization": f"Bearer {recep_token}"}

    # 1. Flag off -> 404
    monkeypatch.delenv("CLINICAL_TREATMENT_PLANS_ENABLED", raising=False)
    res_off_get = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
    )
    assert res_off_get.status_code == 404

    res_off_post = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
        json={"title": "Test Plan"},
    )
    assert res_off_post.status_code == 404

    # 2. Turn flag ON
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    # 3. RBAC: Receptionist has CLINICAL_READ so can GET empty list
    res_recep_get = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=recep_headers,
    )
    assert res_recep_get.status_code == 200
    assert res_recep_get.json()["data"] == []

    # RBAC: Receptionist lacks TREATMENT_PLAN_WRITE, so POST returns 403
    res_recep_post = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=recep_headers,
        json={"title": "Unauthorized Plan"},
    )
    assert res_recep_post.status_code == 403

    # 4. Doctor can create plan
    res_doc_post = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
        json={"title": "Doctor Rehabilitation Plan", "notes": "Careful monitoring"},
    )
    assert res_doc_post.status_code == 200
    body = res_doc_post.json()
    assert body["success"] is True
    plan_data = body["data"]
    assert plan_data["title"] == "Doctor Rehabilitation Plan"
    assert plan_data["notes"] == "Careful monitoring"
    assert plan_data["status"] == "draft"
    assert plan_data["created_by_user_id"] == doctor_1.id
    assert len(plan_data["phases"]) == 1
    assert plan_data["phases"][0]["phase_order"] == 0
    assert plan_data["phases"][0]["name"] == "Phase 1"
    assert plan_data["phases"][0]["status"] == "draft"

    # 5. Doctor can list plans
    res_doc_get = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
    )
    assert res_doc_get.status_code == 200
    plans_list = res_doc_get.json()["data"]
    assert len(plans_list) == 1
    assert plans_list[0]["id"] == plan_data["id"]

    # 6. GET /api/v1/settings/features includes clinical_treatment_plans
    res_feat = client.get("/api/v1/settings/features", headers=doc_headers)
    assert res_feat.status_code == 200
    features = res_feat.json()["data"]["features"]
    assert "clinical_treatment_plans" in features



@pytest.mark.asyncio
async def test_add_phase_sequential_ordering_and_validation(
    async_db_session, seed_data, monkeypatch
):
    """Adding phases sequentially assigns phase_order 1, 2... and validates name."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    plan = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Phase Test Plan")
    )
    assert len(plan.phases) == 1
    assert plan.phases[0].phase_order == 0  # Default phase

    # Add Phase 2
    phase_2 = await service.add_phase(
        patient_1.id,
        plan.id,
        schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 2: Surgical", notes="Extractions"),
    )
    assert phase_2.id is not None
    assert phase_2.plan_id == plan.id
    assert phase_2.phase_order == 1
    assert phase_2.name == "Phase 2: Surgical"
    assert phase_2.status == "draft"
    assert phase_2.notes == "Extractions"

    # Add Phase 3
    phase_3 = await service.add_phase(
        patient_1.id,
        plan.id,
        schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 3: Prosthetics"),
    )
    assert phase_3.phase_order == 2
    assert phase_3.name == "Phase 3: Prosthetics"

    # Blank / whitespace name validation -> 422
    with pytest.raises(HTTPException) as exc_blank:
        await service.add_phase(
            patient_1.id,
            plan.id,
            schemas.ClinicalTreatmentPlanPhaseCreate(name="   "),
        )
    assert exc_blank.value.status_code == 422


@pytest.mark.asyncio
async def test_candidate_work_items_filters_cancelled(
    async_db_session, seed_data, monkeypatch
):
    """Candidate work items returns non-cancelled items and respects tenant/patient scoping."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    plan = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Candidates Plan")
    )

    # Seed 3 clinical work items for patient 1:
    # 1. proposed procedure
    wi_1 = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D2391",
        status="proposed",
        notes="Composite 1-surface",
    )
    # 2. planned procedure
    wi_2 = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D3330",
        status="planned",
        notes="Molar RCT",
    )
    # 3. cancelled procedure
    wi_cancelled = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D7140",
        status="cancelled",
        notes="Extraction cancelled",
    )
    async_db_session.add_all([wi_1, wi_2, wi_cancelled])
    await async_db_session.commit()

    candidates = await service.get_candidate_work_items(patient_1.id, plan.id)
    candidate_ids = [c.id for c in candidates]
    assert wi_1.id in candidate_ids
    assert wi_2.id in candidate_ids
    assert wi_cancelled.id not in candidate_ids  # Cancelled excluded (Amendment A)


@pytest.mark.asyncio
async def test_add_work_item_to_phase_and_unlink(
    async_db_session, seed_data, monkeypatch
):
    """Adding work item links to phase; unlinking removes item and leaves work_item intact."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    plan = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Link Test Plan")
    )
    phase_0 = plan.phases[0]

    wi = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D2740",
        status="proposed",
        notes="Crown porcelain",
    )
    async_db_session.add(wi)
    await async_db_session.commit()

    # Link item to phase
    item = await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_0.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id, notes="Phase notes"),
    )
    assert item.id is not None
    assert item.phase_id == phase_0.id
    assert item.work_item_id == wi.id
    assert item.item_order == 0
    assert item.status == "planned"
    assert item.notes == "Phase notes"
    assert item.work_item.code == "D2740"

    # Verify listing plan includes phase item
    plans = await service.list_plans(patient_1.id)
    target_plan = next(p for p in plans if p.id == plan.id)
    assert len(target_plan.phases[0].items) == 1
    assert target_plan.phases[0].items[0].work_item_id == wi.id

    # Unlink item from phase (Amendment 5)
    await service.remove_work_item_from_phase(patient_1.id, plan.id, phase_0.id, item.id)

    # Item is deleted
    plans_after = await service.list_plans(patient_1.id)
    target_plan_after = next(p for p in plans_after if p.id == plan.id)
    assert len(target_plan_after.phases[0].items) == 0

    # Underlying work item is completely untouched
    stmt_wi_check = select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi.id)
    wi_reloaded = (await async_db_session.execute(stmt_wi_check)).scalar_one()
    assert wi_reloaded.code == "D2740"
    assert wi_reloaded.status == "proposed"


@pytest.mark.asyncio
async def test_multi_plan_sharing_g9_m05_amendment_b(
    async_db_session, seed_data, monkeypatch
):
    """The SAME work item MAY be attached to phases of two different plans without duplication."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    # 1. Create two alternative plans
    plan_conservative = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Option A: Conservative")
    )
    plan_surgical = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Option B: Surgical")
    )

    # 2. Create single work item
    wi_shared = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D1110",
        status="proposed",
        notes="Prophylaxis",
    )
    async_db_session.add(wi_shared)
    await async_db_session.commit()

    # Initial counts
    stmt_wi_count = select(func.count(models.ClinicalWorkItem.id)).where(
        models.ClinicalWorkItem.tenant_id == doctor_1.tenant_id
    )
    stmt_ev_count = select(func.count(models.ClinicalEvent.id)).where(
        models.ClinicalEvent.tenant_id == doctor_1.tenant_id
    )
    wi_count_before = (await async_db_session.execute(stmt_wi_count)).scalar()
    ev_count_before = (await async_db_session.execute(stmt_ev_count)).scalar()

    # 3. Attach wi_shared to Plan Conservative (Phase 0)
    item_a = await service.add_work_item_to_phase(
        patient_1.id,
        plan_conservative.id,
        plan_conservative.phases[0].id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_shared.id),
    )
    # 4. Attach SAME wi_shared to Plan Surgical (Phase 0)
    item_b = await service.add_work_item_to_phase(
        patient_1.id,
        plan_surgical.id,
        plan_surgical.phases[0].id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_shared.id),
    )

    # Assert 2 distinct plan item rows created
    assert item_a.id != item_b.id
    assert item_a.phase_id == plan_conservative.phases[0].id
    assert item_b.phase_id == plan_surgical.phases[0].id
    assert item_a.work_item_id == wi_shared.id
    assert item_b.work_item_id == wi_shared.id

    # ZERO new work items or events created (Amendment B)
    wi_count_after = (await async_db_session.execute(stmt_wi_count)).scalar()
    ev_count_after = (await async_db_session.execute(stmt_ev_count)).scalar()
    assert wi_count_after == wi_count_before
    assert ev_count_after == ev_count_before


@pytest.mark.asyncio
async def test_duplicate_item_in_same_phase_returns_409(
    async_db_session, seed_data, monkeypatch
):
    """Attaching the same work item twice to the SAME phase returns 409 (Amendment B)."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    plan = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Duplicate Test Plan")
    )
    phase_0 = plan.phases[0]

    wi = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D0120",
        status="proposed",
    )
    async_db_session.add(wi)
    await async_db_session.commit()

    # First attach succeeds
    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_0.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id),
    )

    # Second attach to same phase raises 409
    with pytest.raises(HTTPException) as exc_dup:
        await service.add_work_item_to_phase(
            patient_1.id,
            plan.id,
            phase_0.id,
            schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id),
        )
    assert exc_dup.value.status_code == 409
    assert "already attached" in exc_dup.value.detail.lower()


@pytest.mark.asyncio
async def test_cancelled_and_cross_patient_work_item_rejected(
    async_db_session, seed_data, monkeypatch
):
    """Cancelled work items return 422; cross-patient / cross-tenant items return 404."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    patient_2 = seed_data["patient_2"]  # Tenant 2
    service = TreatmentPlanService(async_db_session, doctor_1.tenant_id, doctor_1)

    plan = await service.create_plan(
        patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Validation Plan")
    )
    phase_0 = plan.phases[0]

    # Cancelled item for patient 1
    wi_cancelled = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D0150",
        status="cancelled",
    )
    # Item belonging to patient 2 (different tenant/patient)
    wi_p2 = models.ClinicalWorkItem(
        tenant_id=seed_data["tenant_2"].id,
        patient_id=patient_2.id,
        kind="procedure",
        code="D0150",
        status="proposed",
    )
    async_db_session.add_all([wi_cancelled, wi_p2])
    await async_db_session.commit()

    # Cancelled -> 422
    with pytest.raises(HTTPException) as exc_canc:
        await service.add_work_item_to_phase(
            patient_1.id,
            plan.id,
            phase_0.id,
            schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_cancelled.id),
        )
    assert exc_canc.value.status_code == 422

    # Cross-tenant / cross-patient -> 404
    with pytest.raises(HTTPException) as exc_cross:
        await service.add_work_item_to_phase(
            patient_1.id,
            plan.id,
            phase_0.id,
            schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_p2.id),
        )
    assert exc_cross.value.status_code == 404


@pytest.mark.asyncio
async def test_http_endpoints_g9b_phases_and_items(client, seed_data, async_db_session, monkeypatch):
    """Test full HTTP API flows for Slice G9b: candidates, add phase, add item, remove item."""
    patient_1 = seed_data["patient_1"]
    doctor_1 = seed_data["doctor_1"]
    receptionist_1 = seed_data["receptionist_1"]

    doc_token = create_access_token(
        data={"sub": doctor_1.username, "tenant_id": doctor_1.tenant_id, "role": "doctor"}
    )
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    recep_token = create_access_token(
        data={"sub": receptionist_1.username, "tenant_id": receptionist_1.tenant_id, "role": "receptionist"}
    )
    recep_headers = {"Authorization": f"Bearer {recep_token}"}

    # Enable flag
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")

    # 1. Create plan via HTTP
    res_plan = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
        json={"title": "HTTP Full Plan"},
    )
    assert res_plan.status_code == 200
    plan_id = res_plan.json()["data"]["id"]

    # 2. Add Phase 2 via HTTP
    res_phase = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases",
        headers=doc_headers,
        json={"name": "Phase 2: Restorative", "notes": "Crowns and inlays"},
    )
    assert res_phase.status_code == 200
    phase_2_data = res_phase.json()["data"]
    assert phase_2_data["name"] == "Phase 2: Restorative"
    assert phase_2_data["phase_order"] == 1
    phase_2_id = phase_2_data["id"]

    # Receptionist cannot add phase (403)
    res_recep_phase = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases",
        headers=recep_headers,
        json={"name": "Phase 3"},
    )
    assert res_recep_phase.status_code == 403

    # 3. Create candidate work item directly in DB for testing
    wi = models.ClinicalWorkItem(
        tenant_id=doctor_1.tenant_id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D2740",
        status="planned",
        notes="Crown tooth 16",
    )
    async_db_session.add(wi)
    await async_db_session.commit()
    wi_id = wi.id

    # 4. Candidates endpoint works with CLINICAL_READ (receptionist & doctor)
    res_cand_recep = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/candidate-work-items",
        headers=recep_headers,
    )
    assert res_cand_recep.status_code == 200
    cands = res_cand_recep.json()["data"]
    assert any(c["id"] == wi_id for c in cands)

    # 5. Add work item to Phase 2
    res_item = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_2_id}/items",
        headers=doc_headers,
        json={"work_item_id": wi_id, "notes": "Specific lab instructions"},
    )
    assert res_item.status_code == 200
    item_data = res_item.json()["data"]
    assert item_data["work_item_id"] == wi_id
    assert item_data["phase_id"] == phase_2_id
    item_id = item_data["id"]

    # Receptionist cannot add item (403)
    res_recep_item = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_2_id}/items",
        headers=recep_headers,
        json={"work_item_id": wi_id},
    )
    assert res_recep_item.status_code == 403

    # Duplicate add returns 409
    res_dup = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_2_id}/items",
        headers=doc_headers,
        json={"work_item_id": wi_id},
    )
    assert res_dup.status_code == 409

    # 6. List plans returns updated tree
    res_list = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
    )
    assert res_list.status_code == 200
    plans = res_list.json()["data"]
    target_plan = next(p for p in plans if p["id"] == plan_id)
    assert len(target_plan["phases"]) == 2
    assert len(target_plan["phases"][1]["items"]) == 1
    assert target_plan["phases"][1]["items"][0]["id"] == item_id

    # 7. Remove item from Phase 2
    res_del = client.delete(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_2_id}/items/{item_id}",
        headers=doc_headers,
    )
    assert res_del.status_code == 200

    # Verify item gone from phase
    res_list_after = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
    )
    target_plan_after = next(p for p in res_list_after.json()["data"] if p["id"] == plan_id)
    assert len(target_plan_after["phases"][1]["items"]) == 0

    # 8. Flag off returns 404 on all endpoints
    monkeypatch.delenv("CLINICAL_TREATMENT_PLANS_ENABLED", raising=False)
    assert client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/candidate-work-items",
        headers=doc_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases",
        headers=doc_headers,
        json={"name": "Flag Off Phase"},
    ).status_code == 404
    assert client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_2_id}/items",
        headers=doc_headers,
        json={"work_item_id": wi_id},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_2_id}/items/{item_id}",
        headers=doc_headers,
    ).status_code == 404
