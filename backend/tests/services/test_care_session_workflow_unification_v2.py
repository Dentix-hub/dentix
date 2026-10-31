"""
Comprehensive Verification Tests for DENTIX Care Session Workflow Unification (Part 2).
Covers:
1. Generic visit workspace & snapshot association for non-RCT procedures
2. Workflow template CRUD, custom fields, immutability & versioning
3. Adding and removing procedures in an active care session
4. Retrospective historical care sessions (validation & isolation)
5. Observation amendments with traceable audit & supersession
6. Follow-up dashboard KPI counts, categories (overdue/upcoming/unscheduled), and filters
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend import models, schemas
from backend.services.care_session_service import CareSessionService
from backend.services.workflow_template_service import WorkflowTemplateService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService


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


@pytest.fixture
async def setup_env(async_db_session):
    tenant = models.Tenant(name="Apex Dental Clinic", domain="apex.example.com", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    doctor1 = models.User(
        tenant_id=tenant.id,
        username="dr_sarah",
        email="sarah@apex.com",
        hashed_password="hashed-password",
        role="doctor",
        is_active=True,
    )
    doctor2 = models.User(
        tenant_id=tenant.id,
        username="dr_james",
        email="james@apex.com",
        hashed_password="hashed-password",
        role="doctor",
        is_active=True,
    )
    async_db_session.add_all([doctor1, doctor2])
    await async_db_session.flush()

    patient1 = models.Patient(
        tenant_id=tenant.id,
        name="Amira Hassan",
        age=29,
        phone="+201001234567",
        assigned_doctor_id=doctor1.id,
        is_deleted=False,
    )
    patient2 = models.Patient(
        tenant_id=tenant.id,
        name="Khaled Omar",
        age=45,
        phone="+201009876543",
        assigned_doctor_id=doctor2.id,
        is_deleted=False,
    )
    async_db_session.add_all([patient1, patient2])
    await async_db_session.flush()

    # Enable native writes
    await set_native_writes_flag(async_db_session, tenant.id, True)

    return {
        "tenant": tenant,
        "doctor1": doctor1,
        "doctor2": doctor2,
        "patient1": patient1,
        "patient2": patient2,
    }


@pytest.mark.asyncio
async def test_workflow_template_crud_versioning_and_validation(async_db_session, setup_env):
    """
    Verifies Requirement 2:
    - Template creation with custom fields and ordered steps
    - Validation prevents duplicate codes and script injection
    - Editing creates an incremented version (immutability)
    - Status toggle (active/inactive)
    """
    tenant = setup_env["tenant"]
    doctor = setup_env["doctor1"]

    service = WorkflowTemplateService(async_db_session, tenant.id, doctor)

    # 1. Validation: script injection rejection
    with pytest.raises(Exception):
        schemas.WorkflowFieldSchema(
            field_id="shade",
            label="<script>alert(1)</script>",
            field_type="text",
        )

    # 2. Validation: duplicate field keys rejected
    with pytest.raises(Exception):
        schemas.WorkflowTemplateDefinitionPayload(
            steps=[schemas.WorkflowStepSchema(step_code="prep", title="Tooth Preparation", step_order=1)],
            custom_fields=[
                schemas.WorkflowFieldSchema(field_id="depth", label="Depth 1", field_type="number"),
                schemas.WorkflowFieldSchema(field_id="depth", label="Depth 2", field_type="number"),
            ],
        )

    # 3. Create Template
    create_payload = schemas.WorkflowTemplateCreate(
        template_code="REST_COMPOSITE_CUSTOM",
        procedure_code="REST_COMPOSITE",
        title="Custom Composite Restoration Protocol",
        description="Standard clinic protocol for direct composite",
        definition=schemas.WorkflowTemplateDefinitionPayload(
            steps=[
                schemas.WorkflowStepSchema(step_code="anesthesia", title="Local Anesthesia", step_order=1),
                schemas.WorkflowStepSchema(step_code="isolation", title="Rubber Dam Isolation", step_order=2),
                schemas.WorkflowStepSchema(step_code="etch_bond", title="Etch & Bond Application", step_order=3),
                schemas.WorkflowStepSchema(step_code="layering", title="Incremental Composite Layering", step_order=4),
                schemas.WorkflowStepSchema(step_code="finishing", title="Finishing & Polishing", step_order=5),
            ],
            custom_fields=[
                schemas.WorkflowFieldSchema(field_id="shade", label="Composite Shade", field_type="text", is_required=True),
                schemas.WorkflowFieldSchema(field_id="etch_time", label="Etching Time", field_type="number", unit="sec"),
                schemas.WorkflowFieldSchema(
                    field_id="curing_light",
                    label="Curing Device",
                    field_type="choice",
                    choices=["Valo Cordless", "3M Elipar", "Standard LED"],
                ),
            ],
        ),
    )

    created = await service.create_template(create_payload)
    assert created.id is not None
    assert created.version == 1
    assert created.is_active is True
    assert len(created.definition.get("steps", [])) == 5
    assert len(created.definition.get("custom_fields", [])) == 3

    # 4. Update Template -> creates version 2
    update_payload = schemas.WorkflowTemplateUpdate(
        title="Updated Composite Restoration Protocol v2",
        definition=schemas.WorkflowTemplateDefinitionPayload(
            steps=[
                schemas.WorkflowStepSchema(step_code="anesthesia", title="Local Anesthesia", step_order=1),
                schemas.WorkflowStepSchema(step_code="isolation", title="Rubber Dam Isolation", step_order=2),
                schemas.WorkflowStepSchema(step_code="etch_bond", title="Etch & Bond Application", step_order=3),
                schemas.WorkflowStepSchema(step_code="matrix", title="Sectional Matrix Placement", step_order=4),
                schemas.WorkflowStepSchema(step_code="layering", title="Incremental Composite Layering", step_order=5),
                schemas.WorkflowStepSchema(step_code="finishing", title="Finishing & Polishing", step_order=6),
            ],
            custom_fields=create_payload.definition.custom_fields,
        ),
    )

    updated = await service.update_template(created.template_code, update_payload)
    assert updated.version == 2
    assert updated.title == "Updated Composite Restoration Protocol v2"
    assert len(updated.definition.get("steps", [])) == 6

    # 5. Status toggle
    toggled = await service.set_active_status(updated.id, is_active=False)
    assert toggled.is_active is False


@pytest.mark.asyncio
async def test_care_session_generic_workspace_and_snapshot_association(async_db_session, setup_env):
    """
    Verifies Requirement 1 & 3:
    - Multi-procedure care session starts with populated template snapshot
    - Non-RCT procedures (e.g. SURG_EXTRACTION) get their canonical custom fields
    - Adding and removing procedures in active session
    - Guard prevents removing a procedure that has documented steps
    """
    tenant = setup_env["tenant"]
    doctor = setup_env["doctor1"]
    patient = setup_env["patient1"]

    service = CareSessionService(async_db_session, tenant.id, doctor)

    wi_ext = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="SURG_EXTRACTION",
        status="active",
        created_by_user_id=doctor.id,
    )
    wi_comp = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add_all([wi_ext, wi_comp])
    await async_db_session.flush()

    # Start session with Extraction procedure
    session_payload = schemas.CareSessionCreate(
        work_item_ids=[wi_ext.id],
    )
    session = await service.start_session(patient.id, session_payload)
    assert session.status == "in_progress"
    assert len(session.procedures) == 1

    proc_ext = session.procedures[0]
    assert proc_ext.work_item_id == wi_ext.id
    assert proc_ext.template_snapshot is not None
    # Template snapshot must have custom fields from SURG_EXTRACTION canonical template
    custom_fields = proc_ext.template_snapshot.get("custom_fields", [])
    assert any(f["field_id"] == "anesthesia" for f in custom_fields)
    assert any(f["field_id"] == "suture_type" for f in custom_fields)

    # Add second procedure (REST_COMPOSITE) to the active session
    proc_comp = await service.add_procedure_to_session(patient.id, session.id, wi_comp.id)
    assert proc_comp.work_item_id == wi_comp.id
    assert proc_comp.template_snapshot is not None
    comp_custom_fields = proc_comp.template_snapshot.get("custom_fields", [])
    assert any(f["field_id"] == "cavity_class" for f in comp_custom_fields)
    assert any(f["field_id"] == "shade" for f in comp_custom_fields)

    session_after_add = await service.get_session(patient.id, session.id)
    assert len(session_after_add.procedures) == 2

    # Document a step for Extraction
    step = models.CareSessionStep(
        tenant_id=tenant.id,
        care_session_id=session.id,
        work_item_id=wi_ext.id,
        step_code="surg_luxation",
        title="Elevator Luxation",
        status="completed",
        step_order=1,
    )
    async_db_session.add(step)
    await async_db_session.flush()

    # Guard: Attempting to remove procedure with documented work must fail (400)
    with pytest.raises(HTTPException) as exc_info:
        await service.remove_procedure_from_session(patient.id, session.id, wi_ext.id)
    assert exc_info.value.status_code == 400
    assert "documented clinical work" in str(exc_info.value.detail)

    # Removing REST_COMPOSITE (no documented work) succeeds
    removed = await service.remove_procedure_from_session(patient.id, session.id, wi_comp.id)
    assert removed is True
    session_after_remove = await service.get_session(patient.id, session.id)
    assert len(session_after_remove.procedures) == 1
    assert session_after_remove.procedures[0].work_item_id == wi_ext.id

    # Update procedure-scoped notes and next action
    proc_update_payload = schemas.CareSessionProcedureUpdate(
        procedure_notes="Patient tolerated extraction well under local anesthesia.",
        next_action="Suture removal in 7 days",
    )
    updated_proc = await service.update_session_procedure(patient.id, session.id, wi_ext.id, proc_update_payload)
    assert updated_proc.procedure_notes == "Patient tolerated extraction well under local anesthesia."
    assert updated_proc.next_action == "Suture removal in 7 days"


@pytest.mark.asyncio
async def test_historical_care_session_validation_and_isolation(async_db_session, setup_env):
    """
    Verifies Requirement 4:
    - Retrospective historical care sessions record actual_visit_date
    - Marked is_historical=True and created directly in completed status
    - Does not create or conflict with active chairside sessions
    - Future actual_visit_date is rejected with 422
    """
    tenant = setup_env["tenant"]
    doctor = setup_env["doctor1"]
    patient = setup_env["patient1"]

    service = CareSessionService(async_db_session, tenant.id, doctor)

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    # 1. Reject future visit date
    future_payload = schemas.CareSessionCreate(
        is_historical=True,
        actual_visit_date=tomorrow,
    )
    with pytest.raises(HTTPException) as exc:
        await service.start_session(patient.id, future_payload)
    assert exc.value.status_code == 422

    # 2. Record legitimate past visit
    historical_payload = schemas.CareSessionCreate(
        is_historical=True,
        actual_visit_date=yesterday,
        notes="Historical record of treatment done at previous clinic",
    )
    historical_session = await service.start_session(patient.id, historical_payload)
    assert historical_session.is_historical is True
    assert historical_session.status == "completed"
    actual_dt = historical_session.actual_visit_date
    if actual_dt.tzinfo is None:
        actual_dt = actual_dt.replace(tzinfo=timezone.utc)
    assert actual_dt == yesterday

    # 3. No active session conflict: Starting a live session still succeeds
    live_payload = schemas.CareSessionCreate()
    live_session = await service.start_session(patient.id, live_payload)
    assert live_session.status == "in_progress"
    assert live_session.is_historical is False


@pytest.mark.asyncio
async def test_care_observation_amendment(async_db_session, setup_env):
    """
    Verifies Requirement 4:
    - Traceable amendment of chairside observation
    - Superseded row preserved with is_superseded=True, superseded_by_id, and amendment_reason
    - Cannot amend an already superseded observation
    """
    tenant = setup_env["tenant"]
    doctor = setup_env["doctor1"]
    patient = setup_env["patient1"]

    service = CareSessionService(async_db_session, tenant.id, doctor)

    session = await service.start_session(patient.id, schemas.CareSessionCreate())

    # Record original observation
    orig_payload = schemas.CareObservationCreate(
        observation_code="canal_length",
        tooth_key="16",
        canal_id="MB1",
        structured_value={"length_mm": 20.0, "maf": "25"},
        notes="Initial apex locator reading",
    )
    orig_obs = await service.add_observation(patient.id, session.id, orig_payload)
    assert orig_obs.is_superseded is False

    # Amend observation
    amend_payload = schemas.CareObservationAmend(
        reason="Re-measured after curvature negotiation; apex locator indicates 21.0mm",
        structured_value={"length_mm": 21.0, "maf": "30"},
        notes="Apex re-confirmed with radiograph",
    )
    new_obs = await service.amend_observation(patient.id, orig_obs.id, amend_payload)

    assert new_obs.id != orig_obs.id
    assert new_obs.structured_value["length_mm"] == 21.0
    assert new_obs.structured_value["maf"] == "30"
    assert new_obs.amendment_reason == amend_payload.reason

    # Verify original observation is marked superseded
    await async_db_session.refresh(orig_obs)
    assert orig_obs.is_superseded is True
    assert orig_obs.superseded_by_id == new_obs.id
    assert orig_obs.amendment_reason == amend_payload.reason

    # Attempting to amend the already superseded row raises 409 Conflict
    with pytest.raises(HTTPException) as exc:
        await service.amend_observation(patient.id, orig_obs.id, amend_payload)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_follow_up_dashboard_metrics_and_filters(async_db_session, setup_env):
    """
    Verifies Requirement 5:
    - Overdue vs upcoming vs unscheduled follow-up classification
    - Accurate total and KPI metrics
    - Filtering by due category, doctor, status, and patient search
    """
    tenant = setup_env["tenant"]
    doctor1 = setup_env["doctor1"]
    doctor2 = setup_env["doctor2"]
    patient1 = setup_env["patient1"]
    patient2 = setup_env["patient2"]

    service = CareSessionService(async_db_session, tenant.id, doctor1)

    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=3)
    future_due = now + timedelta(days=5)

    # 1. Overdue request for patient1 assigned to doctor1
    req_overdue = models.NextVisitRequest(
        tenant_id=tenant.id,
        patient_id=patient1.id,
        status="requested",
        reason="Crown fitting step 2",
        preferred_time_window_start=past_due,
        assigned_doctor_id=doctor1.id,
        suggested_duration_minutes=45,
    )
    # 2. Upcoming request for patient2 assigned to doctor2
    req_upcoming = models.NextVisitRequest(
        tenant_id=tenant.id,
        patient_id=patient2.id,
        status="requested",
        reason="Suture removal and healing check",
        preferred_time_window_start=future_due,
        assigned_doctor_id=doctor2.id,
        suggested_duration_minutes=15,
    )
    # 3. Unscheduled request (no target date)
    req_unscheduled = models.NextVisitRequest(
        tenant_id=tenant.id,
        patient_id=patient1.id,
        status="requested",
        reason="Routine prophylaxis follow-up",
        assigned_doctor_id=doctor1.id,
        suggested_duration_minutes=30,
    )
    # 4. Postponed request
    req_postponed = models.NextVisitRequest(
        tenant_id=tenant.id,
        patient_id=patient2.id,
        status="postponed",
        reason="Delayed by patient travel",
        postponed_to_date=future_due + timedelta(days=10),
        assigned_doctor_id=doctor2.id,
        suggested_duration_minutes=30,
    )
    async_db_session.add_all([req_overdue, req_upcoming, req_unscheduled, req_postponed])
    await async_db_session.flush()

    # Query Dashboard with no filters
    dash = await service.get_follow_up_dashboard()
    assert dash.counts.total == 4
    assert dash.counts.overdue == 1
    assert dash.counts.upcoming == 2
    assert dash.counts.unscheduled == 1
    assert dash.counts.postponed == 1

    # Filter by due_category="overdue"
    dash_overdue = await service.get_follow_up_dashboard(due_category="overdue")
    assert len(dash_overdue.items) == 1
    assert dash_overdue.items[0].id == req_overdue.id
    assert dash_overdue.items[0].due_category == "overdue"

    # Filter by doctor_id
    dash_doc2 = await service.get_follow_up_dashboard(doctor_id=doctor2.id)
    assert len(dash_doc2.items) == 2
    assert all(item.assigned_doctor_id == doctor2.id for item in dash_doc2.items)

    # Filter by search string "Suture"
    dash_search = await service.get_follow_up_dashboard(search="Suture")
    assert len(dash_search.items) == 1
    assert dash_search.items[0].id == req_upcoming.id
