"""
Care Session Appointment Integration & Next-Visit Request Tests (Slice S22 / G11).

Covers:
- G11-M01: Link session to appointment
- G11-M02: Add next-visit request creation
- G11-M06: Populate appointment reason
- G11-M07: Suggest duration
- G11-M08: Prevent auto-booking without user action (Architectural Invariant)
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend import models, schemas
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService


@pytest.fixture
async def seed_data(async_db_session):
    """Seed tenants, doctors, patients, appointments, and feature flags."""
    tenant_1 = models.Tenant(name="Apex Dental Clinic", domain="apex.example.com", is_active=True)
    tenant_2 = models.Tenant(name="Other Clinic", domain="other.example.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="dr_apex",
        email="doctor@apex.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="dr_other",
        email="doctor@other.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    async_db_session.add_all([doctor_1, doctor_2])
    await async_db_session.flush()

    patient_1 = models.Patient(
        tenant_id=tenant_1.id,
        name="Tariq Ali",
        age=35,
        phone="+966500000001",
        medical_history="No systemic allergies",
        notes="Root canal therapy required on Tooth 46",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_2 = models.Patient(
        tenant_id=tenant_2.id,
        name="External Patient",
        age=40,
        phone="+966500000002",
        medical_history="No history",
        notes="Patient 2 notes",
        assigned_doctor_id=doctor_2.id,
        is_deleted=False,
    )
    patient_3 = models.Patient(
        tenant_id=tenant_1.id,
        name="Patient Three (Same Tenant)",
        age=28,
        phone="+966500000003",
        medical_history="None",
        notes="Patient 3 notes",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    async_db_session.add_all([patient_1, patient_2, patient_3])
    await async_db_session.flush()

    # Create appointments
    now = datetime.now(timezone.utc)
    appt_1 = models.Appointment(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        doctor_id=doctor_1.id,
        date_time=now,
        duration_minutes=45,
        status="In_Progress",
        notes="Session 1 Root canal",
    )
    appt_2 = models.Appointment(
        tenant_id=tenant_2.id,
        patient_id=patient_2.id,
        doctor_id=doctor_2.id,
        date_time=now + timedelta(days=1),
        duration_minutes=30,
        status="Scheduled",
        notes="Tenant 2 Appointment",
    )
    appt_3 = models.Appointment(
        tenant_id=tenant_1.id,
        patient_id=patient_3.id,
        doctor_id=doctor_1.id,
        date_time=now + timedelta(days=2),
        duration_minutes=30,
        status="Scheduled",
        notes="Patient 3 Appointment",
    )
    async_db_session.add_all([appt_1, appt_2, appt_3])
    await async_db_session.flush()

    # Ensure FeatureFlag exists and enable for tenant 1
    stmt = select(models.FeatureFlag).where(
        models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES
    )
    flag = (await async_db_session.execute(stmt)).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Clinical native writes",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        async_db_session.add(flag)
        await async_db_session.commit()
        await async_db_session.refresh(flag)

    await FeatureFlagService.set_tenant_override(
        async_db_session, tenant_1.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
    )
    await async_db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "doctor_1": doctor_1,
        "doctor_2": doctor_2,
        "patient_1": patient_1,
        "patient_2": patient_2,
        "patient_3": patient_3,
        "appt_1": appt_1,
        "appt_2": appt_2,
        "appt_3": appt_3,
    }


@pytest.mark.asyncio
async def test_link_care_session_to_appointment(async_db_session, seed_data):
    """
    Test G11-M01: Link session to appointment.
    Verifies linking on creation, linking/unlinking existing session, audit logging,
    and tenant/patient boundary enforcement.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    appt1 = seed_data["appt_1"]
    appt2 = seed_data["appt_2"]
    appt3 = seed_data["appt_3"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    # 1. Start care session linked directly to appt1
    session = await service.start_session(
        pat1.id,
        schemas.CareSessionCreate(
            appointment_id=appt1.id,
            notes="Session linked to appointment at start",
        ),
    )
    assert session.id is not None
    assert session.appointment_id == appt1.id

    # 2. Unlink appointment from session
    unlinked_session = await service.link_appointment(pat1.id, session.id, None)
    assert unlinked_session.appointment_id is None

    # 3. Re-link appointment to session
    relinked_session = await service.link_appointment(pat1.id, session.id, appt1.id)
    assert relinked_session.appointment_id == appt1.id

    # 4. Verify ClinicalEvents were emitted
    events = (
        await async_db_session.execute(
            select(models.ClinicalEvent)
            .where(
                models.ClinicalEvent.tenant_id == t1.id,
                models.ClinicalEvent.patient_id == pat1.id,
                models.ClinicalEvent.care_session_id == session.id,
            )
            .order_by(models.ClinicalEvent.occurred_at.asc())
        )
    ).scalars().all()

    event_types = [e.event_type for e in events]
    assert "care_session_started" in event_types
    assert "care_session_unlinked_appointment" in event_types
    assert "care_session_linked_appointment" in event_types

    # 5. Cross-tenant isolation check: Attempting to link appointment from tenant 2
    with pytest.raises(HTTPException) as exc_tenant:
        await service.link_appointment(pat1.id, session.id, appt2.id)
    assert exc_tenant.value.status_code == 404

    # 6. Cross-patient isolation check: Attempting to link appointment belonging to another patient (pat3)
    with pytest.raises(HTTPException) as exc_patient:
        await service.link_appointment(pat1.id, session.id, appt3.id)
    assert exc_patient.value.status_code == 404


@pytest.mark.asyncio
async def test_create_next_visit_request_standalone(async_db_session, seed_data):
    """
    Test G11-M02: Add next-visit request creation (standalone chairside).
    Verifies creation, field defaults, tenant isolation, and audit events.
    """
    t1 = seed_data["tenant_1"]
    t2 = seed_data["tenant_2"]
    doc1 = seed_data["doctor_1"]
    doc2 = seed_data["doctor_2"]
    pat1 = seed_data["patient_1"]
    pat2 = seed_data["patient_2"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    # Create a work item
    wi = models.ClinicalWorkItem(
        tenant_id=t1.id,
        patient_id=pat1.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    wi_target = models.ClinicalWorkItemTarget(
        tenant_id=t1.id,
        work_item_id=wi.id,
        target_kind="tooth",
        tooth_key="46",
    )
    async_db_session.add(wi_target)
    await async_db_session.commit()

    # Start session
    session = await service.start_session(
        pat1.id,
        schemas.CareSessionCreate(notes="RCT Session 1"),
    )

    # Create next visit request
    req = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            care_session_id=session.id,
            work_item_id=wi.id,
            reason="Tooth 46: Root Canal Treatment - Obturation",
            suggested_duration_minutes=45,
            notes="Check patient tolerance, prep for gutta-percha obturation",
        ),
        session_id=session.id,
    )

    assert req.id is not None
    assert req.tenant_id == t1.id
    assert req.patient_id == pat1.id
    assert req.care_session_id == session.id
    assert req.work_item_id == wi.id
    assert req.requested_by_user_id == doc1.id
    assert req.reason == "Tooth 46: Root Canal Treatment - Obturation"
    assert req.suggested_duration_minutes == 45
    assert req.status == "requested"
    assert req.notes == "Check patient tolerance, prep for gutta-percha obturation"

    # Query list
    requests = await service.list_next_visit_requests(pat1.id, session_id=session.id)
    assert len(requests) == 1
    assert requests[0].id == req.id

    # Retrieve single
    fetched = await service.get_next_visit_request(pat1.id, req.id)
    assert fetched.id == req.id

    # Cross-tenant query should fail with 404
    service_t2 = CareSessionService(async_db_session, t2.id, doc2)
    with pytest.raises(HTTPException) as exc_t2:
        await service_t2.get_next_visit_request(pat2.id, req.id)
    assert exc_t2.value.status_code == 404


@pytest.mark.asyncio
async def test_next_visit_request_in_finish_session(async_db_session, seed_data):
    """
    Test G11-M02 & G11-M06: Next-visit request creation directly within finish_session.
    Verifies that finishing a session can simultaneously queue a next-visit request
    for reception with auto-populated reason and duration.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    # 1. Create work item
    wi = models.ClinicalWorkItem(
        tenant_id=t1.id,
        patient_id=pat1.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    wi_target = models.ClinicalWorkItemTarget(
        tenant_id=t1.id,
        work_item_id=wi.id,
        target_kind="tooth",
        tooth_key="46",
    )
    async_db_session.add(wi_target)
    await async_db_session.commit()

    # 2. Start session and apply ENDO_RCT template
    session = await service.start_session(
        pat1.id,
        schemas.CareSessionCreate(notes="RCT Visit 1"),
    )
    steps = await service.apply_template(
        pat1.id,
        session.id,
        schemas.CareSessionTemplateApply(
            template_code="ENDO_RCT",
            work_item_id=wi.id,
        ),
    )
    assert len(steps) == 6

    # Complete first two steps: assessment, access
    await service.update_step(
        pat1.id, session.id, steps[0].id, schemas.CareSessionStepUpdate(status="completed")
    )
    await service.update_step(
        pat1.id, session.id, steps[1].id, schemas.CareSessionStepUpdate(status="completed")
    )

    # 3. Finish session with next_visit_request included (reason omitted to test auto-population)
    finished_session = await service.finish_session(
        pat1.id,
        session.id,
        schemas.CareSessionFinish(
            notes="Session 1 completed. Canals accessed and irrigated.",
            next_visit_request=schemas.NextVisitRequestCreate(
                suggested_duration_minutes=45,
                notes="Schedule within 7-10 days for canal shaping & obturation",
            ),
        ),
    )

    assert finished_session.status == "completed"
    assert len(finished_session.next_visit_requests) == 1

    nvr = finished_session.next_visit_requests[0]
    assert nvr.care_session_id == session.id
    assert nvr.status == "requested"
    assert nvr.suggested_duration_minutes == 45
    assert "Tooth 46" in nvr.reason or "Root Canal" in nvr.reason
    assert nvr.notes == "Schedule within 7-10 days for canal shaping & obturation"


@pytest.mark.asyncio
async def test_populate_appointment_reason_and_suggest_duration(async_db_session, seed_data):
    """
    Test G11-M06 & G11-M07: Auto-suggest appointment reason and duration based on workflow context.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    wi = models.ClinicalWorkItem(
        tenant_id=t1.id,
        patient_id=pat1.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    wi_target = models.ClinicalWorkItemTarget(
        tenant_id=t1.id,
        work_item_id=wi.id,
        target_kind="tooth",
        tooth_key="46",
    )
    async_db_session.add(wi_target)
    await async_db_session.commit()

    session = await service.start_session(
        pat1.id,
        schemas.CareSessionCreate(notes="RCT Visit 1"),
    )
    steps = await service.apply_template(
        pat1.id,
        session.id,
        schemas.CareSessionTemplateApply(
            template_code="ENDO_RCT",
            work_item_id=wi.id,
        ),
    )

    # First step completed
    await service.update_step(
        pat1.id, session.id, steps[0].id, schemas.CareSessionStepUpdate(status="completed")
    )

    # Ask for suggestion
    suggestion = await service.suggest_next_visit(pat1.id, session_id=session.id)

    assert suggestion.suggested_duration_minutes == 45  # G11-M07
    assert "Tooth 46" in suggestion.reason              # G11-M06
    assert "Root Canal Treatment" in suggestion.reason  # G11-M06
    assert suggestion.next_step_title is not None
    assert suggestion.remaining_steps_count == 5


@pytest.mark.asyncio
async def test_prevent_auto_booking_without_user_action_invariant(async_db_session, seed_data):
    """
    Test G11-M08 (Architectural Invariant): Appointment integration must NEVER auto-book
    an appointment without explicit confirmed front-desk action.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    # 1. Count existing appointments for tenant 1
    stmt_count = select(func.count(models.Appointment.id)).where(
        models.Appointment.tenant_id == t1.id
    )
    initial_appt_count = (await async_db_session.execute(stmt_count)).scalar_one()

    # 2. Start session and create next-visit request
    session = await service.start_session(pat1.id, schemas.CareSessionCreate())
    req1 = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            care_session_id=session.id,
            reason="Review Visit",
            suggested_duration_minutes=30,
        ),
    )
    assert req1.status == "requested"

    # Verify ZERO appointments created
    count_after_create = (await async_db_session.execute(stmt_count)).scalar_one()
    assert count_after_create == initial_appt_count, (
        f"G11-M08 Invariant Violated: NextVisitRequest creation must not create an Appointment. "
        f"Expected {initial_appt_count}, found {count_after_create}"
    )

    # 3. Finish session with next_visit_request
    await service.finish_session(
        pat1.id,
        session.id,
        schemas.CareSessionFinish(
            notes="Session done",
            next_visit_request=schemas.NextVisitRequestCreate(
                reason="Follow-up after 14 days",
                suggested_duration_minutes=30,
            ),
        ),
    )

    # Verify STILL ZERO appointments created
    count_after_finish = (await async_db_session.execute(stmt_count)).scalar_one()
    assert count_after_finish == initial_appt_count, (
        f"G11-M08 Invariant Violated: finish_session with next_visit_request must not create an Appointment. "
        f"Expected {initial_appt_count}, found {count_after_finish}"
    )


@pytest.mark.asyncio
async def test_feature_flag_gated(async_db_session, seed_data):
    """
    Test fail-closed feature flag gate: clinical_vnext_native_writes (404 when disabled).
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    # Disable flag for tenant 1
    await FeatureFlagService.set_tenant_override(
        async_db_session, t1.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, False
    )
    await async_db_session.commit()

    service = CareSessionService(async_db_session, t1.id, doc1)

    with pytest.raises(HTTPException) as exc1:
        await service.start_session(pat1.id, schemas.CareSessionCreate())
    assert exc1.value.status_code == 404

    with pytest.raises(HTTPException) as exc2:
        await service.create_next_visit_request(
            pat1.id, schemas.NextVisitRequestCreate(reason="Test", suggested_duration_minutes=30)
        )
    assert exc2.value.status_code == 404

    with pytest.raises(HTTPException) as exc3:
        await service.suggest_next_visit(pat1.id)
    assert exc3.value.status_code == 404
