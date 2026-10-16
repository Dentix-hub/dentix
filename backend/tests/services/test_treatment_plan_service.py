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
from sqlalchemy import select

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
