"""
Tests for Care Session Service and Router (Slice S18).
Covers:
- G10-M01: Care session service creation and operations
- G10-M02: Start-session command & event logging
- G10-M03: Finish-session command & event logging
- G10-M18: Concurrency protection (Decision D3: strictly one active session per patient)
- Lifecycle status transitions (in_progress, paused, completed, cancelled)
- Feature flag gating (clinical_vnext_native_writes -> 404 when off)
- Tenant isolation and patient scoping
- RBAC permissions (CLINICAL_WRITE, CLINICAL_READ)
- Appointment parent patient verification
- Optimistic locking / StaleDataError mapping to 409 Conflict
"""

import asyncio
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.auth import create_access_token
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService


@pytest.fixture
async def seed_data(async_db_session):
    """Seed two tenants with users, patients, and appointments for isolation & RBAC testing."""
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
    await async_db_session.flush()

    appointment_1 = models.Appointment(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        doctor_id=doctor_1.id,
        date_time=datetime.now(timezone.utc),
        duration_minutes=30,
        status="Confirmed",
    )
    appointment_2 = models.Appointment(
        tenant_id=tenant_2.id,
        patient_id=patient_2.id,
        doctor_id=doctor_2.id,
        date_time=datetime.now(timezone.utc),
        duration_minutes=30,
        status="Confirmed",
    )
    work_item_1 = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor_1.id,
    )
    work_item_2 = models.ClinicalWorkItem(
        tenant_id=tenant_2.id,
        patient_id=patient_2.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor_2.id,
    )
    async_db_session.add_all([appointment_1, appointment_2, work_item_1, work_item_2])
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
        "appointment_1": appointment_1,
        "appointment_2": appointment_2,
        "work_item_1": work_item_1,
        "work_item_2": work_item_2,
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
async def test_flag_off_returns_404(client, seed_data, async_db_session):
    """When clinical_vnext_native_writes is OFF, all care session endpoints return 404."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    # Explicitly ensure flag is OFF
    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, False)

    # POST start session -> 404
    r_start = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Starting session with flag off"},
    )
    assert r_start.status_code == 404
    assert "disabled" in r_start.json()["detail"].lower()

    # GET active session -> 404
    r_active = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/active",
        headers=headers,
    )
    assert r_active.status_code == 404

    # GET list sessions -> 404
    r_list = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
    )
    assert r_list.status_code == 404


@pytest.mark.asyncio
async def test_start_care_session_success_and_audit_event(client, seed_data, async_db_session):
    """Starting a care session succeeds, sets in_progress, and appends ClinicalEvent."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    resp = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Root canal therapy session 1"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["patient_id"] == patient_1.id
    assert data["tenant_id"] == doctor_1.tenant_id
    assert data["status"] == "in_progress"
    assert data["provider_user_id"] == doctor_1.id
    assert data["started_at"] is not None
    assert data["finished_at"] is None
    assert data["notes"] == "Root canal therapy session 1"
    assert data["version_id"] == 1
    session_id = data["id"]

    # Verify append-only ClinicalEvent logged
    stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == session_id,
        models.ClinicalEvent.event_type == "care_session_started",
    )
    event = (await async_db_session.execute(stmt)).scalars().first()
    assert event is not None
    assert event.patient_id == patient_1.id
    assert event.actor_user_id == doctor_1.id
    assert event.payload["status"] == "in_progress"
    assert event.payload["session_id"] == session_id


@pytest.mark.asyncio
async def test_start_session_with_valid_appointment(client, seed_data, async_db_session):
    """Starting a care session linking a valid appointment of the patient succeeds."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    appointment_1 = seed_data["appointment_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    resp = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"appointment_id": appointment_1.id, "notes": "Linked to scheduled appt"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["appointment_id"] == appointment_1.id


@pytest.mark.asyncio
async def test_start_session_cross_patient_appointment_rejected(client, seed_data, async_db_session):
    """Attempting to link an appointment belonging to another patient returns 404."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    appointment_2 = seed_data["appointment_2"]  # Belongs to tenant 2 & patient 2
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    resp = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"appointment_id": appointment_2.id, "notes": "Mismatched appointment"},
    )
    assert resp.status_code == 404
    assert "appointment not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_d3_concurrency_one_active_session_per_patient(client, seed_data, async_db_session):
    """
    Enforces Decision D3 (G10-M18):
    Starting a second session while one is in_progress returns 409 Conflict with the active session ID.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Start first session
    r1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "First active session"},
    )
    assert r1.status_code == 201
    s1_id = r1.json()["data"]["id"]

    # 2. Attempt to start second session while first is in_progress
    r2 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Second session attempt (concurrent conflict)"},
    )
    assert r2.status_code == 409
    detail = r2.json()["detail"]
    assert detail["active_session_id"] == s1_id
    assert "already in progress" in detail["message"].lower()


@pytest.mark.asyncio
async def test_finish_care_session_success(client, seed_data, async_db_session):
    """Finishing an in-progress care session marks completed, records finished_at, and appends ClinicalEvent."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Start session
    r_start = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Chairside start"},
    )
    s_id = r_start.json()["data"]["id"]

    # Finish session
    r_finish = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/finish",
        headers=headers,
        json={"notes": "Procedure finished cleanly, obturation successful"},
    )
    assert r_finish.status_code == 200
    data = r_finish.json()["data"]
    assert data["id"] == s_id
    assert data["status"] == "completed"
    assert data["finished_at"] is not None
    assert "obturation successful" in data["notes"]

    # Verify event logged
    stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == s_id,
        models.ClinicalEvent.event_type == "care_session_finished",
    )
    event = (await async_db_session.execute(stmt)).scalars().first()
    assert event is not None
    assert event.payload["status"] == "completed"
    assert event.payload["finished_at"] is not None


@pytest.mark.asyncio
async def test_finish_session_terminal_status_error(client, seed_data, async_db_session):
    """Attempting to finish an already completed or cancelled session returns 400."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Start and finish
    r_start = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Start session"},
    )
    s_id = r_start.json()["data"]["id"]
    client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/finish",
        headers=headers,
        json={},
    )

    # Attempt second finish -> 400
    r_finish_2 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/finish",
        headers=headers,
        json={"notes": "Second finish attempt"},
    )
    assert r_finish_2.status_code == 400
    assert "cannot finish care session" in r_finish_2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_session_lifecycle_transitions(client, seed_data, async_db_session):
    """
    Tests allowed status transitions:
    in_progress -> paused -> in_progress -> cancelled
    and verifies invalid transitions are rejected with 400.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Start session
    r1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Initial state"},
    )
    s_id = r1.json()["data"]["id"]
    assert r1.json()["data"]["status"] == "in_progress"

    # 2. Pause session
    r2 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/transition",
        headers=headers,
        json={"to_status": "paused", "notes": "Paused for X-ray"},
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "paused"

    # Verify care_session_paused event
    stmt_pause = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == s_id,
        models.ClinicalEvent.event_type == "care_session_paused",
    )
    event_pause = (await async_db_session.execute(stmt_pause)).scalars().first()
    assert event_pause is not None

    # 3. Resume session (paused -> in_progress)
    r3 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/transition",
        headers=headers,
        json={"to_status": "in_progress", "notes": "Resumed after review"},
    )
    assert r3.status_code == 200
    assert r3.json()["data"]["status"] == "in_progress"

    # Verify care_session_resumed event
    stmt_resume = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == s_id,
        models.ClinicalEvent.event_type == "care_session_resumed",
    )
    event_resume = (await async_db_session.execute(stmt_resume)).scalars().first()
    assert event_resume is not None

    # 4. Cancel session (in_progress -> cancelled)
    r4 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/transition",
        headers=headers,
        json={"to_status": "cancelled", "notes": "Patient had to leave"},
    )
    assert r4.status_code == 200
    assert r4.json()["data"]["status"] == "cancelled"

    # 5. Invalid transition from cancelled (terminal) -> in_progress returns 400
    r5 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/transition",
        headers=headers,
        json={"to_status": "in_progress"},
    )
    assert r5.status_code == 400
    assert "invalid session status transition" in r5.json()["detail"].lower()


@pytest.mark.asyncio
async def test_d3_transition_to_in_progress_blocked_if_another_session_active(
    client, seed_data, async_db_session
):
    """
    If Session A is paused, and Session B is started (in_progress),
    transitioning Session A back to in_progress violates D3 and returns 409 Conflict.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Start Session A
    r_a = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Session A"},
    )
    s_a_id = r_a.json()["data"]["id"]

    # 2. Pause Session A
    client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_a_id}/transition",
        headers=headers,
        json={"to_status": "paused"},
    )

    # 3. Start Session B (now in_progress)
    r_b = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Session B"},
    )
    assert r_b.status_code == 201
    s_b_id = r_b.json()["data"]["id"]

    # 4. Attempt to resume Session A while Session B is in_progress -> 409 Conflict
    r_resume = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_a_id}/transition",
        headers=headers,
        json={"to_status": "in_progress"},
    )
    assert r_resume.status_code == 409
    detail = r_resume.json()["detail"]
    assert detail["active_session_id"] == s_b_id


@pytest.mark.asyncio
async def test_active_and_list_care_sessions_queries(client, seed_data, async_db_session):
    """Verify active session query and list queries with status filtering."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Initially no active session
    r_init = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/active",
        headers=headers,
    )
    assert r_init.status_code == 200
    assert r_init.json()["data"] is None

    # Start session 1
    r_s1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Session 1"},
    )
    s1_id = r_s1.json()["data"]["id"]

    # Now active returns session 1
    r_act = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/active",
        headers=headers,
    )
    assert r_act.status_code == 200
    assert r_act.json()["data"]["id"] == s1_id

    # Finish session 1
    client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s1_id}/finish",
        headers=headers,
        json={},
    )

    # Active is now None
    r_act2 = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/active",
        headers=headers,
    )
    assert r_act2.json()["data"] is None

    # Start session 2
    r_s2 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Session 2"},
    )
    s2_id = r_s2.json()["data"]["id"]

    # List all
    r_list = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
    )
    assert r_list.status_code == 200
    items = r_list.json()["data"]
    assert len(items) == 2

    # Filter by completed
    r_comp = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions?status=completed",
        headers=headers,
    )
    comp_items = r_comp.json()["data"]
    assert len(comp_items) == 1
    assert comp_items[0]["id"] == s1_id

    # Filter by in_progress
    r_prog = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions?status=in_progress",
        headers=headers,
    )
    prog_items = r_prog.json()["data"]
    assert len(prog_items) == 1
    assert prog_items[0]["id"] == s2_id


@pytest.mark.asyncio
async def test_tenant_isolation(client, seed_data, async_db_session):
    """Doctor from Tenant 2 cannot access, start, or modify care sessions of Tenant 1 patient."""
    doctor_1 = seed_data["doctor_1"]
    doctor_2 = seed_data["doctor_2"]
    patient_1 = seed_data["patient_1"]
    headers_1 = make_headers(doctor_1)
    headers_2 = make_headers(doctor_2)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)
    await set_native_writes_flag(async_db_session, doctor_2.tenant_id, True)

    # Tenant 1 creates a care session
    r1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers_1,
        json={"notes": "Tenant 1 session"},
    )
    s_id = r1.json()["data"]["id"]

    # Tenant 2 cannot get session by ID -> 404
    r_t2_get = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}",
        headers=headers_2,
    )
    assert r_t2_get.status_code == 404

    # Tenant 2 cannot list sessions for Tenant 1 patient -> 404
    r_t2_list = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers_2,
    )
    assert r_t2_list.status_code == 404

    # Tenant 2 cannot start session for Tenant 1 patient -> 404
    r_t2_start = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers_2,
        json={"notes": "Intrusion attempt"},
    )
    assert r_t2_start.status_code == 404

    # Tenant 2 cannot finish session of Tenant 1 -> 404
    r_t2_finish = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/finish",
        headers=headers_2,
        json={"notes": "Intrusion finish"},
    )
    assert r_t2_finish.status_code == 404


@pytest.mark.asyncio
async def test_rbac_permissions(client, seed_data, async_db_session):
    """
    Users without CLINICAL_WRITE (e.g. receptionist) cannot mutate sessions (403),
    while users with CLINICAL_WRITE can.
    """
    receptionist_1 = seed_data["receptionist_1"]
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    h_recep = make_headers(receptionist_1)
    h_doc = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Receptionist cannot start care session -> 403
    r_start = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=h_recep,
        json={"notes": "Receptionist trying to start clinical session"},
    )
    assert r_start.status_code == 403

    # Doctor can start session
    r_doc_start = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=h_doc,
        json={"notes": "Doctor starts session"},
    )
    assert r_doc_start.status_code == 201
    s_id = r_doc_start.json()["data"]["id"]

    # Receptionist cannot finish care session -> 403
    r_finish = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/finish",
        headers=h_recep,
        json={},
    )
    assert r_finish.status_code == 403

    # Receptionist cannot transition care session -> 403
    r_trans = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s_id}/transition",
        headers=h_recep,
        json={"to_status": "paused"},
    )
    assert r_trans.status_code == 403


@pytest.mark.asyncio
async def test_optimistic_concurrency_staledataerror_mapping(async_db_session, seed_data):
    """
    Simulating a concurrent mutation / StaleDataError during care session flush
    maps to 409 Conflict cleanly and reloads active user.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    patient_id = int(patient_1.id)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    service = CareSessionService(async_db_session, doctor_1.tenant_id, doctor_1)
    session = await service.start_session(
        patient_id, schemas.CareSessionCreate(notes="Initial")
    )
    assert session.version_id == 1
    session_id = session.id

    orig_flush = async_db_session.flush

    async def flush_stale(*args, **kwargs):
        raise StaleDataError(models.CareSession, "Row was updated or deleted by another transaction")

    async_db_session.flush = flush_stale
    try:
        with pytest.raises(HTTPException) as exc_info:
            await service.finish_session(
                patient_id,
                session_id,
                schemas.CareSessionFinish(notes="Stale update"),
            )
        assert exc_info.value.status_code == 409
        assert "conflict" in exc_info.value.detail.lower()
    finally:
        async_db_session.flush = orig_flush

    # Verify session remains in_progress and user can be re-queried without MissingGreenlet
    session_after = await service.get_session(patient_id, session_id)
    assert session_after.status == "in_progress"


# ---------------------------------------------------------------------------
# Slice S19 Tests: Steps, Observations, Free Notes & Finalization Audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_step_manual_and_auto_order(client, seed_data, async_db_session):
    """
    G10-M04: Add structured step to care session.
    Auto-assigns step_order sequentially and emits care_session_step_added event.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    work_item_1 = seed_data["work_item_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # 1. Start care session
    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "RCT Chairside"},
    )
    session_id = r_session.json()["data"]["id"]

    # 2. Add step 1 without step_order (auto-assigned to 1)
    r_step1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={
            "step_code": "access_cavity",
            "title": "Access Cavity Preparation",
            "work_item_id": work_item_1.id,
            "notes": "Good visibility, rubber dam placed",
        },
    )
    assert r_step1.status_code == 201
    s1_data = r_step1.json()["data"]
    assert s1_data["step_order"] == 1
    assert s1_data["step_code"] == "access_cavity"
    assert s1_data["status"] == "pending"
    assert s1_data["work_item_id"] == work_item_1.id
    assert "rubber dam placed" in s1_data["notes"]

    # 3. Add step 2 without step_order (auto-assigned to 2)
    r_step2 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={
            "step_code": "working_length",
            "title": "Working Length Determination",
            "status": "in_progress",
        },
    )
    assert r_step2.status_code == 201
    s2_data = r_step2.json()["data"]
    assert s2_data["step_order"] == 2
    assert s2_data["status"] == "in_progress"
    assert s2_data["started_at"] is not None

    # Verify audit event
    stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == session_id,
        models.ClinicalEvent.event_type == "care_session_step_added",
    )
    events = (await async_db_session.execute(stmt)).scalars().all()
    assert len(events) == 2


@pytest.mark.asyncio
async def test_partial_step_support(client, seed_data, async_db_session):
    """
    G10-M05: Add partial-step support.
    Step can be marked as 'partial' when procedure could only be partially completed chairside.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    session_id = r_session.json()["data"]["id"]

    # Add step initially pending
    r_step = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={"step_code": "canal_shaping", "title": "Canal Cleaning and Shaping"},
    )
    step_id = r_step.json()["data"]["id"]

    # Update step to partial
    r_update = client.patch(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps/{step_id}",
        headers=headers,
        json={
            "status": "partial",
            "notes": "MB and ML shaped to size 25. Distal canal calcified, deferred to next visit.",
        },
    )
    assert r_update.status_code == 200
    up_data = r_update.json()["data"]
    assert up_data["status"] == "partial"
    assert up_data["completed_at"] is not None
    assert "calcified" in up_data["notes"]


@pytest.mark.asyncio
async def test_update_step_and_preserve_notes(client, seed_data, async_db_session):
    """
    G10-M15: Preserve free notes across step creation and updates.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Session free note 1"},
    )
    session_id = r_session.json()["data"]["id"]

    r_step = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={"step_code": "prep", "title": "Preparation", "notes": "Initial step notes"},
    )
    step_id = r_step.json()["data"]["id"]
    assert r_step.json()["data"]["notes"] == "Initial step notes"

    r_patch = client.patch(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps/{step_id}",
        headers=headers,
        json={"notes": "Updated detailed clinical findings and step remarks", "status": "completed"},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["data"]["notes"] == "Updated detailed clinical findings and step remarks"
    assert r_patch.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_step_terminal_session_error(client, seed_data, async_db_session):
    """Attempting to add or update steps on a completed or cancelled session returns 400."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    session_id = r_session.json()["data"]["id"]

    # Finish session
    client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/finish",
        headers=headers,
        json={},
    )

    # Adding step to completed session -> 400
    r_add = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={"step_code": "post_finish", "title": "Late Step"},
    )
    assert r_add.status_code == 400
    assert "cannot add steps" in r_add.json()["detail"].lower()


@pytest.mark.asyncio
async def test_step_cross_patient_work_item_rejected(client, seed_data, async_db_session):
    """Attempting to link a step to a work item of another patient returns 404 (matching trigger trg_css_session_work_item_patient)."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    work_item_2 = seed_data["work_item_2"]  # Belongs to patient 2
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    session_id = r_session.json()["data"]["id"]

    r_step = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={
            "step_code": "invalid_wi",
            "title": "Invalid Work Item Step",
            "work_item_id": work_item_2.id,
        },
    )
    assert r_step.status_code == 404
    assert "work item not found" in r_step.json()["detail"].lower()


@pytest.mark.asyncio
async def test_apply_workflow_template_steps(client, seed_data, async_db_session):
    """
    Initialize care session steps from canonical workflow template blueprints (e.g. ENDO_RCT).
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    work_item_1 = seed_data["work_item_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    session_id = r_session.json()["data"]["id"]

    # Apply ENDO_RCT template
    r_apply = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps/from-template",
        headers=headers,
        json={"template_code": "ENDO_RCT", "work_item_id": work_item_1.id},
    )
    assert r_apply.status_code == 201
    steps = r_apply.json()["data"]
    assert len(steps) == 6
    step_codes = [s["step_code"] for s in steps]
    assert step_codes == ["assessment", "access", "canal_measurement", "clean_shape", "obturate", "restore"]
    assert all(s["work_item_id"] == work_item_1.id for s in steps)

    # Test unknown template -> 404
    r_unknown = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps/from-template",
        headers=headers,
        json={"template_code": "UNKNOWN_TEMPLATE"},
    )
    assert r_unknown.status_code == 404


@pytest.mark.asyncio
async def test_record_care_observation(client, seed_data, async_db_session):
    """
    G10-M07: Add observation API.
    Records structured observations (working length, canal ID, apex measurement) and preserves free notes.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    session_id = r_session.json()["data"]["id"]

    # Add a step
    r_step = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={"step_code": "canal_measurement", "title": "Canal Lengths"},
    )
    step_id = r_step.json()["data"]["id"]

    # Record observation on step
    r_obs = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/observations",
        headers=headers,
        json={
            "observation_code": "working_length",
            "step_id": step_id,
            "tooth_key": "46",
            "root_id": "M",
            "canal_id": "MB",
            "structured_value": {"length_mm": 21.5, "maf": 25, "reference_point": "mesiobuccal cusp"},
            "notes": "Good apical tugback",
        },
    )
    assert r_obs.status_code == 201
    obs_data = r_obs.json()["data"]
    assert obs_data["observation_code"] == "working_length"
    assert obs_data["tooth_key"] == "46"
    assert obs_data["root_id"] == "M"
    assert obs_data["canal_id"] == "MB"
    assert obs_data["structured_value"]["length_mm"] == 21.5
    assert obs_data["notes"] == "Good apical tugback"
    assert obs_data["recorded_by_user_id"] == doctor_1.id

    # List observations for session
    r_list = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/observations",
        headers=headers,
    )
    assert r_list.status_code == 200
    assert len(r_list.json()["data"]) == 1

    # Filter by step_id
    r_list_step = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/observations?step_id={step_id}",
        headers=headers,
    )
    assert r_list_step.status_code == 200
    assert len(r_list_step.json()["data"]) == 1


@pytest.mark.asyncio
async def test_observation_invalid_tooth_key(client, seed_data, async_db_session):
    """Observation with invalid non-FDI tooth key returns 422."""
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    session_id = r_session.json()["data"]["id"]

    r_obs = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/observations",
        headers=headers,
        json={
            "observation_code": "color_shade",
            "tooth_key": "99",  # Invalid tooth key
        },
    )
    assert r_obs.status_code == 422
    assert "invalid tooth key" in r_obs.json()["detail"].lower()


@pytest.mark.asyncio
async def test_observation_cross_session_step_rejected(client, seed_data, async_db_session):
    """
    Attempting to associate an observation with a step from another care session
    returns 404 (preventing violation of trigger trg_co_step_care_session_match).
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    # Session 1 with Step 1
    r_s1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    s1_id = r_s1.json()["data"]["id"]
    r_step1 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s1_id}/steps",
        headers=headers,
        json={"step_code": "s1_step", "title": "Step from Session 1"},
    )
    s1_step_id = r_step1.json()["data"]["id"]

    # Finish Session 1 and start Session 2
    client.post(f"/api/v1/patients/{patient_1.id}/care-sessions/{s1_id}/finish", headers=headers, json={})
    r_s2 = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={},
    )
    s2_id = r_s2.json()["data"]["id"]

    # Try to add observation to Session 2 referencing step from Session 1 -> 404
    r_obs = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{s2_id}/observations",
        headers=headers,
        json={
            "observation_code": "cross_session_test",
            "step_id": s1_step_id,
        },
    )
    assert r_obs.status_code == 404
    assert "step not found" in r_obs.json()["detail"].lower()


@pytest.mark.asyncio
async def test_finalization_audit_trail(client, seed_data, async_db_session):
    """
    G10-M17: Add finalization audit trail.
    Finishing a care session logs an AuditLog row via log_admin_action AND an append-only ClinicalEvent.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Finalization audit test session"},
    )
    session_id = r_session.json()["data"]["id"]

    r_finish = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/finish",
        headers=headers,
        json={"notes": "Completed with all canals obturated"},
    )
    assert r_finish.status_code == 200

    # 1. Verify AuditLog written
    stmt_audit = select(models.AuditLog).where(
        models.AuditLog.entity_id == session_id,
        models.AuditLog.action == "FINISH_CARE_SESSION",
        models.AuditLog.entity_type == "care_session",
    )
    audit_log = (await async_db_session.execute(stmt_audit)).scalars().first()
    assert audit_log is not None
    assert audit_log.performed_by_id == doctor_1.id
    assert audit_log.tenant_id == doctor_1.tenant_id

    # 2. Verify ClinicalEvent written
    stmt_event = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == session_id,
        models.ClinicalEvent.event_type == "care_session_finished",
    )
    event = (await async_db_session.execute(stmt_event)).scalars().first()
    assert event is not None
    assert event.payload["status"] == "completed"


@pytest.mark.asyncio
async def test_eager_loaded_session_with_steps_and_observations(client, seed_data, async_db_session):
    """
    GET /care-sessions/{session_id} returns session with eager-loaded steps and observations.
    """
    doctor_1 = seed_data["doctor_1"]
    patient_1 = seed_data["patient_1"]
    headers = make_headers(doctor_1)

    await set_native_writes_flag(async_db_session, doctor_1.tenant_id, True)

    r_session = client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions",
        headers=headers,
        json={"notes": "Full session"},
    )
    session_id = r_session.json()["data"]["id"]

    # Add step
    client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/steps",
        headers=headers,
        json={"step_code": "step1", "title": "Step 1"},
    )

    # Add observation
    client.post(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}/observations",
        headers=headers,
        json={"observation_code": "obs1", "tooth_key": "11"},
    )

    # Retrieve session details
    r_get = client.get(
        f"/api/v1/patients/{patient_1.id}/care-sessions/{session_id}",
        headers=headers,
    )
    assert r_get.status_code == 200
    data = r_get.json()["data"]
    assert len(data["steps"]) == 1
    assert data["steps"][0]["step_code"] == "step1"
    assert len(data["observations"]) == 1
    assert data["observations"][0]["observation_code"] == "obs1"
