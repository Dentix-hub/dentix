"""
PR-09A Acceptance Test Suite: Patient, Clinical, and Appointment Module Governance.

Acceptance Criteria:
1. Every registered clinical / appointment action enforces commercial gating:
   - Permitted active plan + role succeeds on new writes and reads.
   - Expired / restricted plan blocks new clinical & appointment writes with HTTP 403.
   - Authorized clinical history reads are PERMANENTLY preserved under the Clinical History Invariant.
2. Emergency restriction on 'clinical' stops all new writes immediately, without breaking history reads.
3. Commercial overrides disabling 'clinical' on tenant stop all new writes immediately.
4. Direct domain service calls (CareSessionService, TreatmentPlanService) fail-closed on writes, preserve reads.
5. Related AI tools (create_patient, create_appointment, record_medical_note vs get_patient_file, get_appointments, get_recent_treatments) obey the commercial decision.
6. RBAC permissions and canonical doctor patient visibility remain strictly enforced in all subscription states.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from fastapi.testclient import TestClient

from backend import models, schemas
from backend.main import app
from backend.auth import create_access_token, get_password_hash
from backend.core.permissions import Permission, Role
from backend.core.commercial_registry import CapabilityKey, OperationClass
from backend.services.commercial_decision import CommercialDecisionEngine
from backend.services.entitlement_service import EntitlementService
from backend.services.care_session_service import CareSessionService
from backend.services.treatment_plan_service import TreatmentPlanService
from backend.ai.executor import ToolExecutor


@pytest.fixture(autouse=True)
def enforce_subscription_mode_for_pr09a(monkeypatch):
    """Ensure subscription enforcement mode is 'enforce' for PR-09A tests."""
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")


def _auth_header(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pr09a_setup(db_session):
    """Seed test plans, active clinic, expired clinic, and users."""
    now = datetime.now(timezone.utc)

    # 1. Full Clinical Plan
    plan_full = models.SubscriptionPlan(
        name="pr09a_full_plan",
        display_name_ar="خطة إكلينيكية كاملة",
        price=Decimal("200.00"),
        max_users=5,
        is_ai_enabled=True,
        ai_daily_limit=10,
        features='{"clinical": true, "billing": true, "ai_insights": true}',
    )
    # 2. Plan Without Clinical (Billing only)
    plan_no_clinical = models.SubscriptionPlan(
        name="pr09a_no_clinical_plan",
        display_name_ar="خطة محاسبية فقط",
        price=Decimal("150.00"),
        max_users=5,
        is_ai_enabled=False,
        ai_daily_limit=0,
        features='{"clinical": false, "billing": true, "ai_insights": false}',
    )
    db_session.add_all([plan_full, plan_no_clinical])
    db_session.commit()
    for p in (plan_full, plan_no_clinical):
        db_session.refresh(p)

    # 3. Active Clinic (Full Plan)
    tenant_active = models.Tenant(
        name="PR09A Active Clinic",
        plan=plan_full.name,
        plan_id=plan_full.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=25),
        is_active=True,
    )
    tenant_active.subscription_plan = plan_full

    # 4. Expired Clinic (Full Plan, but subscription ended 10 days ago, past 7 grace days)
    tenant_expired = models.Tenant(
        name="PR09A Expired Clinic",
        plan=plan_full.name,
        plan_id=plan_full.id,
        subscription_status="expired_read_only",
        subscription_end_date=now - timedelta(days=10),
        grace_period_until=now - timedelta(days=3),
        is_active=True,
    )
    tenant_expired.subscription_plan = plan_full

    # 5. Restricted Clinic (Active subscription, but Plan has clinical=False)
    tenant_restricted = models.Tenant(
        name="PR09A Restricted Clinic",
        plan=plan_no_clinical.name,
        plan_id=plan_no_clinical.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=25),
        is_active=True,
    )
    tenant_restricted.subscription_plan = plan_no_clinical

    db_session.add_all([tenant_active, tenant_expired, tenant_restricted])
    db_session.commit()
    for t in (tenant_active, tenant_expired, tenant_restricted):
        db_session.refresh(t)

    # 6. Users
    doc_active = models.User(
        username="pr09a_doc_active",
        email="doc_active@pr09a.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_active.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    doc_expired = models.User(
        username="pr09a_doc_expired",
        email="doc_exp@pr09a.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_expired.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    doc_restricted = models.User(
        username="pr09a_doc_restricted",
        email="doc_rest@pr09a.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_restricted.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    db_session.add_all([doc_active, doc_expired, doc_restricted])
    db_session.commit()
    for u in (doc_active, doc_expired, doc_restricted):
        db_session.refresh(u)

    # 7. Pre-existing patient, appointment, care session, treatment plan in expired clinic
    patient_exp = models.Patient(
        name="Zainab Historical",
        phone="01011112222",
        age=32,
        tenant_id=tenant_expired.id,
        assigned_doctor_id=doc_expired.id,
    )
    db_session.add(patient_exp)
    db_session.commit()
    db_session.refresh(patient_exp)

    appt_exp = models.Appointment(
        patient_id=patient_exp.id,
        doctor_id=doc_expired.id,
        tenant_id=tenant_expired.id,
        date_time=now - timedelta(days=12),
        status="completed",
        notes="Previous root canal visit",
    )
    db_session.add(appt_exp)

    session_exp = models.CareSession(
        patient_id=patient_exp.id,
        provider_user_id=doc_expired.id,
        tenant_id=tenant_expired.id,
        status="completed",
        started_at=now - timedelta(days=12),
        finished_at=now - timedelta(days=12, hours=-1),
    )
    db_session.add(session_exp)

    plan_exp = models.ClinicalTreatmentPlan(
        patient_id=patient_exp.id,
        created_by_user_id=doc_expired.id,
        tenant_id=tenant_expired.id,
        title="Comprehensive Restoration Plan",
        status="active",
    )
    db_session.add(plan_exp)
    db_session.commit()
    for obj in (appt_exp, session_exp, plan_exp):
        db_session.refresh(obj)

    return {
        "tenant_active": tenant_active,
        "tenant_expired": tenant_expired,
        "tenant_restricted": tenant_restricted,
        "doc_active": doc_active,
        "doc_expired": doc_expired,
        "doc_restricted": doc_restricted,
        "patient_exp": patient_exp,
        "appt_exp": appt_exp,
        "session_exp": session_exp,
        "plan_exp": plan_exp,
    }


# ==============================================================================
# 1. Active Clinic: Permitted Writes and Reads
# ==============================================================================

def test_active_clinic_permitted_clinical_and_appointment_actions(client, pr09a_setup):
    """In an active clinic with clinical capability, writes and reads succeed."""
    doc_active = pr09a_setup["doc_active"]
    headers = _auth_header(doc_active)

    # 1. Create Patient (POST /patients)
    res_p = client.post(
        "/api/v1/patients",
        json={"name": "Kareem Active", "phone": "01099998888", "age": 25},
        headers=headers,
    )
    assert res_p.status_code == 200, res_p.text
    p_data = res_p.json()["data"]
    p_id = p_data["id"]

    # 2. Read Patient (GET /patients/{id})
    res_get_p = client.get(f"/api/v1/patients/{p_id}", headers=headers)
    assert res_get_p.status_code == 200
    assert res_get_p.json()["data"]["name"] == "Kareem Active"

    # 3. Create Appointment (POST /appointments)
    appt_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    res_appt = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": p_id,
            "doctor_id": doc_active.id,
            "date_time": appt_time,
            "notes": "Regular checkup",
        },
        headers=headers,
    )
    assert res_appt.status_code in {200, 201}, res_appt.text
    appt_id = res_appt.json()["data"]["id"]

    # 4. Read Appointments (GET /appointments)
    res_get_appt = client.get("/api/v1/appointments", headers=headers)
    assert res_get_appt.status_code == 200
    assert any(a["id"] == appt_id for a in res_get_appt.json()["data"])


# ==============================================================================
# 2. Expired Clinic: Writes Blocked, Historical Reads Permanently Preserved
# ==============================================================================

def test_expired_clinic_blocks_all_clinical_writes_while_preserving_reads(client, pr09a_setup):
    """
    Expired clinic:
    - All write/mutation requests to clinical and appointment endpoints return HTTP 403.
    - All historical read requests return HTTP 200 with accurate data under Clinical History Invariant.
    """
    doc_expired = pr09a_setup["doc_expired"]
    p_exp = pr09a_setup["patient_exp"]
    appt_exp = pr09a_setup["appt_exp"]
    session_exp = pr09a_setup["session_exp"]
    plan_exp = pr09a_setup["plan_exp"]
    headers = _auth_header(doc_expired)

    # -------------------------------------------------------------
    # MUTATIONS: Must be blocked with HTTP 403
    # -------------------------------------------------------------
    # 1. Create Patient -> 403
    res_new_p = client.post(
        "/api/v1/patients",
        json={"name": "Blocked Patient", "phone": "01000000000", "age": 40},
        headers=headers,
    )
    assert res_new_p.status_code == 403
    assert "اشتراك" in res_new_p.text or "expired" in res_new_p.text.lower()

    # 2. Update Patient -> 403
    res_upd_p = client.put(
        f"/api/v1/patients/{p_exp.id}",
        json={"name": "Zainab Mutated"},
        headers=headers,
    )
    assert res_upd_p.status_code == 403

    # 3. Create Appointment -> 403
    appt_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    res_new_appt = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": p_exp.id,
            "doctor_id": doc_expired.id,
            "date_time": appt_time,
        },
        headers=headers,
    )
    assert res_new_appt.status_code == 403

    # 4. Create Treatment Plan -> 403
    res_new_tp = client.post(
        f"/api/v1/patients/{p_exp.id}/clinical-plans",
        json={"title": "New Blocked Plan"},
        headers=headers,
    )
    assert res_new_tp.status_code == 403

    # 5. Create Care Session -> 403
    res_new_cs = client.post(
        f"/api/v1/patients/{p_exp.id}/care-sessions",
        json={},
        headers=headers,
    )
    assert res_new_cs.status_code == 403

    # -------------------------------------------------------------
    # HISTORICAL READS: Must SUCCEED with HTTP 200 (Clinical Invariant)
    # -------------------------------------------------------------
    # 1. Read Patient details -> 200
    res_read_p = client.get(f"/api/v1/patients/{p_exp.id}", headers=headers)
    assert res_read_p.status_code == 200
    assert res_read_p.json()["data"]["name"] == p_exp.name

    # 2. Read Patient Directory -> 200
    res_dir = client.get("/api/v1/patients", headers=headers)
    assert res_dir.status_code == 200

    # 3. Read Appointments -> 200
    res_read_appt = client.get("/api/v1/appointments", headers=headers)
    assert res_read_appt.status_code == 200
    assert any(a["id"] == appt_exp.id for a in res_read_appt.json()["data"])

    # 4. Read Treatment Plan -> 200
    res_read_tp = client.get(
        f"/api/v1/patients/{p_exp.id}/clinical-plans/{plan_exp.id}",
        headers=headers,
    )
    assert res_read_tp.status_code == 200
    assert res_read_tp.json()["data"]["title"] == plan_exp.title

    # 5. Read Care Session -> 200
    res_read_cs = client.get(
        f"/api/v1/patients/{p_exp.id}/care-sessions/{session_exp.id}",
        headers=headers,
    )
    assert res_read_cs.status_code == 200
    assert res_read_cs.json()["data"]["id"] == session_exp.id


# ==============================================================================
# 3. Plan Lacking Clinical Capability
# ==============================================================================

def test_plan_without_clinical_capability_blocks_writes_while_preserving_reads(client, pr09a_setup, db_session):
    """
    Clinic assigned a plan where clinical=False:
    - Writes fail with 403.
    - Existing history reads succeed with 200.
    """
    doc_restricted = pr09a_setup["doc_restricted"]
    tenant_restricted = pr09a_setup["tenant_restricted"]
    headers = _auth_header(doc_restricted)

    # Seed an existing patient in this restricted clinic
    patient = models.Patient(
        name="Nader Restricted Plan",
        phone="01077776666",
        tenant_id=tenant_restricted.id,
        assigned_doctor_id=doc_restricted.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # 1. Create Patient -> 403
    res_create = client.post(
        "/api/v1/patients",
        json={"name": "Must Block", "phone": "01033334444"},
        headers=headers,
    )
    assert res_create.status_code == 403

    # 2. Read existing patient -> 200 (Clinical History Invariant)
    res_read = client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["data"]["name"] == "Nader Restricted Plan"


# ==============================================================================
# 4. Emergency Restriction on 'clinical'
# ==============================================================================

def test_emergency_restriction_on_clinical_blocks_writes_immediately(client, pr09a_setup, db_session):
    """
    When an emergency restriction is active on 'clinical':
    - New clinical and appointment writes are immediately blocked with 403.
    - Historical reads remain permanently permitted.
    """
    doc_active = pr09a_setup["doc_active"]
    tenant_active = pr09a_setup["tenant_active"]
    headers = _auth_header(doc_active)

    # Seed an existing patient
    patient = models.Patient(
        name="Amira Emergency Test",
        phone="01055554444",
        tenant_id=tenant_active.id,
        assigned_doctor_id=doc_active.id,
    )
    db_session.add(patient)
    # Enable emergency restriction on 'clinical' in SystemSetting
    setting = models.SystemSetting(key="emergency_restriction_clinical", value="true")
    db_session.add(setting)
    db_session.commit()
    db_session.refresh(patient)

    try:
        # 1. Attempt to create a new patient under emergency restriction -> 403
        res_create = client.post(
            "/api/v1/patients",
            json={"name": "Emergency Blocked Patient", "phone": "01011110000"},
            headers=headers,
        )
        assert res_create.status_code == 403
        assert "طوارئ" in res_create.text or "emergency" in res_create.text.lower() or "حظر" in res_create.text

        # 2. Read existing patient -> 200
        res_read = client.get(f"/api/v1/patients/{patient.id}", headers=headers)
        assert res_read.status_code == 200
        assert res_read.json()["data"]["name"] == "Amira Emergency Test"
    finally:
        # Cleanup emergency setting
        db_session.delete(setting)
        db_session.commit()


# ==============================================================================
# 5. Direct Domain Service Layer Enforcement
# ==============================================================================

@pytest.mark.asyncio
async def test_direct_service_layer_care_session_and_treatment_plan_enforcement(
    async_db_session, pr09a_setup
):
    """
    Calling domain services directly:
    - CareSessionService.start_session on expired tenant raises HTTPException(403).
    - CareSessionService.get_session on expired tenant succeeds.
    - TreatmentPlanService.create_plan on expired tenant raises HTTPException(403).
    - TreatmentPlanService.get_plan on expired tenant succeeds.
    """
    from fastapi import HTTPException

    doc_expired = pr09a_setup["doc_expired"]
    tenant_expired = pr09a_setup["tenant_expired"]
    p_exp = pr09a_setup["patient_exp"]
    session_exp = pr09a_setup["session_exp"]
    plan_exp = pr09a_setup["plan_exp"]

    # 1. CareSessionService: Direct start_session raises 403
    care_service = CareSessionService(
        async_db_session, tenant_id=tenant_expired.id, current_user=doc_expired
    )
    with pytest.raises(HTTPException) as exc_cs:
        await care_service.start_session(
            patient_id=p_exp.id, data=schemas.CareSessionCreate()
        )
    assert exc_cs.value.status_code == 403

    # Direct get_session succeeds (Clinical History Invariant)
    pres = await care_service.get_session(patient_id=p_exp.id, session_id=session_exp.id)
    assert pres is not None
    assert pres.id == session_exp.id

    # 2. TreatmentPlanService: Direct create_plan raises 403
    tp_service = TreatmentPlanService(
        async_db_session, tenant_id=tenant_expired.id, current_user=doc_expired
    )
    with pytest.raises(HTTPException) as exc_tp:
        await tp_service.create_plan(
            patient_id=p_exp.id,
            plan_data=schemas.ClinicalTreatmentPlanCreate(title="Direct Plan Blocked"),
        )
    assert exc_tp.value.status_code == 403

    # Direct get_plan succeeds (Clinical History Invariant)
    plan_loaded = await tp_service.get_plan(patient_id=p_exp.id, plan_id=plan_exp.id)
    assert plan_loaded is not None
    assert plan_loaded.id == plan_exp.id


# ==============================================================================
# 6. Related AI Tools Enforce Commercial Gating
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_clinical_tools_enforce_commercial_decision(
    async_db_session, pr09a_setup
):
    """
    AI ToolExecutor:
    - Mutating tools (create_patient, create_appointment, record_medical_note) return success=False on expired clinic.
    - History read tools (get_patient_file, get_appointments, get_recent_treatments) return success=True.
    """
    doc_expired = pr09a_setup["doc_expired"]
    p_exp = pr09a_setup["patient_exp"]

    executor = ToolExecutor(async_db_session, doc_expired)

    # 1. Mutating tool create_patient -> Denied
    res_cp = await executor.execute("create_patient", {"name": "AI New Patient"})
    assert res_cp.get("success") is False
    assert res_cp.get("error_code") == "subscription_expired"

    # 2. Mutating tool create_appointment -> Denied
    res_ca = await executor.execute(
        "create_appointment",
        {
            "patient_name": p_exp.name,
            "date": "2026-11-10",
            "time": "10:00",
        },
    )
    assert res_ca.get("success") is False
    assert res_ca.get("error_code") == "subscription_expired"

    # 3. Mutating tool record_medical_note -> Denied
    res_note = await executor.execute(
        "record_medical_note",
        {"patient_name": p_exp.name, "content": "Follow up noted"},
    )
    assert res_note.get("success") is False
    assert res_note.get("error_code") == "subscription_expired"

    # 4. History read tool get_patient_file -> Allowed
    res_read_file = await executor.execute("get_patient_file", {"patient_name": p_exp.name})
    assert res_read_file.get("success") is True

    # 5. History read tool get_appointments -> Allowed
    res_read_appts = await executor.execute("get_appointments", {"patient_name": p_exp.name})
    assert res_read_appts.get("success") is True

    # 6. History read tool get_recent_treatments -> Allowed
    res_treatments = await executor.execute("get_recent_treatments", {})
    assert res_treatments.get("success") is True


# ==============================================================================
# 7. Multi-Doctor Patient Visibility and Cross-Tenant Isolation
# ==============================================================================

def test_rbac_and_tenant_isolation_preserved_on_expired_clinic(
    client, pr09a_setup, db_session
):
    """
    Even in an expired clinic:
    - A doctor cannot access another tenant's patients (cross-tenant isolation).
    - A doctor cannot access a patient assigned to another doctor (canonical visibility).
    """
    tenant_expired = pr09a_setup["tenant_expired"]
    p_exp = pr09a_setup["patient_exp"]  # Assigned to doc_expired
    doc_active = pr09a_setup["doc_active"]  # In tenant_active

    # Second doctor in tenant_expired
    doc_other = models.User(
        username="pr09a_doc_other",
        email="doc_other@pr09a.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_expired.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    db_session.add(doc_other)
    db_session.commit()
    db_session.refresh(doc_other)

    # 1. Doctor from another clinic attempting to read expired clinic's patient -> 404 (isolated)
    res_cross = client.get(
        f"/api/v1/patients/{p_exp.id}", headers=_auth_header(doc_active)
    )
    assert res_cross.status_code in {403, 404}

    # 2. Doctor from same clinic but NOT assigned to patient -> 404/403 (visibility denied)
    res_unassigned = client.get(
        f"/api/v1/patients/{p_exp.id}", headers=_auth_header(doc_other)
    )
    assert res_unassigned.status_code in {403, 404}
