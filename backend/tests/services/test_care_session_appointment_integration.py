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


@pytest.mark.asyncio
async def test_reception_queue_retrieval_and_filtering(async_db_session, seed_data):
    """
    Test G11-M04: Reception queue retrieval, enrichment (patient name/phone), and status filtering.
    """
    t1 = seed_data["tenant_1"]
    t2 = seed_data["tenant_2"]
    doc1 = seed_data["doctor_1"]
    doc2 = seed_data["doctor_2"]
    pat1 = seed_data["patient_1"]
    pat3 = seed_data["patient_3"]
    pat2 = seed_data["patient_2"]

    service_t1 = CareSessionService(async_db_session, t1.id, doc1)
    service_t2 = CareSessionService(async_db_session, t2.id, doc2)

    # 1. Create two requests in tenant 1 for different patients
    req1 = await service_t1.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            reason="Tariq Obturation Step",
            suggested_duration_minutes=45,
            notes="Requires 45 min slot",
        ),
    )
    req2 = await service_t1.create_next_visit_request(
        pat3.id,
        schemas.NextVisitRequestCreate(
            reason="Patient Three Crown Delivery",
            suggested_duration_minutes=30,
        ),
    )

    # 2. Create one request in tenant 2
    req_t2 = await service_t2.create_next_visit_request(
        pat2.id,
        schemas.NextVisitRequestCreate(
            reason="External Clinic Followup",
            suggested_duration_minutes=20,
        ),
    )

    # 3. Retrieve reception queue for tenant 1
    queue_t1 = await service_t1.list_reception_queue(status="requested")
    t1_ids = [r.id for r in queue_t1]

    assert req1.id in t1_ids
    assert req2.id in t1_ids
    assert req_t2.id not in t1_ids, "Cross-tenant leak: tenant 2 request appeared in tenant 1 queue!"

    # Verify patient enrichment
    found_r1 = next(r for r in queue_t1 if r.id == req1.id)
    assert found_r1.patient_name == pat1.name
    assert found_r1.patient_phone == pat1.phone
    assert found_r1.suggested_duration_minutes == 45
    assert found_r1.status == "requested"

    # 4. Filter by patient
    pat1_queue = await service_t1.list_reception_queue(status="requested", patient_id=pat1.id)
    assert len(pat1_queue) == 1
    assert pat1_queue[0].id == req1.id


@pytest.mark.asyncio
async def test_convert_request_to_appointment_and_lifecycle(async_db_session, seed_data):
    """
    Test G11-M05: Convert next-visit request to appointment with explicit receptionist submission.
    Test G11-M09: Safe cancellation (reverts to 'requested').
    Test G11-M10: Safe completion (marks 'completed').
    Test G11-M11: Integration lifecycle from triage -> booking -> cancellation -> re-booking -> completion.
    """
    from backend import crud

    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    # 1. Chairside creates next-visit request
    req = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            reason="Tooth 46: RCT - Obturation & Seal",
            suggested_duration_minutes=45,
            notes="Bring pre-op radiograph",
        ),
    )
    assert req.status == "requested"
    initial_request_id = req.id

    # 2. Receptionist views queue and explicitly books an appointment (G11-M05, G11-M08)
    booking_time = datetime.now(timezone.utc) + timedelta(days=7)
    scheduled_req, appt = await service.schedule_next_visit_request(
        request_id=initial_request_id,
        data=schemas.NextVisitRequestSchedule(
            date_time=booking_time,
            doctor_id=doc1.id,
            duration_minutes=45,
            notes="Scheduled per patient phone call",
        ),
    )

    # Verify appointment was created
    assert appt.id is not None
    assert appt.patient_id == pat1.id
    assert appt.doctor_id == doc1.id
    assert appt.duration_minutes == 45
    assert appt.status == "Scheduled"

    # Verify request status updated to 'scheduled' and structured token added per PD06
    assert scheduled_req.status == "scheduled"
    assert f"[APPOINTMENT:{appt.id}]" in scheduled_req.notes
    assert scheduled_req.fulfilled_appointment_id == appt.id

    # Verify audit event emitted
    stmt_event = select(models.ClinicalEvent).where(
        models.ClinicalEvent.tenant_id == t1.id,
        models.ClinicalEvent.event_type == "next_visit_request_scheduled",
    )
    evt = (await async_db_session.execute(stmt_event)).scalars().first()
    assert evt is not None
    assert evt.payload["appointment_id"] == appt.id
    assert evt.payload["request_id"] == initial_request_id

    # 3. Patient calls to cancel the appointment -> receptionist cancels it (G11-M09)
    await crud.update_appointment_status(
        async_db_session,
        appointment_id=appt.id,
        status="Cancelled",
        tenant_id=t1.id,
    )

    # Verify request status safely reverted to 'requested' so it reappears in reception queue!
    reloaded_req = await service.get_next_visit_request(pat1.id, initial_request_id)
    assert reloaded_req.status == "requested", "Cancelled appointment must reopen NextVisitRequest to 'requested' (G11-M09)!"

    # Verify it shows up in reception pending queue again
    pending_queue = await service.list_reception_queue(status="requested")
    assert any(r.id == initial_request_id for r in pending_queue)

    # 4. Receptionist contacts patient and reschedules to a new appointment
    new_booking_time = datetime.now(timezone.utc) + timedelta(days=10)
    rescheduled_req, new_appt = await service.schedule_next_visit_request(
        request_id=initial_request_id,
        data=schemas.NextVisitRequestSchedule(
            date_time=new_booking_time,
            doctor_id=doc1.id,
            duration_minutes=45,
            notes="Rescheduled appointment",
        ),
    )
    assert rescheduled_req.status == "scheduled"
    assert f"[APPOINTMENT:{new_appt.id}]" in rescheduled_req.notes
    assert rescheduled_req.fulfilled_appointment_id == new_appt.id

    # 5. Patient attends and appointment is marked Completed (G11-M10)
    await crud.update_appointment_status(
        async_db_session,
        appointment_id=new_appt.id,
        status="Completed",
        tenant_id=t1.id,
    )

    # Verify request is now marked 'completed'
    completed_req = await service.get_next_visit_request(pat1.id, initial_request_id)
    assert completed_req.status == "completed", "Completed appointment must mark NextVisitRequest 'completed' (G11-M10)!"


@pytest.mark.asyncio
async def test_appointment_soft_delete_reopens_request(async_db_session, seed_data):
    """
    Test G11-M09: Soft-deleting an appointment safely reopens linked next-visit request.
    """
    from backend import crud

    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    req = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            reason="Check Suture Removal",
            suggested_duration_minutes=15,
        ),
    )
    scheduled_req, appt = await service.schedule_next_visit_request(
        request_id=req.id,
        data=schemas.NextVisitRequestSchedule(
            date_time=datetime.now(timezone.utc) + timedelta(days=5),
            doctor_id=doc1.id,
        ),
    )
    assert scheduled_req.status == "scheduled"

    # Delete appointment
    await crud.delete_appointment(async_db_session, appointment_id=appt.id, tenant_id=t1.id)

    # Verify request safely reopened to 'requested'
    reloaded = await service.get_next_visit_request(pat1.id, req.id)
    assert reloaded.status == "requested"


@pytest.mark.asyncio
async def test_concurrency_race_double_schedule_protection(async_db_session, seed_data):
    """
    Test G11-M12: Concurrency and race tests for request booking conversion.
    Attempting to schedule an already scheduled or cancelled request raises 409 Conflict.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    req = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            reason="Concurrent test request",
            suggested_duration_minutes=30,
        ),
    )

    # First schedule succeeds
    booking_time = datetime.now(timezone.utc) + timedelta(days=3)
    await service.schedule_next_visit_request(
        request_id=req.id,
        data=schemas.NextVisitRequestSchedule(
            date_time=booking_time,
            doctor_id=doc1.id,
        ),
    )

    # Second concurrent attempt raises 409 Conflict
    with pytest.raises(HTTPException) as exc:
        await service.schedule_next_visit_request(
            request_id=req.id,
            data=schemas.NextVisitRequestSchedule(
                date_time=booking_time + timedelta(hours=1),
                doctor_id=doc1.id,
            ),
        )
    assert exc.value.status_code == 409
    assert "Only 'requested' items can be scheduled" in exc.value.detail


@pytest.mark.asyncio
async def test_cross_tenant_isolation_and_security(async_db_session, seed_data):
    """
    Test tenant security and isolation on reception queue and conversion operations.
    """
    t1 = seed_data["tenant_1"]
    t2 = seed_data["tenant_2"]
    doc1 = seed_data["doctor_1"]
    doc2 = seed_data["doctor_2"]
    pat1 = seed_data["patient_1"]

    service_t1 = CareSessionService(async_db_session, t1.id, doc1)
    service_t2 = CareSessionService(async_db_session, t2.id, doc2)

    req_t1 = await service_t1.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(reason="Tenant 1 Request", suggested_duration_minutes=30),
    )

    # Tenant 2 attempts to schedule Tenant 1's request -> 404
    with pytest.raises(HTTPException) as exc:
        await service_t2.schedule_next_visit_request(
            request_id=req_t1.id,
            data=schemas.NextVisitRequestSchedule(
                date_time=datetime.now(timezone.utc) + timedelta(days=2),
                doctor_id=doc2.id,
            ),
        )
    assert exc.value.status_code == 404

    # Tenant 2 attempts to cancel Tenant 1's request -> 404
    with pytest.raises(HTTPException) as exc2:
        await service_t2.cancel_next_visit_request(request_id=req_t1.id)
    assert exc2.value.status_code == 404


@pytest.mark.asyncio
async def test_schedule_next_visit_request_rejects_cross_tenant_doctor_and_price_list(
    async_db_session, seed_data
):
    """F-14: doctor_id and price_list_id must belong to the same tenant (404 otherwise)."""
    t1 = seed_data["tenant_1"]
    t2 = seed_data["tenant_2"]
    doc1 = seed_data["doctor_1"]
    doc2 = seed_data["doctor_2"]
    pat1 = seed_data["patient_1"]

    service_t1 = CareSessionService(async_db_session, t1.id, doc1)

    pl_t1 = models.PriceList(tenant_id=t1.id, name="T1 Price List")
    pl_t2 = models.PriceList(tenant_id=t2.id, name="T2 Price List")
    async_db_session.add_all([pl_t1, pl_t2])
    await async_db_session.flush()

    req_1 = await service_t1.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(reason="Checkup", suggested_duration_minutes=30),
    )

    # 1. Attempt to schedule with cross-tenant doctor_id (doc2 belongs to t2) -> 404
    with pytest.raises(HTTPException) as exc_doc:
        await service_t1.schedule_next_visit_request(
            request_id=req_1.id,
            data=schemas.NextVisitRequestSchedule(
                date_time=datetime.now(timezone.utc) + timedelta(days=1),
                doctor_id=doc2.id,
            ),
        )
    assert exc_doc.value.status_code == 404
    assert "Doctor not found" in exc_doc.value.detail

    # 2. Attempt to schedule with non-existent doctor_id -> 404
    with pytest.raises(HTTPException) as exc_doc_missing:
        await service_t1.schedule_next_visit_request(
            request_id=req_1.id,
            data=schemas.NextVisitRequestSchedule(
                date_time=datetime.now(timezone.utc) + timedelta(days=1),
                doctor_id=99999999,
            ),
        )
    assert exc_doc_missing.value.status_code == 404
    assert "Doctor not found" in exc_doc_missing.value.detail

    # 3. Attempt to schedule with cross-tenant price_list_id (pl_t2 belongs to t2) -> 404
    with pytest.raises(HTTPException) as exc_pl:
        await service_t1.schedule_next_visit_request(
            request_id=req_1.id,
            data=schemas.NextVisitRequestSchedule(
                date_time=datetime.now(timezone.utc) + timedelta(days=1),
                doctor_id=doc1.id,
                price_list_id=pl_t2.id,
            ),
        )
    assert exc_pl.value.status_code == 404
    assert "Price list not found" in exc_pl.value.detail

    # 4. Attempt to schedule with non-existent price_list_id -> 404
    with pytest.raises(HTTPException) as exc_pl_missing:
        await service_t1.schedule_next_visit_request(
            request_id=req_1.id,
            data=schemas.NextVisitRequestSchedule(
                date_time=datetime.now(timezone.utc) + timedelta(days=1),
                doctor_id=doc1.id,
                price_list_id=88888888,
            ),
        )
    assert exc_pl_missing.value.status_code == 404
    assert "Price list not found" in exc_pl_missing.value.detail

    # 5. Scheduling with valid tenant-owned doctor_id and price_list_id succeeds
    req_res, appt = await service_t1.schedule_next_visit_request(
        request_id=req_1.id,
        data=schemas.NextVisitRequestSchedule(
            date_time=datetime.now(timezone.utc) + timedelta(days=1),
            doctor_id=doc1.id,
            price_list_id=pl_t1.id,
        ),
    )
    assert req_res.status == "scheduled"
    assert appt.doctor_id == doc1.id
    assert appt.price_list_id == pl_t1.id


@pytest.mark.asyncio
async def test_next_visit_requests_router_handlers(async_db_session, seed_data):
    """
    Test REST router endpoints directly:
    - GET /api/v1/next-visit-requests (G11-M04)
    - POST /api/v1/next-visit-requests/{id}/schedule (G11-M05)
    - POST /api/v1/next-visit-requests/{id}/cancel
    - GET /api/v1/next-visit-requests/{id}
    """
    from backend.routers import next_visit_requests as nvr_router

    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]

    service = CareSessionService(async_db_session, t1.id, doc1)

    # 1. Create chairside request
    req = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            reason="Router test follow-up",
            suggested_duration_minutes=30,
        ),
    )

    # 2. Test list_reception_queue router endpoint
    res_list = await nvr_router.list_reception_queue(
        status="requested",
        patient_id=None,
        skip=0,
        limit=50,
        db=async_db_session,
        current_user=doc1,
    )
    items = res_list["data"]
    assert any(r.id == req.id for r in items)
    matched = next(r for r in items if r.id == req.id)
    assert matched.patient_name == pat1.name
    assert matched.status == "requested"

    # 3. Test get_next_visit_request router endpoint
    res_get = await nvr_router.get_next_visit_request(
        request_id=req.id,
        db=async_db_session,
        current_user=doc1,
    )
    assert res_get["data"].id == req.id
    assert res_get["data"].reason == "Router test follow-up"

    # 4. Test schedule_next_visit_request router endpoint
    booking_time = datetime.now(timezone.utc) + timedelta(days=2)
    res_sched = await nvr_router.schedule_next_visit_request(
        request_id=req.id,
        payload=schemas.NextVisitRequestSchedule(
            date_time=booking_time,
            duration_minutes=30,
            notes="Booked via router endpoint",
        ),
        db=async_db_session,
        current_user=doc1,
    )
    assert res_sched["data"].status == "scheduled"
    assert res_sched["data"].appointment_id is not None
    assert res_sched["data"].request.fulfilled_appointment_id == res_sched["data"].appointment_id

    # 5. Duplicate schedule via router endpoint returns 409
    with pytest.raises(HTTPException) as exc_dup:
        await nvr_router.schedule_next_visit_request(
            request_id=req.id,
            payload=schemas.NextVisitRequestSchedule(
                date_time=booking_time,
            ),
            db=async_db_session,
            current_user=doc1,
        )
    assert exc_dup.value.status_code == 409

    # 6. Test cancel_next_visit_request router endpoint
    req2 = await service.create_next_visit_request(
        pat1.id,
        schemas.NextVisitRequestCreate(
            reason="Second request to cancel",
            suggested_duration_minutes=15,
        ),
    )
    res_cancel = await nvr_router.cancel_next_visit_request(
        request_id=req2.id,
        payload=nvr_router.CancelRequestPayload(reason="Patient moved"),
        db=async_db_session,
        current_user=doc1,
    )
    assert res_cancel["data"].status == "cancelled"
