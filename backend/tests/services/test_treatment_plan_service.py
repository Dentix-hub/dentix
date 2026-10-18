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
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

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


# ==============================================================================
# SLICE G9c TESTS: Lifecycle, Concurrency, Hardening, and Guardrails
# ==============================================================================

@pytest.mark.asyncio
async def test_plan_transition_valid_lifecycle_and_audit(seed_data, async_db_session, monkeypatch):
    """
    Decision 1 & 7: Test valid transitions: draft -> proposed -> accepted -> completed.
    Verify audit log records who, when, old status, and new status for each step.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]

    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)
    plan = await service.create_plan(
        patient_1.id,
        schemas.ClinicalTreatmentPlanCreate(title="Lifecycle Plan"),
    )
    assert plan.status == "draft"

    # 1. draft -> proposed
    p1 = await service.transition_plan(patient_1.id, plan.id, "proposed")
    assert p1.status == "proposed"

    # 2. proposed -> accepted
    p2 = await service.transition_plan(patient_1.id, plan.id, "accepted")
    assert p2.status == "accepted"

    # 3. accepted -> completed
    p3 = await service.transition_plan(patient_1.id, plan.id, "completed")
    assert p3.status == "completed"

    # Verify AuditLog entries (Decision 7)
    stmt_audit = (
        select(models.AuditLog)
        .where(
            models.AuditLog.tenant_id == tenant_1.id,
            models.AuditLog.entity_type == "clinical_treatment_plan",
            models.AuditLog.entity_id == plan.id,
        )
        .order_by(models.AuditLog.id.asc())
    )
    audit_logs = (await async_db_session.execute(stmt_audit)).scalars().all()
    assert len(audit_logs) == 3

    assert audit_logs[0].action == "transition_proposed"
    assert '"draft"' in audit_logs[0].old_value
    assert '"proposed"' in audit_logs[0].new_value
    assert audit_logs[0].performed_by_id == doctor_1.id

    assert audit_logs[1].action == "transition_accepted"
    assert '"proposed"' in audit_logs[1].old_value
    assert '"accepted"' in audit_logs[1].new_value

    assert audit_logs[2].action == "transition_completed"
    assert '"accepted"' in audit_logs[2].old_value
    assert '"completed"' in audit_logs[2].new_value


@pytest.mark.asyncio
async def test_plan_transition_cancellation_from_any_active_state(seed_data, async_db_session, monkeypatch):
    """
    Decision 1: Test cancellation allowed from any non-completed state:
    - draft -> cancelled
    - proposed -> cancelled
    - accepted -> cancelled
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    # 1. From draft -> cancelled
    plan1 = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Cancel from Draft"))
    c1 = await service.transition_plan(patient_1.id, plan1.id, "cancelled")
    assert c1.status == "cancelled"

    # 2. From proposed -> cancelled
    plan2 = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Cancel from Proposed"))
    await service.transition_plan(patient_1.id, plan2.id, "proposed")
    c2 = await service.transition_plan(patient_1.id, plan2.id, "cancelled")
    assert c2.status == "cancelled"

    # 3. From accepted -> cancelled
    plan3 = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Cancel from Accepted"))
    await service.transition_plan(patient_1.id, plan3.id, "proposed")
    await service.transition_plan(patient_1.id, plan3.id, "accepted")
    c3 = await service.transition_plan(patient_1.id, plan3.id, "cancelled")
    assert c3.status == "cancelled"


@pytest.mark.asyncio
async def test_plan_transition_invalid_transitions_return_409(seed_data, async_db_session, monkeypatch):
    """
    Decision 1: Invalid transitions raise HTTP 409 Conflict:
    - Skipping states (draft -> accepted, draft -> completed, proposed -> completed)
    - Moving backwards (proposed -> draft, accepted -> draft, accepted -> proposed)
    - Moving from terminal states (completed -> anything, cancelled -> anything)
    - Same status or unknown status
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Invalid Transition Test"))

    # Draft: invalid transitions
    for invalid in ("accepted", "completed", "draft", "unknown_status"):
        with pytest.raises(HTTPException) as exc:
            await service.transition_plan(patient_1.id, plan.id, invalid)
        assert exc.value.status_code == 409

    # Advance to proposed
    await service.transition_plan(patient_1.id, plan.id, "proposed")
    for invalid in ("draft", "completed", "proposed", "invalid_xyz"):
        with pytest.raises(HTTPException) as exc:
            await service.transition_plan(patient_1.id, plan.id, invalid)
        assert exc.value.status_code == 409

    # Advance to accepted
    await service.transition_plan(patient_1.id, plan.id, "accepted")
    for invalid in ("draft", "proposed", "accepted"):
        with pytest.raises(HTTPException) as exc:
            await service.transition_plan(patient_1.id, plan.id, invalid)
        assert exc.value.status_code == 409

    # Advance to completed (terminal)
    await service.transition_plan(patient_1.id, plan.id, "completed")
    for invalid in ("draft", "proposed", "accepted", "completed", "cancelled"):
        with pytest.raises(HTTPException) as exc:
            await service.transition_plan(patient_1.id, plan.id, invalid)
        assert exc.value.status_code == 409

    # Cancelled (terminal)
    plan_c = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Cancelled Plan"))
    await service.transition_plan(patient_1.id, plan_c.id, "cancelled")
    for invalid in ("draft", "proposed", "accepted", "completed", "cancelled"):
        with pytest.raises(HTTPException) as exc:
            await service.transition_plan(patient_1.id, plan_c.id, invalid)
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_plan_transition_plan_level_only_count_assertions(seed_data, async_db_session, monkeypatch):
    """
    Decision 2: Transitions are plan-level ONLY.
    They must NOT change work item status, create treatments, invoices, payments, inventory movements, or ClinicalEvents.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    # 1. Setup plan with item
    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Plan-level Isolation Test"))
    phase = plan.phases[0]

    wi = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D2391",
        status="planned",
        created_by_user_id=doctor_1.id,
    )
    async_db_session.add(wi)
    await async_db_session.commit()

    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id),
    )

    # Record baseline counts across related domains
    count_wi_before = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar()
    count_events_before = (await async_db_session.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
    count_treatments_before = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar()
    count_stock_mov_before = (await async_db_session.execute(select(func.count(models.StockMovement.id)))).scalar()
    count_payments_before = (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar()

    # 2. Transition plan: draft -> proposed -> accepted
    await service.transition_plan(patient_1.id, plan.id, "proposed")
    await service.transition_plan(patient_1.id, plan.id, "accepted")

    # 3. Assert counts are completely identical (zero side effects)
    count_wi_after = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar()
    count_events_after = (await async_db_session.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
    count_treatments_after = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar()
    count_stock_mov_after = (await async_db_session.execute(select(func.count(models.StockMovement.id)))).scalar()
    count_payments_after = (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar()

    assert count_wi_after == count_wi_before
    assert count_events_after == count_events_before
    assert count_treatments_after == count_treatments_before
    assert count_stock_mov_after == count_stock_mov_before
    assert count_payments_after == count_payments_before

    # 4. Assert underlying work item status was NOT modified
    wi_reloaded = (
        await async_db_session.execute(select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi.id))
    ).scalar_one()
    assert wi_reloaded.status == "planned"


@pytest.mark.asyncio
async def test_plan_alternatives_preserved_on_accept(seed_data, async_db_session, monkeypatch):
    """
    Decision 3: Alternatives: a patient may have several plans.
    Accepting plan A does NOT auto-cancel plan B.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    plan_a = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Plan A (Implants)"))
    plan_b = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Plan B (Bridge)"))

    assert plan_a.status == "draft"
    assert plan_b.status == "draft"

    # Propose and accept Plan A
    await service.transition_plan(patient_1.id, plan_a.id, "proposed")
    await service.transition_plan(patient_1.id, plan_a.id, "accepted")

    # Reload Plan B and verify it remains in draft
    reloaded_b = await service._get_plan_and_verify(patient_1.id, plan_b.id)
    assert reloaded_b.status == "draft"


@pytest.mark.asyncio
async def test_plan_mutations_blocked_in_non_draft_proposed_statuses(seed_data, async_db_session, monkeypatch):
    """
    Decision 4: Phases and items can be added or removed ONLY while the plan is draft or proposed.
    In accepted, completed, or cancelled plans, add_phase, add_work_item_to_phase, and remove_work_item_from_phase return 409.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    # Setup plan with phase and item in draft
    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Mutation Lockdown Plan"))
    phase = plan.phases[0]

    wi = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D1110",
        status="planned",
    )
    async_db_session.add(wi)
    await async_db_session.commit()

    item = await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id),
    )

    # 1. Propose plan -> mutations still allowed in proposed
    await service.transition_plan(patient_1.id, plan.id, "proposed")
    phase2 = await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 2"))
    assert phase2.name == "Phase 2"

    # 2. Accept plan -> mutations blocked (409)
    await service.transition_plan(patient_1.id, plan.id, "accepted")

    with pytest.raises(HTTPException) as exc_add_phase:
        await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 3"))
    assert exc_add_phase.value.status_code == 409

    with pytest.raises(HTTPException) as exc_add_item:
        await service.add_work_item_to_phase(
            patient_1.id,
            plan.id,
            phase.id,
            schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id),
        )
    assert exc_add_item.value.status_code == 409

    with pytest.raises(HTTPException) as exc_del_item:
        await service.remove_work_item_from_phase(patient_1.id, plan.id, phase.id, item.id)
    assert exc_del_item.value.status_code == 409

    # 3. Complete plan -> mutations blocked (409)
    await service.transition_plan(patient_1.id, plan.id, "completed")
    with pytest.raises(HTTPException) as exc_comp_phase:
        await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 4"))
    assert exc_comp_phase.value.status_code == 409


@pytest.mark.asyncio
async def test_plan_transition_stale_data_concurrency_409(seed_data, async_db_session, monkeypatch):
    """
    Decision 6: Plan uses version_id; map SQLAlchemy StaleDataError to HTTP 409 Conflict.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Concurrency Plan"))
    assert plan.version_id == 1

    orig_commit = async_db_session.commit

    async def commit_with_stale_data():
        raise StaleDataError(models.ClinicalTreatmentPlan, "Optimistic locking conflict")

    async_db_session.commit = commit_with_stale_data
    try:
        with pytest.raises(HTTPException) as exc:
            await service.transition_plan(patient_1.id, plan.id, "proposed")
        assert exc.value.status_code == 409
        assert "concurrently" in exc.value.detail.lower()
    finally:
        async_db_session.commit = orig_commit


@pytest.mark.asyncio
async def test_finding_work_item_rejected_422_and_excluded_from_candidates(seed_data, async_db_session, monkeypatch):
    """
    Fix A: Candidate list and add_work_item_to_phase: only kind == 'procedure' allowed;
    a finding returns 422 on attach and is excluded from the candidate list.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Findings Exclusion Plan"))
    phase = plan.phases[0]

    # Create one procedure and one finding
    proc = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D2140",
        status="planned",
    )
    finding = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="finding",
        code="CARIES",
        status="planned",
    )
    async_db_session.add_all([proc, finding])
    await async_db_session.commit()

    # 1. Candidate list includes procedure, but excludes finding
    candidates = await service.get_candidate_work_items(patient_1.id, plan.id)
    candidate_ids = [c.id for c in candidates]
    assert proc.id in candidate_ids
    assert finding.id not in candidate_ids

    # 2. Attempting to add finding to phase raises HTTP 422
    with pytest.raises(HTTPException) as exc:
        await service.add_work_item_to_phase(
            patient_1.id,
            plan.id,
            phase.id,
            schemas.ClinicalTreatmentPlanItemCreate(work_item_id=finding.id),
        )
    assert exc.value.status_code == 422
    assert "finding" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_add_phase_integrity_error_retry_and_missing_greenlet_safety(seed_data, async_db_session, monkeypatch):
    """
    Fix B: Verify add_phase retry path handles rollback cleanly without MissingGreenlet/expired-attribute errors,
    and returns 409 on persistent conflict.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Phase Retry Plan"))
    patient_1_id = patient_1.id
    plan_id = plan.id

    orig_commit = async_db_session.commit
    fail_once_counter = 0

    async def commit_fail_once():
        nonlocal fail_once_counter
        fail_once_counter += 1
        if fail_once_counter == 1:
            raise IntegrityError("mock unique constraint", orig=Exception("race condition"), params={})
        await orig_commit()

    # 1. Retry recovers on first failure
    async_db_session.commit = commit_fail_once
    new_phase = await service.add_phase(
        patient_1_id,
        plan_id,
        schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase Retry Success"),
    )
    assert new_phase.name == "Phase Retry Success"
    assert fail_once_counter >= 2

    # 2. Both attempts fail -> clean 409
    async def commit_fail_always():
        raise IntegrityError("mock unique constraint", orig=Exception("persistent race"), params={})

    async_db_session.commit = commit_fail_always
    with pytest.raises(HTTPException) as exc:
        await service.add_phase(
            patient_1_id,
            plan_id,
            schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase Failing Double"),
        )
    assert exc.value.status_code == 409
    assert "conflict" in exc.value.detail.lower()

    # Restore original commit
    async_db_session.commit = orig_commit


@pytest.mark.asyncio
async def test_add_work_item_integrity_error_retry_and_missing_greenlet_safety(seed_data, async_db_session, monkeypatch):
    """
    Fix B: Verify add_work_item_to_phase retry path handles rollback cleanly without MissingGreenlet errors,
    and returns 409 on persistent conflict.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    service = TreatmentPlanService(db=async_db_session, tenant_id=tenant_1.id, current_user=doctor_1)

    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Item Retry Plan"))
    phase = plan.phases[0]

    wi = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="D0120",
        status="planned",
    )
    async_db_session.add(wi)
    await async_db_session.commit()

    tenant_1_id = tenant_1.id
    patient_1_id = patient_1.id
    plan_id = plan.id
    phase_id = phase.id
    wi_id = wi.id

    orig_commit = async_db_session.commit
    fail_once_counter = 0

    async def commit_fail_once():
        nonlocal fail_once_counter
        fail_once_counter += 1
        if fail_once_counter == 1:
            raise IntegrityError("mock unique constraint", orig=Exception("race condition"), params={})
        await orig_commit()

    # 1. Retry recovers on first failure
    async_db_session.commit = commit_fail_once
    item = await service.add_work_item_to_phase(
        patient_1_id,
        plan_id,
        phase_id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_id),
    )
    assert item.work_item_id == wi_id
    assert fail_once_counter >= 2

    # 2. Both attempts fail -> clean 409
    wi2 = models.ClinicalWorkItem(
        tenant_id=tenant_1_id,
        patient_id=patient_1_id,
        kind="procedure",
        code="D0140",
        status="planned",
    )
    async_db_session.add(wi2)
    await orig_commit()
    wi2_id = wi2.id

    async def commit_fail_always():
        raise IntegrityError("mock unique constraint", orig=Exception("persistent race"), params={})

    async_db_session.commit = commit_fail_always
    with pytest.raises(HTTPException) as exc:
        await service.add_work_item_to_phase(
            patient_1_id,
            plan_id,
            phase_id,
            schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi2_id),
        )
    assert exc.value.status_code == 409

    # Restore original commit
    async_db_session.commit = orig_commit


@pytest.mark.asyncio
async def test_transition_router_endpoint_rbac_and_gates(client, seed_data, async_db_session, monkeypatch):
    """
    Decision 5: Router endpoint POST /patients/{pid}/clinical-plans/{plan_id}/transition
    - Requires TREATMENT_PLAN_WRITE (doctor: 200, receptionist: 403)
    - Tenant and patient scoped (cross-tenant / patient mismatch: 404)
    - Gate fail-closed (flag-off: 404)
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    receptionist_1 = seed_data["receptionist_1"]
    patient_1 = seed_data["patient_1"]
    patient_2 = seed_data["patient_2"]

    doc_token = create_access_token(data={"sub": doctor_1.username, "tenant_id": tenant_1.id})
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    recep_token = create_access_token(data={"sub": receptionist_1.username, "tenant_id": tenant_1.id})
    recep_headers = {"Authorization": f"Bearer {recep_token}"}

    # 1. Create a plan
    res_create = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
        json={"title": "Endpoint Lifecycle Plan"},
    )
    assert res_create.status_code == 200
    plan_id = res_create.json()["data"]["id"]

    # 2. Receptionist without TREATMENT_PLAN_WRITE gets 403
    res_recep = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/transition",
        headers=recep_headers,
        json={"to_status": "proposed"},
    )
    assert res_recep.status_code == 403

    # 3. Doctor with TREATMENT_PLAN_WRITE succeeds -> proposed
    res_prop = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/transition",
        headers=doc_headers,
        json={"to_status": "proposed"},
    )
    assert res_prop.status_code == 200
    assert res_prop.json()["data"]["status"] == "proposed"

    # 4. Patient mismatch / cross-tenant gets uniform 404
    res_mismatch = client.post(
        f"/api/v1/patients/{patient_2.id}/clinical-plans/{plan_id}/transition",
        headers=doc_headers,
        json={"to_status": "accepted"},
    )
    assert res_mismatch.status_code == 404

    # 5. Flag-off returns 404
    monkeypatch.delenv("CLINICAL_TREATMENT_PLANS_ENABLED", raising=False)
    res_flag_off = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/transition",
        headers=doc_headers,
        json={"to_status": "accepted"},
    )
    assert res_flag_off.status_code == 404


@pytest.mark.asyncio
async def test_phase_update_success_and_guards(seed_data, async_db_session, monkeypatch):
    """
    Test phase update (name/notes):
    - Succeeds in draft and proposed statuses.
    - Locked (409) in accepted/completed/cancelled statuses.
    - Validation (422) on empty name.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]

    service = TreatmentPlanService(async_db_session, tenant_1.id, doctor_1)
    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Phase Edit Plan"))
    default_phase = plan.phases[0]

    # 1. Update name and notes in draft
    updated = await service.update_phase(
        patient_1.id,
        plan.id,
        default_phase.id,
        schemas.ClinicalTreatmentPlanPhaseUpdate(name="Preparatory Phase", notes="Clean tartar first"),
    )
    assert updated.name == "Preparatory Phase"
    assert updated.notes == "Clean tartar first"

    # 2. Transition to proposed -> update still succeeds
    await service.transition_plan(patient_1.id, plan.id, "proposed")
    updated_prop = await service.update_phase(
        patient_1.id,
        plan.id,
        default_phase.id,
        schemas.ClinicalTreatmentPlanPhaseUpdate(name="Phase 1 - Prep"),
    )
    assert updated_prop.name == "Phase 1 - Prep"
    assert updated_prop.notes == "Clean tartar first"  # Unchanged

    # 3. Validation error on empty name
    with pytest.raises(HTTPException) as exc_empty:
        await service.update_phase(
            patient_1.id,
            plan.id,
            default_phase.id,
            schemas.ClinicalTreatmentPlanPhaseUpdate(name="   "),
        )
    assert exc_empty.value.status_code == 422

    # 4. Transition to accepted -> update phase fails with 409
    await service.transition_plan(patient_1.id, plan.id, "accepted")
    with pytest.raises(HTTPException) as exc_locked:
        await service.update_phase(
            patient_1.id,
            plan.id,
            default_phase.id,
            schemas.ClinicalTreatmentPlanPhaseUpdate(name="Cannot Change"),
        )
    assert exc_locked.value.status_code == 409
    assert "cannot be updated" in exc_locked.value.detail


@pytest.mark.asyncio
async def test_phase_reorder_atomic_and_guards(seed_data, async_db_session, monkeypatch):
    """
    Test phase reordering (G9-M03):
    - Atomically reorders phase_order without uq_ctpp_plan_phase_order collision.
    - Validates all phases must be present (422 on missing/duplicate).
    - Locked (409) in accepted/completed/cancelled statuses.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]

    service = TreatmentPlanService(async_db_session, tenant_1.id, doctor_1)
    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Reorder Test Plan"))
    phase_0 = plan.phases[0]  # phase_order: 0

    phase_1 = await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 2"))
    phase_2 = await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 3"))

    assert [p.id for p in [phase_0, phase_1, phase_2]] == [phase_0.id, phase_1.id, phase_2.id]

    # Reverse order: [phase_2, phase_1, phase_0]
    reversed_phases = await service.reorder_phases(
        patient_1.id,
        plan.id,
        schemas.ClinicalTreatmentPlanPhaseReorder(phase_ids=[phase_2.id, phase_1.id, phase_0.id]),
    )
    assert [p.id for p in reversed_phases] == [phase_2.id, phase_1.id, phase_0.id]
    assert [p.phase_order for p in reversed_phases] == [0, 1, 2]

    # Swap again: [phase_1, phase_0, phase_2]
    reordered_again = await service.reorder_phases(
        patient_1.id,
        plan.id,
        schemas.ClinicalTreatmentPlanPhaseReorder(phase_ids=[phase_1.id, phase_0.id, phase_2.id]),
    )
    assert [p.id for p in reordered_again] == [phase_1.id, phase_0.id, phase_2.id]
    assert [p.phase_order for p in reordered_again] == [0, 1, 2]

    # 422 on duplicate phase IDs
    with pytest.raises(HTTPException) as exc_dup:
        await service.reorder_phases(
            patient_1.id,
            plan.id,
            schemas.ClinicalTreatmentPlanPhaseReorder(phase_ids=[phase_1.id, phase_1.id, phase_2.id]),
        )
    assert exc_dup.value.status_code == 422

    # 422 on missing phase IDs
    with pytest.raises(HTTPException) as exc_missing:
        await service.reorder_phases(
            patient_1.id,
            plan.id,
            schemas.ClinicalTreatmentPlanPhaseReorder(phase_ids=[phase_1.id, phase_2.id]),
        )
    assert exc_missing.value.status_code == 422

    # 409 when plan transitioned to accepted
    await service.transition_plan(patient_1.id, plan.id, "proposed")
    await service.transition_plan(patient_1.id, plan.id, "accepted")
    with pytest.raises(HTTPException) as exc_locked:
        await service.reorder_phases(
            patient_1.id,
            plan.id,
            schemas.ClinicalTreatmentPlanPhaseReorder(phase_ids=[phase_0.id, phase_1.id, phase_2.id]),
        )
    assert exc_locked.value.status_code == 409


@pytest.mark.asyncio
async def test_phase_delete_and_guards(seed_data, async_db_session, monkeypatch):
    """
    Test phase deletion (G9-M03):
    - Succeeds in draft/proposed plan.
    - Underlying ClinicalWorkItems linked to items are untouched.
    - Remaining phases re-compacted sequentially.
    - Locked (409) in accepted/completed/cancelled statuses.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]

    # Create work item
    wi = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="CROWN_PORCELAIN",
        status="active",
        created_by_user_id=doctor_1.id,
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    service = TreatmentPlanService(async_db_session, tenant_1.id, doctor_1)
    plan = await service.create_plan(patient_1.id, schemas.ClinicalTreatmentPlanCreate(title="Delete Phase Plan"))
    phase_0 = plan.phases[0]
    phase_1 = await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 2"))
    phase_2 = await service.add_phase(patient_1.id, plan.id, schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 3"))

    # Attach work item to phase 1
    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_1.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi.id),
    )

    # Delete phase 1 (the middle phase)
    await service.delete_phase(patient_1.id, plan.id, phase_1.id)

    # Reload plan
    plans = await service.list_plans(patient_1.id)
    plan_reloaded = next(p for p in plans if p.id == plan.id)
    remaining_phases = sorted(plan_reloaded.phases, key=lambda x: x.phase_order)
    assert len(remaining_phases) == 2
    assert [p.id for p in remaining_phases] == [phase_0.id, phase_2.id]
    assert [p.phase_order for p in remaining_phases] == [0, 1]

    # Underlying work item is untouched
    stmt_wi = select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi.id)
    wi_reloaded = (await async_db_session.execute(stmt_wi)).scalar_one()
    assert wi_reloaded.status == "active"

    # Transition to proposed -> delete still works
    await service.transition_plan(patient_1.id, plan.id, "proposed")
    await service.delete_phase(patient_1.id, plan.id, phase_2.id)

    # Transition to accepted -> delete fails with 409
    await service.transition_plan(patient_1.id, plan.id, "accepted")
    with pytest.raises(HTTPException) as exc_locked:
        await service.delete_phase(patient_1.id, plan.id, phase_0.id)
    assert exc_locked.value.status_code == 409


def test_phase_endpoints_router_integration(client, seed_data, monkeypatch):
    """
    Test HTTP endpoints for phase PATCH, reorder POST, and DELETE:
    - TREATMENT_PLAN_WRITE permission required.
    - Receptionist without permission gets 403.
    - Flag-off returns 404.
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    tenant_1 = seed_data["tenant_1"]
    doctor_1 = seed_data["doctor_1"]
    receptionist_1 = seed_data["receptionist_1"]
    patient_1 = seed_data["patient_1"]

    doc_token = create_access_token(data={"sub": doctor_1.username, "tenant_id": tenant_1.id})
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    recep_token = create_access_token(data={"sub": receptionist_1.username, "tenant_id": tenant_1.id})
    recep_headers = {"Authorization": f"Bearer {recep_token}"}

    # Create plan
    res_create = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
        json={"title": "Router Phase Test Plan"},
    )
    assert res_create.status_code == 200
    plan_id = res_create.json()["data"]["id"]
    phase_0_id = res_create.json()["data"]["phases"][0]["id"]

    # Add second phase
    res_add_ph = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases",
        headers=doc_headers,
        json={"name": "Second Phase"},
    )
    assert res_add_ph.status_code == 200
    phase_1_id = res_add_ph.json()["data"]["id"]

    # 1. PATCH phase (Update)
    # Receptionist gets 403
    res_patch_recep = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_0_id}",
        headers=recep_headers,
        json={"name": "Updated by Recep"},
    )
    assert res_patch_recep.status_code == 403

    # Doctor succeeds
    res_patch_doc = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_0_id}",
        headers=doc_headers,
        json={"name": "Renamed Phase 1", "notes": "New phase notes"},
    )
    assert res_patch_doc.status_code == 200
    assert res_patch_doc.json()["data"]["name"] == "Renamed Phase 1"
    assert res_patch_doc.json()["data"]["notes"] == "New phase notes"

    # 2. POST reorder
    # Receptionist gets 403
    res_reorder_recep = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/reorder",
        headers=recep_headers,
        json={"phase_ids": [phase_1_id, phase_0_id]},
    )
    assert res_reorder_recep.status_code == 403

    # Doctor succeeds
    res_reorder_doc = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/reorder",
        headers=doc_headers,
        json={"phase_ids": [phase_1_id, phase_0_id]},
    )
    assert res_reorder_doc.status_code == 200
    phases_out = res_reorder_doc.json()["data"]
    assert [p["id"] for p in phases_out] == [phase_1_id, phase_0_id]
    assert [p["phase_order"] for p in phases_out] == [0, 1]

    # 3. DELETE phase
    # Receptionist gets 403
    res_del_recep = client.delete(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_1_id}",
        headers=recep_headers,
    )
    assert res_del_recep.status_code == 403

    # Doctor succeeds
    res_del_doc = client.delete(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_1_id}",
        headers=doc_headers,
    )
    assert res_del_doc.status_code == 200

    # 4. Flag off -> 404
    monkeypatch.delenv("CLINICAL_TREATMENT_PLANS_ENABLED", raising=False)
    res_flag_off = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_0_id}",
        headers=doc_headers,
        json={"name": "Will fail"},
    )
    assert res_flag_off.status_code == 404


# ===========================================================================
# Slice S13: Treatment Plan Dynamic Estimate Projection (G9-M10, D2, PD04)
# ===========================================================================


@pytest.mark.asyncio
async def test_dynamic_estimates_priority_price_lists_and_unpriced(async_db_session, seed_data, monkeypatch):
    """
    Test dynamic estimate projection:
    - Priority 1: Patient default price list (PriceListItem)
    - Priority 2: Clinic default price list (PriceListItem)
    - Priority 3: Base Procedure price (Procedure.price)
    - Priority 4: Unpriced procedure fallback (fee=0.00, unpriced=True)
    - Phase subtotal and plan total aggregations (G9-M10, Decision D2 & PD04).
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    patient_1 = seed_data["patient_1"]
    doctor_1 = seed_data["doctor_1"]
    tenant_1 = seed_data["tenant_1"]

    service = TreatmentPlanService(async_db_session, tenant_1.id, doctor_1)

    # 1. Create Price Lists
    vip_price_list = models.PriceList(
        tenant_id=tenant_1.id,
        name="VIP Price List",
        is_default=False,
        is_active=True,
    )
    clinic_default_list = models.PriceList(
        tenant_id=tenant_1.id,
        name="Standard Cash List",
        is_default=True,
        is_active=True,
    )
    async_db_session.add_all([vip_price_list, clinic_default_list])
    await async_db_session.flush()

    # Assign patient_1 to VIP Price List
    patient_1.default_price_list_id = vip_price_list.id
    await async_db_session.flush()

    # 2. Create Procedures
    # Proc 1: in VIP list, in default list, has base price
    proc_1 = models.Procedure(tenant_id=tenant_1.id, name="Proc VIP", price=500.0)
    # Proc 2: NOT in VIP list, in default list, has base price
    proc_2 = models.Procedure(tenant_id=tenant_1.id, name="Proc Standard", price=300.0)
    # Proc 3: NOT in any price list, has base price
    proc_3 = models.Procedure(tenant_id=tenant_1.id, name="Proc BaseOnly", price=150.0)
    async_db_session.add_all([proc_1, proc_2, proc_3])
    await async_db_session.flush()

    # PriceListItems
    pli_vip = models.PriceListItem(
        price_list_id=vip_price_list.id,
        procedure_id=proc_1.id,
        price=400.0,
    )
    pli_def_1 = models.PriceListItem(
        price_list_id=clinic_default_list.id,
        procedure_id=proc_1.id,
        price=450.0,
    )
    pli_def_2 = models.PriceListItem(
        price_list_id=clinic_default_list.id,
        procedure_id=proc_2.id,
        price=250.0,
    )
    async_db_session.add_all([pli_vip, pli_def_1, pli_def_2])
    await async_db_session.flush()

    # 3. Create Work Items
    wi_1 = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="Proc VIP",
        status="planned",
    )
    wi_2 = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="Proc Standard",
        status="planned",
    )
    wi_3 = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="Proc BaseOnly",
        status="planned",
    )
    wi_unpriced = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="UNKNOWN_CUSTOM_PROC",
        status="planned",
    )
    async_db_session.add_all([wi_1, wi_2, wi_3, wi_unpriced])
    await async_db_session.flush()

    # 4. Create Plan with 2 phases
    plan = await service.create_plan(
        patient_1.id,
        schemas.ClinicalTreatmentPlanCreate(title="Estimated Multi-Phase Plan"),
    )
    phase_0 = plan.phases[0]

    phase_1 = await service.add_phase(
        patient_1.id,
        plan.id,
        schemas.ClinicalTreatmentPlanPhaseCreate(name="Phase 2: Complex"),
    )

    # Attach to Phase 0: Item 1 & Item 2
    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_0.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_1.id),
    )
    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_0.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_2.id),
    )

    # Attach to Phase 1: Item 3 & Unpriced Item
    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_1.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_3.id),
    )
    await service.add_work_item_to_phase(
        patient_1.id,
        plan.id,
        phase_1.id,
        schemas.ClinicalTreatmentPlanItemCreate(work_item_id=wi_unpriced.id),
    )

    # 5. Fetch plan and verify dynamic estimates
    fetched_plan = await service.get_plan(patient_1.id, plan.id)
    phases = fetched_plan.phases
    assert len(phases) == 2

    # Phase 0 items
    p0 = phases[0]
    assert p0.phase_order == 0
    p0_items = {it.work_item_id: it for it in p0.items}

    # Item 1: from patient's VIP list -> 400.0
    assert p0_items[wi_1.id].estimated_fee == 400.0
    assert p0_items[wi_1.id].unpriced is False

    # Item 2: not in VIP list, falls back to clinic default list -> 250.0
    assert p0_items[wi_2.id].estimated_fee == 250.0
    assert p0_items[wi_2.id].unpriced is False

    # Phase 0 subtotal
    assert p0.phase_estimated_total == 650.0
    assert p0.unpriced_items_count == 0

    # Phase 1 items
    p1 = phases[1]
    assert p1.phase_order == 1
    p1_items = {it.work_item_id: it for it in p1.items}

    # Item 3: not in any price list, falls back to Procedure.price -> 150.0
    assert p1_items[wi_3.id].estimated_fee == 150.0
    assert p1_items[wi_3.id].unpriced is False

    # Item 4: unpriced procedure -> 0.00, unpriced=True
    assert p1_items[wi_unpriced.id].estimated_fee == 0.0
    assert p1_items[wi_unpriced.id].unpriced is True

    # Phase 1 subtotal
    assert p1.phase_estimated_total == 150.0
    assert p1.unpriced_items_count == 1

    # Plan total
    assert fetched_plan.plan_estimated_total == 800.0
    assert fetched_plan.unpriced_items_count == 1

    # 6. Test dedicated get_plan_estimate method
    estimate_read = await service.get_plan_estimate(patient_1.id, plan.id)
    assert estimate_read.plan_id == plan.id
    assert estimate_read.plan_estimated_total == 800.0
    assert estimate_read.unpriced_items_count == 1
    assert estimate_read.price_list_id == vip_price_list.id
    assert len(estimate_read.phases) == 2
    assert estimate_read.phases[0].phase_estimated_total == 650.0
    assert estimate_read.phases[1].phase_estimated_total == 150.0


@pytest.mark.asyncio
async def test_dynamic_estimates_zero_database_side_effects(async_db_session, seed_data, monkeypatch):
    """
    Verify Decision D2 & PD04 invariant:
    Computing and viewing dynamic estimates must NEVER write to finance tables or alter legacy data:
    - 0 treatments created
    - 0 payments created
    - 0 stock movements created
    - 0 material usages created
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    patient_1 = seed_data["patient_1"]
    doctor_1 = seed_data["doctor_1"]
    tenant_1 = seed_data["tenant_1"]

    service = TreatmentPlanService(async_db_session, tenant_1.id, doctor_1)

    # Record baseline counts of finance / clinical legacy tables
    count_treatments_before = (
        await async_db_session.execute(select(func.count(models.Treatment.id)))
    ).scalar_one()
    count_payments_before = (
        await async_db_session.execute(select(func.count(models.Payment.id)))
    ).scalar_one()
    count_stock_before = (
        await async_db_session.execute(select(func.count(models.StockMovement.id)))
    ).scalar_one()
    count_usages_before = (
        await async_db_session.execute(select(func.count(models.TreatmentMaterialUsage.id)))
    ).scalar_one()

    # Perform multiple estimate queries
    plans = await service.list_plans(patient_1.id)
    if plans:
        await service.get_plan_estimate(patient_1.id, plans[0].id)

    # Verify counts remain 100% invariant
    count_treatments_after = (
        await async_db_session.execute(select(func.count(models.Treatment.id)))
    ).scalar_one()
    count_payments_after = (
        await async_db_session.execute(select(func.count(models.Payment.id)))
    ).scalar_one()
    count_stock_after = (
        await async_db_session.execute(select(func.count(models.StockMovement.id)))
    ).scalar_one()
    count_usages_after = (
        await async_db_session.execute(select(func.count(models.TreatmentMaterialUsage.id)))
    ).scalar_one()

    assert count_treatments_after == count_treatments_before
    assert count_payments_after == count_payments_before
    assert count_stock_after == count_stock_before
    assert count_usages_after == count_usages_before


@pytest.mark.asyncio
async def test_http_endpoints_estimate_projection(client, seed_data, async_db_session, monkeypatch):
    """
    Test HTTP GET endpoints for estimate projection:
    - GET /api/v1/patients/{patient_id}/clinical-plans/{plan_id}
    - GET /api/v1/patients/{patient_id}/clinical-plans/{plan_id}/estimate
    - Read permissions (CLINICAL_READ)
    """
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    patient_1 = seed_data["patient_1"]
    doctor_1 = seed_data["doctor_1"]
    tenant_1 = seed_data["tenant_1"]

    doc_token = create_access_token(
        data={"sub": doctor_1.username, "tenant_id": doctor_1.tenant_id, "role": "doctor"}
    )
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Setup procedure and work item
    proc = models.Procedure(tenant_id=tenant_1.id, name="Proc Extraction", price=120.0)
    async_db_session.add(proc)
    await async_db_session.flush()

    wi = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="Proc Extraction",
        status="planned",
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    # Create plan via HTTP
    res_plan = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
        json={"title": "Estimate HTTP Plan"},
    )
    assert res_plan.status_code == 200
    plan_data = res_plan.json()["data"]
    plan_id = plan_data["id"]
    phase_id = plan_data["phases"][0]["id"]

    # Attach item
    res_add_item = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/phases/{phase_id}/items",
        headers=doc_headers,
        json={"work_item_id": wi.id},
    )
    assert res_add_item.status_code == 200

    # 1. GET single plan with estimates
    res_get_plan = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}",
        headers=doc_headers,
    )
    assert res_get_plan.status_code == 200
    data_plan = res_get_plan.json()["data"]
    assert data_plan["plan_estimated_total"] == 120.0
    assert data_plan["unpriced_items_count"] == 0
    assert data_plan["phases"][0]["phase_estimated_total"] == 120.0
    assert data_plan["phases"][0]["items"][0]["estimated_fee"] == 120.0
    assert data_plan["phases"][0]["items"][0]["unpriced"] is False

    # 2. GET dedicated plan estimate projection
    res_estimate = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans/{plan_id}/estimate",
        headers=doc_headers,
    )
    assert res_estimate.status_code == 200
    data_est = res_estimate.json()["data"]
    assert data_est["plan_id"] == plan_id
    assert data_est["plan_estimated_total"] == 120.0
    assert data_est["unpriced_items_count"] == 0
    assert len(data_est["phases"]) == 1
    assert data_est["phases"][0]["phase_estimated_total"] == 120.0
    assert data_est["phases"][0]["items"][0]["estimated_fee"] == 120.0

    # 3. GET all plans list includes plan_estimated_total
    res_list = client.get(
        f"/api/v1/patients/{patient_1.id}/clinical-plans",
        headers=doc_headers,
    )
    assert res_list.status_code == 200
    plans_list = res_list.json()["data"]
    matched = [p for p in plans_list if p["id"] == plan_id]
    assert len(matched) == 1
    assert matched[0]["plan_estimated_total"] == 120.0
