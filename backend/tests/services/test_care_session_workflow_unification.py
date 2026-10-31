"""
Comprehensive Tests for Care Session Workflow Unification (Step 2 & Step 3).
Verifies:
1. Status-only command:
   - Transition active <-> completed
   - Pending charge creation on native completion
   - Auto-void pending charge on reopen correction
   - Invoiced charge manual review warning
   - Legacy treatment synchronization (In Progress <-> Done) without duplicate charges
   - Outstanding workflow steps override reason requirement
   - Kind guard (procedures only)
2. Identity & Continuation:
   - Defect 1: Legitimate repetitions not deduplicated by step_code
   - Defect 2: Procedure-scoped step copying (no cross-assignment)
   - Multi-procedure visit association in care_session_procedures
   - Observation reference source attribution
3. Historical visits (Defect 4):
   - actual_visit_date vs created_at
   - No conflict with active in_progress session
   - Rejection of future dates
4. Server Drafts:
   - Optimistic concurrency conflict (409)
   - Draft recovery & clearing
5. Observation Amendments:
   - Traceable supersession and linkage
6. Follow-up Lifecycle:
   - Multiple next visit requests on finish
   - Stop, postpone, resume, and handoff
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func

from backend import models, schemas
from backend.models.clinical_core import (
    CLINICAL_CHARGE_STATUS_INVOICED,
    CLINICAL_CHARGE_STATUS_PENDING,
    CLINICAL_CHARGE_STATUS_VOIDED,
)
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_command_service import ClinicalCommandService
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
async def setup_test_env(async_db_session):
    tenant = models.Tenant(name="Clinic Alpha", domain="alpha.example.com", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    doctor = models.User(
        tenant_id=tenant.id,
        username="doc_alpha",
        email="doc1@alpha.com",
        hashed_password="hashed-password",
        role="doctor",
        is_active=True,
    )
    doctor_2 = models.User(
        tenant_id=tenant.id,
        username="doc2_alpha",
        email="doc2@alpha.com",
        hashed_password="hashed-password",
        role="doctor",
        is_active=True,
    )
    async_db_session.add_all([doctor, doctor_2])
    await async_db_session.flush()

    patient = models.Patient(
        tenant_id=tenant.id,
        name="John Doe",
        age=32,
        phone="+1234567890",
        assigned_doctor_id=doctor.id,
        is_deleted=False,
    )
    async_db_session.add(patient)

    proc_rct = models.Procedure(
        tenant_id=tenant.id,
        name="ENDO_RCT",
        price=300.00,
    )
    async_db_session.add(proc_rct)
    await async_db_session.flush()

    # Enable native writes
    await set_native_writes_flag(async_db_session, tenant.id, True)

    return {
        "tenant": tenant,
        "doctor": doctor,
        "doctor_2": doctor_2,
        "patient": patient,
    }


# ---------------------------------------------------------------------------
# 1. Status-only command tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_only_update_active_to_completed_with_charge_and_audit(async_db_session, setup_test_env):
    env = setup_test_env
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    # Create procedure work item
    wi_payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
    )
    wi = await cmd_service.create_work_item(env["patient"].id, wi_payload)
    assert wi.status == "active"

    # Status update: active -> completed
    status_payload = schemas.ClinicalWorkItemStatusUpdate(
        status="completed",
        expected_version_id=wi.version_id,
        override_reason="Completed successfully",
    )
    res = await cmd_service.update_work_item_status(env["patient"].id, wi.id, status_payload)

    assert res.effective_status == "completed"
    assert res.previous_status == "active"
    assert res.work_item.status == "completed"

    # Verify event logged
    ev_stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.tenant_id == env["tenant"].id,
        models.ClinicalEvent.work_item_id == wi.id,
        models.ClinicalEvent.event_type == "procedure_status_changed",
    )
    event = (await async_db_session.execute(ev_stmt)).scalar_one()
    assert event.payload["status"] == "completed"

    # Verify pending charge was created
    charge_stmt = select(models.ClinicalCharge).where(
        models.ClinicalCharge.tenant_id == env["tenant"].id,
        models.ClinicalCharge.work_item_id == wi.id,
    )
    charge = (await async_db_session.execute(charge_stmt)).scalar_one_or_none()
    assert charge is not None
    assert charge.status == CLINICAL_CHARGE_STATUS_PENDING


@pytest.mark.asyncio
async def test_status_only_update_completed_to_active_reopen_voids_pending_charge(async_db_session, setup_test_env):
    env = setup_test_env
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    # Create active procedure
    wi_payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
    )
    wi = await cmd_service.create_work_item(env["patient"].id, wi_payload)

    # Complete it
    await cmd_service.update_work_item_status(
        env["patient"].id,
        wi.id,
        schemas.ClinicalWorkItemStatusUpdate(status="completed", override_reason="Done"),
    )

    # Verify pending charge exists
    charge_stmt = select(models.ClinicalCharge).where(
        models.ClinicalCharge.tenant_id == env["tenant"].id,
        models.ClinicalCharge.work_item_id == wi.id,
        models.ClinicalCharge.status == CLINICAL_CHARGE_STATUS_PENDING,
    )
    charge = (await async_db_session.execute(charge_stmt)).scalar_one()
    assert charge.status == CLINICAL_CHARGE_STATUS_PENDING

    # Attempt reopening without intent="reopen_correction" should fail (422)
    with pytest.raises(HTTPException) as exc_info:
        await cmd_service.update_work_item_status(
            env["patient"].id,
            wi.id,
            schemas.ClinicalWorkItemStatusUpdate(status="active", reason="Just reopening"),
        )
    assert exc_info.value.status_code == 422

    # Reopen correctly with intent="reopen_correction" and reason
    reopen_payload = schemas.ClinicalWorkItemStatusUpdate(
        status="active",
        intent="reopen_correction",
        reason="Patient reported lingering tenderness on percussion, canal needs further irrigation",
    )
    res = await cmd_service.update_work_item_status(env["patient"].id, wi.id, reopen_payload)
    assert res.effective_status == "active"

    # Pending charge must now be VOIDED
    await async_db_session.refresh(charge)
    assert charge.status == CLINICAL_CHARGE_STATUS_VOIDED
    assert "reopen" in (charge.notes or "")


@pytest.mark.asyncio
async def test_status_only_reopen_with_invoiced_charge_returns_warning(async_db_session, setup_test_env):
    env = setup_test_env
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    wi_payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
    )
    wi = await cmd_service.create_work_item(env["patient"].id, wi_payload)

    # Complete it
    await cmd_service.update_work_item_status(
        env["patient"].id,
        wi.id,
        schemas.ClinicalWorkItemStatusUpdate(status="completed", override_reason="Done"),
    )

    # Manually transition charge to invoiced
    charge_stmt = select(models.ClinicalCharge).where(
        models.ClinicalCharge.tenant_id == env["tenant"].id,
        models.ClinicalCharge.work_item_id == wi.id,
    )
    charge = (await async_db_session.execute(charge_stmt)).scalar_one()
    charge.status = CLINICAL_CHARGE_STATUS_INVOICED
    await async_db_session.commit()

    # Reopen procedure
    reopen_payload = schemas.ClinicalWorkItemStatusUpdate(
        status="active",
        intent="reopen_correction",
        reason="Incorrectly marked completed",
    )
    res = await cmd_service.update_work_item_status(env["patient"].id, wi.id, reopen_payload)

    # Charge must remain invoiced
    await async_db_session.refresh(charge)
    assert charge.status == CLINICAL_CHARGE_STATUS_INVOICED

    # Warning must be returned in response
    assert len(res.warnings) == 1
    assert res.warnings[0].code == "invoiced_charge_requires_manual_review"


@pytest.mark.asyncio
async def test_status_only_legacy_treatment_synchronization(async_db_session, setup_test_env):
    env = setup_test_env
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    # Create legacy treatment
    legacy_tx = models.Treatment(
        tenant_id=env["tenant"].id,
        patient_id=env["patient"].id,
        doctor_id=env["doctor"].id,
        procedure="ENDO_RCT",
        tooth_number=16,
        status="In Progress",
        cost=Decimal("500.00"),
    )
    async_db_session.add(legacy_tx)
    await async_db_session.flush()

    # Create native work item linked via event payload
    wi_payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
    )
    wi = await cmd_service.create_work_item(env["patient"].id, wi_payload)

    # Record linking event
    link_ev = models.ClinicalEvent(
        tenant_id=env["tenant"].id,
        patient_id=env["patient"].id,
        work_item_id=wi.id,
        event_type="legacy_sync",
        occurred_at=datetime.now(timezone.utc),
        payload={"legacy_treatment_id": legacy_tx.id},
    )
    async_db_session.add(link_ev)
    await async_db_session.commit()

    # Complete via status shortcut
    res = await cmd_service.update_work_item_status(
        env["patient"].id,
        wi.id,
        schemas.ClinicalWorkItemStatusUpdate(status="completed", override_reason="Done"),
    )
    assert res.effective_status == "completed"
    assert res.legacy_treatment_id == legacy_tx.id
    assert res.legacy_treatment_status == "Done"

    # Legacy treatment must be 'Done'
    await async_db_session.refresh(legacy_tx)
    assert legacy_tx.status == "Done"

    # Must NOT create duplicate clinical charges for legacy-linked procedures
    charge_stmt = select(models.ClinicalCharge).where(
        models.ClinicalCharge.tenant_id == env["tenant"].id,
        models.ClinicalCharge.work_item_id == wi.id,
    )
    charges = (await async_db_session.execute(charge_stmt)).scalars().all()
    assert len(charges) == 0

    # Reopen via status shortcut
    reopen_res = await cmd_service.update_work_item_status(
        env["patient"].id,
        wi.id,
        schemas.ClinicalWorkItemStatusUpdate(
            status="active",
            intent="reopen_correction",
            reason="Additional canal discovered",
        ),
    )
    assert reopen_res.effective_status == "active"
    assert reopen_res.legacy_treatment_status == "In Progress"

    await async_db_session.refresh(legacy_tx)
    assert legacy_tx.status == "In Progress"


@pytest.mark.asyncio
async def test_status_only_requires_override_reason_when_steps_outstanding(async_db_session, setup_test_env):
    env = setup_test_env
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])

    wi_payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
    )
    wi = await cmd_service.create_work_item(env["patient"].id, wi_payload)

    # Start session and add pending step
    session = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(work_item_ids=[wi.id]),
    )
    await care_service.add_step(
        env["patient"].id,
        session.id,
        schemas.CareSessionStepCreate(
            step_code="obturation",
            title="Canal Obturation",
            work_item_id=wi.id,
            status="pending",
        ),
    )

    # Attempting to complete procedure without override reason must fail (422)
    with pytest.raises(HTTPException) as exc_info:
        await cmd_service.update_work_item_status(
            env["patient"].id,
            wi.id,
            schemas.ClinicalWorkItemStatusUpdate(status="completed"),
        )
    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    if isinstance(detail, dict):
        assert detail.get("code") == "OVERRIDE_REASON_REQUIRED"
        assert "outstanding workflow step" in detail.get("message", "")
    else:
        assert "outstanding workflow step" in str(detail)

    # Providing override reason succeeds
    res = await cmd_service.update_work_item_status(
        env["patient"].id,
        wi.id,
        schemas.ClinicalWorkItemStatusUpdate(
            status="completed",
            override_reason="Obturation completed using alternate technique",
        ),
    )
    assert res.effective_status == "completed"


@pytest.mark.asyncio
async def test_status_only_forbidden_for_finding(async_db_session, setup_test_env):
    env = setup_test_env
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    wi = await cmd_service.create_work_item(
        env["patient"].id,
        schemas.ClinicalWorkItemCreate(
            kind="finding",
            code="CARIES",
            status="proposed",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await cmd_service.update_work_item_status(
            env["patient"].id,
            wi.id,
            schemas.ClinicalWorkItemStatusUpdate(status="active"),
        )
    assert exc_info.value.status_code == 422
    assert "only supported for procedures" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 2. Defect 1 & Defect 2 Continuation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_defect_1_repetition_preservation_not_deduplicated_by_step_code(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    wi = await cmd_service.create_work_item(
        env["patient"].id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="ENDO_RCT",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
        ),
    )

    # First session has multiple steps with SAME step_code
    session_1 = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(work_item_ids=[wi.id]),
    )
    await care_service.add_step(
        env["patient"].id,
        session_1.id,
        schemas.CareSessionStepCreate(
            step_code="irrigation",
            title="Initial NaOCl Irrigation",
            work_item_id=wi.id,
            status="pending",
        ),
    )
    await care_service.add_step(
        env["patient"].id,
        session_1.id,
        schemas.CareSessionStepCreate(
            step_code="irrigation",
            title="Ultrasonic Activation & Final Rinse",
            work_item_id=wi.id,
            status="pending",
        ),
    )
    await care_service.finish_session(
        env["patient"].id,
        session_1.id,
        schemas.CareSessionFinish(notes="Session 1 completed"),
    )

    # Start Session 2 resuming wi.id
    session_2 = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(
            work_item_ids=[wi.id],
            resume_from_session_id=session_1.id,
        ),
    )

    # Defect 1 check: Both irrigation steps MUST be carried over!
    session_2_steps = session_2.steps
    irrigation_steps = [s for s in session_2_steps if s.step_code == "irrigation"]
    assert len(irrigation_steps) == 2, f"Expected 2 irrigation steps, found {len(irrigation_steps)} (Defect 1 regression)"


@pytest.mark.asyncio
async def test_defect_2_procedure_scoped_step_copying_no_cross_assignment(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    # Create two procedures: RCT on tooth 16, Filling on tooth 24
    wi_rct = await cmd_service.create_work_item(
        env["patient"].id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="ENDO_RCT",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
        ),
    )
    wi_fill = await cmd_service.create_work_item(
        env["patient"].id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="REST_COMPOSITE",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="surface", tooth_key="24", surface_code="O")],
        ),
    )

    # Session 1: Documents work on BOTH procedures in one visit
    session_1 = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(work_item_ids=[wi_rct.id, wi_fill.id]),
    )
    await care_service.add_step(
        env["patient"].id,
        session_1.id,
        schemas.CareSessionStepCreate(
            step_code="access_cavity",
            title="Access Cavity",
            work_item_id=wi_rct.id,
            status="pending",
        ),
    )
    await care_service.add_step(
        env["patient"].id,
        session_1.id,
        schemas.CareSessionStepCreate(
            step_code="etch_bond",
            title="Etch & Bond",
            work_item_id=wi_fill.id,
            status="pending",
        ),
    )
    await care_service.finish_session(
        env["patient"].id,
        session_1.id,
        schemas.CareSessionFinish(notes="Session 1 finish"),
    )

    # Session 2: Resumes ONLY RCT (wi_rct.id)
    session_2 = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(
            work_item_ids=[wi_rct.id],
            resume_from_session_id=session_1.id,
        ),
    )

    # Defect 2 check:
    # 1. Filling steps must NOT be copied into Session 2
    # 2. RCT steps must NOT be assigned to another work item
    session_2_steps = session_2.steps
    assert len(session_2_steps) == 1
    assert session_2_steps[0].step_code == "access_cavity"
    assert session_2_steps[0].work_item_id == wi_rct.id


@pytest.mark.asyncio
async def test_multi_procedure_care_session_procedures_table(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    cmd_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    wi_1 = await cmd_service.create_work_item(
        env["patient"].id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="ENDO_RCT",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
        ),
    )
    wi_2 = await cmd_service.create_work_item(
        env["patient"].id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="REST_COMPOSITE",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="surface", tooth_key="24", surface_code="O")],
        ),
    )

    session = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(work_item_ids=[wi_1.id, wi_2.id]),
    )

    # Verify procedures loaded
    reloaded = await care_service.get_session(env["patient"].id, session.id)
    proc_wi_ids = {p.work_item_id for p in reloaded.procedures}
    assert proc_wi_ids == {wi_1.id, wi_2.id}


# ---------------------------------------------------------------------------
# 3. Historical Visits (Defect 4 & Section 2.7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_historical_visit_creation_and_no_active_session_conflict(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])

    # 1. Start an ongoing active session
    active_session = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(notes="Current active visit"),
    )
    assert active_session.status == "in_progress"

    # 2. Document a historical past visit
    past_date = datetime.now(timezone.utc) - timedelta(days=7)
    historical_session = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(
            is_historical=True,
            actual_visit_date=past_date,
            notes="Documentation of visit from last week",
        ),
    )

    assert historical_session.is_historical is True
    assert historical_session.status == "completed"
    assert historical_session.actual_visit_date is not None

    # The ongoing active session must NOT have been cancelled or conflicted
    reloaded_active = await care_service.get_session(env["patient"].id, active_session.id)
    assert reloaded_active.status == "in_progress"

    # Future date must be rejected
    future_date = datetime.now(timezone.utc) + timedelta(days=2)
    with pytest.raises(HTTPException) as exc_info:
        await care_service.start_session(
            env["patient"].id,
            schemas.CareSessionCreate(
                is_historical=True,
                actual_visit_date=future_date,
            ),
        )
    assert exc_info.value.status_code == 422
    assert "future" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# 4. Server Drafts (Section 2.6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_drafts_lifecycle_and_optimistic_concurrency(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])

    # Save draft
    draft_payload = schemas.CareSessionDraftSave(
        draft_data={"notes": "Doctor is typing findings...", "canals": [{"id": "MB1", "length": 21.5}]},
    )
    draft = await care_service.save_draft(env["patient"].id, draft_payload)
    assert draft.version_id == 1
    assert draft.draft_payload["canals"][0]["length"] == 21.5

    # Retrieve draft
    recovered = await care_service.get_draft(env["patient"].id)
    assert recovered is not None
    assert recovered.version_id == 1
    assert recovered.draft_payload["notes"] == "Doctor is typing findings..."
    read_model = schemas.CareSessionDraftRead.model_validate(recovered)
    assert read_model.draft_data["notes"] == "Doctor is typing findings..."

    # Conflict check: save with stale expected_version_id
    with pytest.raises(HTTPException) as exc_info:
        await care_service.save_draft(
            env["patient"].id,
            schemas.CareSessionDraftSave(
                draft_data={"notes": "Conflicting edit"},
                expected_version_id=999,
            ),
        )
    assert exc_info.value.status_code == 409

    # Delete draft
    assert await care_service.delete_draft(env["patient"].id) is True
    assert await care_service.get_draft(env["patient"].id) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("session_owner", ["other_patient", "other_tenant", "missing"])
async def test_draft_cannot_link_an_unrelated_visit(async_db_session, setup_test_env, session_owner):
    env = setup_test_env
    service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    if session_owner == "missing":
        session_id = 99999999
    else:
        tenant_id = env["tenant"].id
        if session_owner == "other_tenant":
            tenant = models.Tenant(name="Synthetic unrelated draft tenant")
            async_db_session.add(tenant)
            await async_db_session.flush()
            tenant_id = tenant.id
        patient = models.Patient(tenant_id=tenant_id, name="Synthetic unrelated draft patient")
        async_db_session.add(patient)
        await async_db_session.flush()
        visit = models.CareSession(tenant_id=tenant_id, patient_id=patient.id, status="completed")
        async_db_session.add(visit)
        await async_db_session.flush()
        session_id = visit.id
    with pytest.raises(HTTPException) as error:
        await service.save_draft(env["patient"].id, schemas.CareSessionDraftSave(
            care_session_id=session_id, draft_data={"notes": "Synthetic documentation"},
        ))
    assert error.value.status_code == 404
    assert await service.get_draft(env["patient"].id) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["in_progress", "completed"])
async def test_draft_can_link_its_patients_visit(async_db_session, setup_test_env, status):
    env = setup_test_env
    visit = models.CareSession(tenant_id=env["tenant"].id, patient_id=env["patient"].id, status=status)
    async_db_session.add(visit)
    await async_db_session.flush()
    service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    draft = await service.save_draft(env["patient"].id, schemas.CareSessionDraftSave(
        care_session_id=visit.id, draft_data={"notes": "Synthetic documentation"},
    ))
    assert draft.care_session_id == visit.id
    assert draft.draft_payload["notes"] == "Synthetic documentation"


# ---------------------------------------------------------------------------
# 5. Observation Amendments (Section 2.7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observation_amendment_supersedes_and_links_original(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])

    session = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(notes="Session for measurement"),
    )
    obs = await care_service.add_observation(
        env["patient"].id,
        session.id,
        schemas.CareObservationCreate(
            observation_code="working_length",
            tooth_key="16",
            canal_id="MB1",
            structured_value={"canal_id": "MB1", "length_mm": 21.0},
        ),
    )
    assert obs.is_superseded is False

    # Amend observation
    amend_payload = schemas.CareObservationAmend(
        reason="Apex locator recalibrated; true working length is 20.5mm",
        structured_value={"canal_id": "MB1", "length_mm": 20.5},
    )
    new_obs = await care_service.amend_observation(env["patient"].id, obs.id, amend_payload)

    assert new_obs.id != obs.id
    assert new_obs.structured_value["length_mm"] == 20.5
    assert new_obs.amendment_reason == amend_payload.reason
    assert new_obs.reference_source_session_id == session.id

    # Original must now be marked superseded
    await async_db_session.refresh(obs)
    assert obs.is_superseded is True
    assert obs.superseded_by_id == new_obs.id

    # Double amendment on superseded record must fail
    with pytest.raises(HTTPException) as exc_info:
        await care_service.amend_observation(
            env["patient"].id,
            obs.id,
            schemas.CareObservationAmend(reason="Second attempt"),
        )
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# 6. Follow-up Lifecycle Actions (Section 2.8 & Scenario 13, 14, 15)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_follow_up_stopping_postponing_resuming_handoff_audit(async_db_session, setup_test_env):
    env = setup_test_env
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])

    session = await care_service.start_session(
        env["patient"].id,
        schemas.CareSessionCreate(notes="Session with follow-up"),
    )
    req = await care_service.create_next_visit_request(
        env["patient"].id,
        schemas.NextVisitRequestCreate(
            care_session_id=session.id,
            reason="Crown seating follow-up",
            suggested_duration_minutes=45,
        ),
    )
    assert req.status == "requested"

    # 1. Stop follow-up
    stopped_req = await care_service.stop_next_visit_request(
        req.id,
        reason="Patient travelling abroad indefinitely",
    )
    assert stopped_req.status == "stopped"
    assert stopped_req.stopped_reason == "Patient travelling abroad indefinitely"

    # 2. Resume follow-up
    resumed_req = await care_service.resume_next_visit_request(
        req.id,
        reason="Patient returned and requested resumption",
    )
    assert resumed_req.status == "requested"
    assert resumed_req.stopped_at is None

    # 3. Postpone follow-up
    new_date = datetime.now(timezone.utc) + timedelta(days=14)
    postponed_req = await care_service.postpone_next_visit_request(
        req.id,
        postponed_to_date=new_date,
        reason="Patient has flu",
    )
    assert postponed_req.status == "postponed"
    assert postponed_req.postponed_reason == "Patient has flu"

    # 4. Handoff to unauthorized doctor must fail (Section 2.8)
    with pytest.raises(HTTPException) as exc_info:
        await care_service.handoff_next_visit_request(
            req.id,
            handoff_to_user_id=env["doctor_2"].id,
            reason="Primary doctor attending endodontic conference",
        )
    assert exc_info.value.status_code in (403, 404)

    # Grant doctor_2 authorized access to patient via mixed visibility mode + appointment
    env["doctor_2"].patient_visibility_mode = "mixed"
    appt = models.Appointment(
        tenant_id=env["tenant"].id,
        patient_id=env["patient"].id,
        doctor_id=env["doctor_2"].id,
        date_time=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=30,
        status="Confirmed",
    )
    async_db_session.add(appt)
    await async_db_session.commit()

    # Handoff to authorized doctor succeeds
    handoff_req = await care_service.handoff_next_visit_request(
        req.id,
        handoff_to_user_id=env["doctor_2"].id,
        reason="Primary doctor attending endodontic conference",
        notes="Inspect MB1 obturation before final core build-up",
    )
    assert handoff_req.assigned_doctor_id == env["doctor_2"].id
    assert handoff_req.handoff_reason == "Primary doctor attending endodontic conference"


@pytest.mark.asyncio
async def test_status_only_does_not_alter_stock_movements_targets_or_notes(async_db_session, setup_test_env):
    """
    Scenario 17/18 & Line 499: Explicit assertion that status-only updates do not
    alter stock movements, targets, notes, or unrelated clinical records.
    """
    env = setup_test_env
    await set_native_writes_flag(async_db_session, env["tenant"].id, True)

    command_service = ClinicalCommandService(
        async_db_session, env["tenant"].id, current_user=env["doctor"]
    )

    # Count existing stock movements before status change
    stmt_stock = select(func.count()).select_from(models.StockMovement)
    stock_count_before = (await async_db_session.execute(stmt_stock)).scalar() or 0

    wi_payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
        notes="Original detailed clinical notes about cavity prep",
        targets=[
            schemas.ClinicalTargetInput(
                target_kind="surface",
                tooth_key="16",
                surface_code="O",
            )
        ],
    )
    wi = await command_service.create_work_item(env["patient"].id, wi_payload)

    # Perform status-only completion
    resp = await command_service.update_work_item_status(
        patient_id=env["patient"].id,
        work_item_id=wi.id,
        payload=schemas.ClinicalWorkItemStatusUpdate(status="completed"),
    )
    assert resp.effective_status == "completed"

    # Verify notes and targets are completely preserved
    reloaded_wi = (await async_db_session.execute(
        select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi.id)
    )).scalar_one()
    assert reloaded_wi.notes == "Original detailed clinical notes about cavity prep"
    assert len(reloaded_wi.targets) == 1
    assert reloaded_wi.targets[0].surface_code == "O"

    # Verify zero stock movements were added by the status-only shortcut
    stock_count_after = (await async_db_session.execute(stmt_stock)).scalar() or 0
    assert stock_count_after == stock_count_before


@pytest.mark.asyncio
async def test_cross_tenant_isolation_fails_all_new_operations(async_db_session, setup_test_env):
    """
    Scenario 18: Cross-tenant and unauthorized patient access fail for every new operation.
    """
    env = setup_test_env
    tenant_2 = models.Tenant(name="Second Clinic Tenant", domain="clinic-2.example.com")
    async_db_session.add(tenant_2)
    await async_db_session.commit()

    doctor_t2 = models.User(
        tenant_id=tenant_2.id,
        username="doc_t2",
        email="doc_t2@dentix.io",
        hashed_password="hashed_pw_test",
        role="doctor",
        is_active=True,
    )
    async_db_session.add(doctor_t2)
    await async_db_session.commit()

    await set_native_writes_flag(async_db_session, tenant_2.id, True)

    command_service_t2 = ClinicalCommandService(
        async_db_session, tenant_2.id, current_user=doctor_t2
    )
    care_service_t2 = CareSessionService(
        async_db_session, tenant_2.id, current_user=doctor_t2
    )

    # Attempt status update on tenant 1 patient with tenant 2 doctor
    with pytest.raises(HTTPException) as exc_info:
        await command_service_t2.update_work_item_status(
            patient_id=env["patient"].id,
            work_item_id=999,
            payload=schemas.ClinicalWorkItemStatusUpdate(status="completed"),
        )
    assert exc_info.value.status_code in (403, 404)

    # Attempt draft access on tenant 1 patient with tenant 2 doctor
    with pytest.raises(HTTPException) as exc_info:
        await care_service_t2.get_draft(patient_id=env["patient"].id)
    assert exc_info.value.status_code in (403, 404)


@pytest.mark.asyncio
async def test_status_only_nurse_denied_completion_and_reopen(async_db_session, setup_test_env):
    """
    CRITICAL (Issue 1): Status-only shortcut strictly requires TREATMENT_PLAN_WRITE.
    Nurses have CLINICAL_WRITE but not TREATMENT_PLAN_WRITE, and must be denied (403)
    both completion and reopening.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]

    # Create nurse user
    nurse = models.User(
        tenant_id=tenant.id,
        username="nurse_test",
        email="nurse@alpha.com",
        hashed_password="hashed_pw_test",
        role="nurse",
        is_active=True,
    )
    async_db_session.add(nurse)
    await async_db_session.commit()

    # Create procedure with doctor
    doc_command_service = ClinicalCommandService(async_db_session, tenant.id, current_user=env["doctor"])
    proc = await doc_command_service.create_work_item(
        patient.id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="ENDO_RCT",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="36")],
        ),
    )

    nurse_command_service = ClinicalCommandService(
        async_db_session, tenant.id, current_user=nurse
    )

    # 1. Nurse denied completing procedure
    with pytest.raises(HTTPException) as exc_complete:
        await nurse_command_service.update_work_item_status(
            patient.id,
            proc.id,
            schemas.ClinicalWorkItemStatusUpdate(status="completed"),
        )
    assert exc_complete.value.status_code == 403
    assert "treatment_plan:write" in exc_complete.value.detail

    # Doctor completes procedure
    await doc_command_service.update_work_item_status(
        patient.id,
        proc.id,
        schemas.ClinicalWorkItemStatusUpdate(status="completed"),
    )

    # Reload procedure version
    reloaded_proc = (await async_db_session.execute(
        select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == proc.id)
    )).scalar_one()

    # 2. Nurse denied reopening completed procedure
    with pytest.raises(HTTPException) as exc_reopen:
        await nurse_command_service.update_work_item_status(
            patient.id,
            proc.id,
            schemas.ClinicalWorkItemStatusUpdate(
                status="active",
                intent="reopen_correction",
                reason="Nurse attempt to reopen",
                expected_version_id=reloaded_proc.version_id,
            ),
        )
    assert exc_reopen.value.status_code == 403
    assert "treatment_plan:write" in exc_reopen.value.detail


@pytest.mark.asyncio
async def test_list_sessions_eager_loads_relationships_without_missing_greenlet(async_db_session, setup_test_env):
    """
    HIGH (Issue 4): list_sessions() loads steps and their work_item targets so
    generate_session_summary does not raise MissingGreenlet on a fresh request.
    """
    env = setup_test_env
    patient = env["patient"]
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    command_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    # Create procedure
    proc = await command_service.create_work_item(
        patient.id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="ENDO_RCT",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="46")],
        ),
    )

    # Create session, add steps and finish
    session = await care_service.start_session(
        patient.id,
        schemas.CareSessionCreate(work_item_ids=[proc.id]),
    )
    await care_service.apply_template(
        patient.id,
        session.id,
        schemas.CareSessionTemplateApply(
            template_code="ENDO_RCT",
            work_item_id=proc.id,
        ),
    )
    await care_service.finish_session(
        patient.id,
        session.id,
        schemas.CareSessionFinish(
            notes="Visit completed smoothly",
        ),
    )

    # Clear identity map to simulate fresh HTTP request with no cached objects
    async_db_session.expunge_all()

    # Query sessions via list_sessions on fresh identity map
    sessions = await care_service.list_sessions(patient.id)
    assert len(sessions) >= 1
    completed_s = next(s for s in sessions if s.id == session.id)
    assert completed_s.status == "completed"
    assert hasattr(completed_s, "summary")
    assert "ENDO_RCT" in completed_s.summary
    assert "Tooth 46" in completed_s.summary


@pytest.mark.asyncio
async def test_continuation_does_not_resurrect_superseded_obs_or_duplicate_completed_steps(async_db_session, setup_test_env):
    """
    HIGH (Issue 6): Continuation carryover must only carry over active effective
    observations (not superseded ones), and must prepare remaining work without
    duplicating completed steps as new completed rows.
    """
    env = setup_test_env
    patient = env["patient"]
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])
    command_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    proc = await command_service.create_work_item(
        patient.id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="ENDO_RCT",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="16")],
        ),
    )

    # Session 1: 2 steps (step 1 completed, step 2 pending), and an observation
    s1 = await care_service.start_session(
        patient.id,
        schemas.CareSessionCreate(work_item_ids=[proc.id]),
    )
    await care_service.apply_template(
        patient.id,
        s1.id,
        schemas.CareSessionTemplateApply(
            template_code="ENDO_RCT",
            work_item_id=proc.id,
        ),
    )
    s1_steps = (await care_service.get_session(patient.id, s1.id)).steps
    # Complete step 1, leave step 2 in_progress/pending
    await care_service.update_step(
        patient.id, s1.id, s1_steps[0].id,
        schemas.CareSessionStepUpdate(status="completed"),
    )

    # Record canal observation
    obs = await care_service.add_observation(
        patient.id, s1.id,
        schemas.CareObservationCreate(
            work_item_id=proc.id,
            observation_code="working_length",
            tooth_key="16",
            structured_value={"canal_id": "MB", "length_mm": 21.0},
        ),
    )
    # Traceably amend the observation: length was corrected from 21.0 to 21.5
    amended_obs = await care_service.amend_observation(
        patient.id, obs.id,
        schemas.CareObservationAmend(
            reason="Corrected apex locator measurement",
            structured_value={"canal_id": "MB", "length_mm": 21.5},
        ),
    )
    assert amended_obs.id != obs.id
    # Original observation is now superseded
    orig_reloaded = (await async_db_session.execute(
        select(models.CareObservation).where(models.CareObservation.id == obs.id)
    )).scalar_one()
    assert orig_reloaded.is_superseded is True

    # Finish Session 1
    await care_service.finish_session(
        patient.id, s1.id,
        schemas.CareSessionFinish(notes="First session done"),
    )

    # Session 2: Resumed from Session 1
    s2 = await care_service.start_session(
        patient.id,
        schemas.CareSessionCreate(
            work_item_ids=[proc.id],
            resume_from_session_id=s1.id,
        ),
    )
    s2_loaded = await care_service.get_session(patient.id, s2.id)

    # 1. Steps: completed step from S1 must NOT be copied as a completed row
    s2_step_codes = [st.step_code for st in s2_loaded.steps]
    assert s1_steps[0].step_code not in s2_step_codes
    assert all(st.status != "completed" for st in s2_loaded.steps)

    # 2. Observations: superseded observation must NOT be carried over
    carried_obs = s2_loaded.observations
    assert len(carried_obs) == 1
    assert carried_obs[0].is_superseded is False
    assert carried_obs[0].structured_value["length_mm"] == 21.5
    assert carried_obs[0].reference_source_session_id == s1.id


@pytest.mark.asyncio
async def test_follow_up_status_transitions_under_lock_and_patient_scoping(async_db_session, setup_test_env):
    """
    HIGH (Issue 9): Follow-up transitions enforce allowed transitions under lock.
    Reopening a completed or scheduled request is rejected with 409 Conflict.
    Patient ID in route must match request patient_id.
    """
    env = setup_test_env
    patient = env["patient"]
    doctor = env["doctor"]
    care_service = CareSessionService(async_db_session, env["tenant"].id, env["doctor"])

    # Create NextVisitRequest in status 'requested'
    nvr = models.NextVisitRequest(
        tenant_id=env["tenant"].id,
        patient_id=patient.id,
        requested_by_user_id=doctor.id,
        reason="Follow-up RCT check",
        status="requested",
    )
    async_db_session.add(nvr)
    await async_db_session.commit()
    await async_db_session.refresh(nvr)

    # 1. Stop request
    stopped = await care_service.stop_next_visit_request(
        nvr.id, reason="Patient travelling abroad", patient_id=patient.id
    )
    assert stopped.status == "stopped"
    assert stopped.stopped_reason == "Patient travelling abroad"

    # 2. Resume stopped request
    resumed = await care_service.resume_next_visit_request(
        nvr.id, reason="Patient returned", patient_id=patient.id
    )
    assert resumed.status == "requested"
    assert resumed.stopped_at is None
    assert resumed.stopped_reason is None

    # 3. Postpone request
    target_dt = datetime.now(timezone.utc) + timedelta(days=14)
    postponed = await care_service.postpone_next_visit_request(
        nvr.id, postponed_to_date=target_dt, reason="Doctor on leave", patient_id=patient.id
    )
    assert postponed.status == "postponed"
    assert postponed.postponed_reason == "Doctor on leave"

    # 4. Resume postponed request
    resumed2 = await care_service.resume_next_visit_request(
        nvr.id, reason="Doctor available earlier", patient_id=patient.id
    )
    assert resumed2.status == "requested"
    assert resumed2.postponed_to_date is None
    assert resumed2.postponed_reason is None

    # 5. Mark as completed (resolved)
    resumed2.status = "completed"
    await async_db_session.commit()

    # 6. Attempting to resume completed request must be rejected with 409 Conflict
    with pytest.raises(HTTPException) as exc_conflict:
        await care_service.resume_next_visit_request(nvr.id, patient_id=patient.id)
    assert exc_conflict.value.status_code == 409
    assert "already completed" in exc_conflict.value.detail

    # 7. Attempting with mismatched patient_id must return 404
    with pytest.raises(HTTPException) as exc_mismatch:
        await care_service.resume_next_visit_request(nvr.id, patient_id=99999)
    assert exc_mismatch.value.status_code == 404


@pytest.mark.asyncio
async def test_legacy_treatment_provenance_via_clinical_events(async_db_session, setup_test_env):
    """
    HIGH (Issue 2): get_treatments resolves real work_item_id and version_id
    exclusively via ClinicalEvent provenance, removing numeric guessing.
    """
    from backend.crud.billing import get_treatments

    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]
    command_service = ClinicalCommandService(async_db_session, env["tenant"].id, env["doctor"])

    # 1. Create native work item
    wi = await command_service.create_work_item(
        patient.id,
        schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code="REST_COMPOSITE",
            status="active",
            targets=[schemas.ClinicalTargetInput(target_kind="tooth", tooth_key="11")],
        ),
    )

    # 2. Create legacy treatment
    tx = models.Treatment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        tooth_number=11,
        diagnosis="Caries",
        procedure="Composite Filling",
        doctor_id=doctor.id,
        cost=Decimal("500.00"),
        status="In Progress",
    )
    async_db_session.add(tx)
    await async_db_session.flush()

    # 3. Create ClinicalEvent linking work_item to treatment
    ev = models.ClinicalEvent(
        tenant_id=tenant.id,
        patient_id=patient.id,
        work_item_id=wi.id,
        event_type="legacy_treatment_linked",
        occurred_at=datetime.now(timezone.utc),
        payload={"treatment_id": tx.id},
    )
    async_db_session.add(ev)
    await async_db_session.commit()

    # 4. Fetch treatments through get_treatments
    treatments = await get_treatments(async_db_session, patient.id, tenant.id)
    matching_tx = next(t for t in treatments if t.id == tx.id)

    assert matching_tx.work_item_id == wi.id
    assert matching_tx.work_item_version_id == wi.version_id


def test_restore_embedded_references_handles_observation_amendments():
    """
    HIGH (Issue 10): Embedded refs remap original_observation_id and
    replacement_observation_id to care_observations without ArchiveError.
    """
    from backend.services.tenant_archive_embedded_refs import remap_event_payload

    mapping = {
        "care_observations": {101: 201, 102: 202},
        "care_sessions": {1: 10},
    }
    payload = {
        "original_observation_id": 101,
        "replacement_observation_id": 102,
        "reason": "Apex locator recalibrated",
    }
    remapped = remap_event_payload(payload, mapping)
    assert remapped["original_observation_id"] == 201
    assert remapped["replacement_observation_id"] == 202
    assert remapped["reason"] == "Apex locator recalibrated"


@pytest.mark.asyncio
async def test_draft_recovery_route_not_shadowed_by_session_id(async_db_session, setup_test_env):
    """
    HIGH (Issue 7): GET /api/v1/patients/{id}/care-sessions/draft is registered
    before GET /{session_id} so 'draft' is not treated as an integer session ID.
    """
    from httpx import AsyncClient, ASGITransport
    from backend.auth import create_access_token
    from backend.main import app

    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    token = create_access_token(data={"sub": doctor.username, "tenant_id": tenant.id, "role": doctor.role})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Save a draft via PUT
        save_res = await client.put(
            f"/api/v1/patients/{patient.id}/care-sessions/draft",
            json={"draft_data": {"notes": "Draft chairside notes"}},
            headers=headers,
        )
        assert save_res.status_code == 200

        # Recover draft via GET /care-sessions/draft
        get_res = await client.get(
            f"/api/v1/patients/{patient.id}/care-sessions/draft",
            headers=headers,
        )
        # Must be 200 OK and NOT 422 integer validation failure!
        assert get_res.status_code == 200
        data = get_res.json()["data"]
        assert data["draft_data"]["notes"] == "Draft chairside notes"


async def test_round2_issue2_procedure_progress_aggregates_across_visits(async_db_session, setup_test_env):
    """
    Review 2 Issue 2: Procedure progress aggregates logical steps across visits.
    Completing 1 of 2 steps in V1, then resuming in V2 reports 1/2 progress (not 0/1).
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    # Create procedure with 2 steps
    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    # Session 1: Add 2 steps
    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(notes="V1"))
    st1 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="prep", title="Tooth Preparation", work_item_id=proc.id
    ))
    await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="fill", title="Composite Placement", work_item_id=proc.id
    ))

    # Complete step 1, leave step 2 pending
    await care_service.update_step(patient.id, s1.id, st1.id, schemas.CareSessionStepUpdate(status="completed"))
    await care_service.finish_session(patient.id, s1.id, schemas.CareSessionFinish(notes="V1 finish"))

    # Resumed in Session 2
    s2 = await care_service.start_session(patient.id, schemas.CareSessionCreate(
        resume_work_item_id=proc.id, notes="V2"
    ))
    s2_steps = await care_service.list_steps(patient.id, s2.id)
    # Step 2 carried over into V2 (row count = 1)
    assert len(s2_steps) == 1

    # Check resumable context: MUST report 1/2 completed steps (overall procedure progress)
    ctx = await care_service.get_resumable_context(patient.id)
    proc_item = next(it for it in ctx["items"] if it["work_item_id"] == proc.id)
    assert proc_item["total_steps"] == 2
    assert proc_item["completed_steps_count"] == 1
    assert "1/2 steps completed" in proc_item["summary"]


async def test_round2_issue3_completion_checks_effective_logical_task_state(async_db_session, setup_test_env):
    """
    Review 2 Issue 3: Completion checks effective logical task state instead of obsolete occurrences.
    A pending step from V1 does not block completion after its continuation was completed in V2.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)
    cmd_service = ClinicalCommandService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    # V1: 2 steps. Step 1 completed, Step 2 marked partial
    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(notes="V1"))
    st1 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="prep", title="Tooth Preparation", work_item_id=proc.id
    ))
    st2 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="fill", title="Composite Placement", work_item_id=proc.id
    ))
    await care_service.update_step(patient.id, s1.id, st1.id, schemas.CareSessionStepUpdate(status="completed"))
    await care_service.update_step(patient.id, s1.id, st2.id, schemas.CareSessionStepUpdate(status="partial"))
    await care_service.finish_session(patient.id, s1.id, schemas.CareSessionFinish(notes="V1 finish"))

    # V2: Step 2 carried over and completed
    s2 = await care_service.start_session(patient.id, schemas.CareSessionCreate(
        resume_work_item_id=proc.id, notes="V2"
    ))
    s2_steps = await care_service.list_steps(patient.id, s2.id)
    assert len(s2_steps) == 1
    await care_service.update_step(patient.id, s2.id, s2_steps[0].id, schemas.CareSessionStepUpdate(status="completed"))
    await care_service.finish_session(patient.id, s2.id, schemas.CareSessionFinish(notes="V2 finish"))

    # Attempt to mark procedure completed WITHOUT override reason:
    # Historical partial row in V1 MUST NOT block completion because its continuation in V2 is completed!
    res = await cmd_service.update_work_item_status(
        patient.id, proc.id,
        schemas.ClinicalWorkItemStatusUpdate(status="completed")
    )
    assert res.work_item.status == "completed"


async def test_round2_issue4_corrected_measurements_excluded_from_resumable_context(async_db_session, setup_test_env):
    """
    Review 2 Issue 4: get_resumable_context and summary separate current measurements from amendment history.
    Amended/superseded measurements never appear in current effective summary or observations.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(notes="V1"))
    st = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="wl", title="Working Length", work_item_id=proc.id
    ))
    obs1 = await care_service.add_observation(patient.id, s1.id, schemas.CareObservationCreate(
        step_id=st.id,
        work_item_id=proc.id,
        observation_code="working_length",
        tooth_key="46",
        canal_id="MB",
        structured_value={"length_mm": 20.0},
    ))

    # Amend observation: replacement is 21.5mm
    obs2 = await care_service.amend_observation(
        patient.id, obs1.id,
        schemas.CareObservationAmend(
            reason="Corrected reading",
            structured_value={"length_mm": 21.5},
        ),
    )
    assert obs2.id != obs1.id

    # Check resumable context: only the active (replacement) observation is returned
    ctx = await care_service.get_resumable_context(patient.id)
    proc_item = next(it for it in ctx["items"] if it["work_item_id"] == proc.id)
    obs_list = proc_item["observations"]
    assert len(obs_list) == 1
    assert obs_list[0].id == obs2.id
    assert obs_list[0].structured_value["length_mm"] == 21.5

    # Check generate_session_summary: does not include superseded observation
    s1_loaded = await care_service.get_session(patient.id, s1.id)
    summary = care_service.generate_session_summary(s1_loaded)
    assert "21.5mm" in summary
    assert "20.0mm" not in summary


async def test_round2_issue5_skipped_steps_not_carried_over(async_db_session, setup_test_env):
    """
    Review 2 Issue 5: Deliberately skipped steps are excluded from carryover into subsequent visits.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(notes="V1"))
    st1 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="prep", title="Step 1", work_item_id=proc.id
    ))
    st2 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="skip_this", title="Step 2 Skipped", work_item_id=proc.id
    ))
    await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="fill", title="Step 3 Pending", work_item_id=proc.id
    ))

    # Mark st1 completed, st2 skipped, leave st3 pending
    await care_service.update_step(patient.id, s1.id, st1.id, schemas.CareSessionStepUpdate(status="completed"))
    await care_service.update_step(patient.id, s1.id, st2.id, schemas.CareSessionStepUpdate(status="skipped"))
    await care_service.finish_session(patient.id, s1.id, schemas.CareSessionFinish(notes="V1 done"))

    # Resume in Session 2
    s2 = await care_service.start_session(patient.id, schemas.CareSessionCreate(
        resume_work_item_id=proc.id, notes="V2"
    ))
    s2_steps = await care_service.list_steps(patient.id, s2.id)

    # ONLY Step 3 must be carried over! Step 2 (skipped) must NOT be prepared again.
    assert len(s2_steps) == 1
    assert s2_steps[0].step_code == "fill"
    assert s2_steps[0].title == "Step 3 Pending"


async def test_round3_issue2_completed_occurrence_does_not_hide_unfinished_repetition(async_db_session, setup_test_env):
    """
    Review 3 Issue 2: Distinct task/occurrence identities are persisted, and an unfinished
    repetition is not masked as satisfied by an earlier completed occurrence.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)
    cmd_service = ClinicalCommandService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(notes="V1"))

    # Initial occurrence of irrigation
    st1 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="irrigation", title="Initial NaOCl Rinse", work_item_id=proc.id
    ))
    assert st1.occurrence_number == 1
    assert st1.is_repeat is False

    # Mark initial irrigation as completed
    await care_service.update_step(patient.id, s1.id, st1.id, schemas.CareSessionStepUpdate(status="completed"))

    # Add a repeated irrigation step
    st2 = await care_service.add_step(patient.id, s1.id, schemas.CareSessionStepCreate(
        step_code="irrigation", title="Final Ultrasonic Activation", work_item_id=proc.id
    ))
    assert st2.occurrence_number == 2
    assert st2.is_repeat is True
    assert st2.status == "pending"

    # Attempting to complete the procedure while the repetition is pending must be BLOCKED
    with pytest.raises(HTTPException) as exc_info:
        await cmd_service.update_work_item_status(
            patient.id,
            proc.id,
            schemas.ClinicalWorkItemStatusUpdate(status="completed"),
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail.get("code") == "OVERRIDE_REASON_REQUIRED"
    assert exc_info.value.detail.get("outstanding_steps_count") == 1

    # Now complete the repeated step
    await care_service.update_step(patient.id, s1.id, st2.id, schemas.CareSessionStepUpdate(status="completed"))

    # Completion should now succeed without override
    updated = await cmd_service.update_work_item_status(
        patient.id,
        proc.id,
        schemas.ClinicalWorkItemStatusUpdate(status="completed"),
    )
    assert updated.effective_status == "completed"
    assert updated.work_item.status == "completed"


async def test_round3_issue3_correcting_source_measurement_updates_carried_references(async_db_session, setup_test_env):
    """
    Review 3 Issue 3: Correcting a source measurement resolves references through the
    effective correction chain, ensuring subsequent visits receive the corrected measurement.
    Reproduction: visit 1 records 20, visit 2 carries it forward, then original is corrected to 21.
    Visit 3 receives 21 from visit 2.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    # Visit 1: record observation with length 20.0
    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 1"))
    obs1 = await care_service.add_observation(patient.id, s1.id, schemas.CareObservationCreate(
        observation_code="working_length",
        tooth_key="16",
        canal_id="MB1",
        structured_value={"canal_id": "MB1", "length_mm": 20.0},
        work_item_id=proc.id,
    ))
    await care_service.finish_session(patient.id, s1.id, schemas.CareSessionFinish(notes="Visit 1 finish"))

    # Visit 2: carries forward from Visit 1
    s2 = await care_service.start_session(patient.id, schemas.CareSessionCreate(
        resume_work_item_id=proc.id,
        resume_from_session_id=s1.id,
        notes="Visit 2",
    ))
    s2_obs = await care_service.list_observations(patient.id, s2.id)
    assert len(s2_obs) == 1
    assert s2_obs[0].structured_value["length_mm"] == 20.0
    assert s2_obs[0].reference_source_observation_id == obs1.id
    await care_service.finish_session(patient.id, s2.id, schemas.CareSessionFinish(notes="Visit 2 finish"))

    # Now, original measurement in Visit 1 is corrected to 21.0
    amended = await care_service.amend_observation(
        patient.id,
        obs1.id,
        schemas.CareObservationAmend(
            structured_value={"canal_id": "MB1", "length_mm": 21.0},
            reason="Corrected apex locator calibration",
        ),
    )
    assert amended.structured_value["length_mm"] == 21.0

    # Visit 3: resumes from Visit 2
    s3 = await care_service.start_session(patient.id, schemas.CareSessionCreate(
        resume_work_item_id=proc.id,
        resume_from_session_id=s2.id,
        notes="Visit 3",
    ))
    s3_obs = await care_service.list_observations(patient.id, s3.id)
    assert len(s3_obs) == 1
    # Visit 3 must receive 21.0 (the effective corrected measurement), NOT the obsolete 20.0!
    assert s3_obs[0].structured_value["length_mm"] == 21.0
    assert s3_obs[0].reference_source_observation_id == amended.id


async def test_round4_issue1_repeated_amendments_preserve_complete_clinical_history(async_db_session, setup_test_env):
    """
    Review 4 Issue 1: Repeated amendments preserve all historical values in the database
    (e.g. 20 -> 21 -> 22) without bulk-rewriting historical payloads, while current views
    and subsequent continuations resolve to 22.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    # 1. Initial measurement 20
    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 1"))
    obs1 = await care_service.add_observation(patient.id, s1.id, schemas.CareObservationCreate(
        observation_code="working_length",
        tooth_key="16",
        canal_id="MB1",
        structured_value={"canal_id": "MB1", "length_mm": 20.0},
        work_item_id=proc.id,
    ))

    # 2. First amendment: 20 -> 21
    obs2 = await care_service.amend_observation(
        patient.id,
        obs1.id,
        schemas.CareObservationAmend(
            structured_value={"canal_id": "MB1", "length_mm": 21.0},
            reason="Initial calibration adjustment",
        ),
    )

    # 3. Second amendment: 21 -> 22
    obs3 = await care_service.amend_observation(
        patient.id,
        obs2.id,
        schemas.CareObservationAmend(
            structured_value={"canal_id": "MB1", "length_mm": 22.0},
            reason="Electronic apex locator confirmed measurement",
        ),
    )

    # Complete historical audit verification:
    # All 3 records must preserve their distinct historical values (20.0, 21.0, 22.0)
    all_obs = await care_service.list_observations(patient.id, s1.id, include_superseded=True)
    assert len(all_obs) == 3
    obs_by_id = {o.id: o for o in all_obs}
    assert obs_by_id[obs1.id].structured_value["length_mm"] == 20.0
    assert obs_by_id[obs1.id].is_superseded is True
    assert obs_by_id[obs1.id].superseded_by_id == obs2.id

    assert obs_by_id[obs2.id].structured_value["length_mm"] == 21.0
    assert obs_by_id[obs2.id].is_superseded is True
    assert obs_by_id[obs2.id].superseded_by_id == obs3.id

    assert obs_by_id[obs3.id].structured_value["length_mm"] == 22.0
    assert obs_by_id[obs3.id].is_superseded is False

    # Current view verification:
    # Default list_observations (include_superseded=False) shows only the effective 22.0
    active_obs = await care_service.list_observations(patient.id, s1.id, include_superseded=False)
    assert len(active_obs) == 1
    assert active_obs[0].id == obs3.id
    assert active_obs[0].structured_value["length_mm"] == 22.0

    # Resumable context verification shows 22.0
    resumable = await care_service.get_resumable_context(patient.id)
    assert len(resumable["items"]) >= 1
    item = next(it for it in resumable["items"] if it["work_item_id"] == proc.id)
    assert len(item["observations"]) == 1
    assert item["observations"][0].structured_value["length_mm"] == 22.0


async def test_round5_issue1_active_session_reads_project_effective_values_while_preserving_stored(async_db_session, setup_test_env):
    """
    Review 5 Issue 1:
    Reproduction: visit 2 carries measurement 20, then its original source is corrected to 21.
    get_active_session() and clinical reads return 21 to the clinical UI through response projections,
    while stored historical values in the database remain 20.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    # 1. Visit 1: Record initial measurement 20
    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 1"))
    obs1 = await care_service.add_observation(patient.id, s1.id, schemas.CareObservationCreate(
        observation_code="working_length",
        tooth_key="16",
        canal_id="MB1",
        structured_value={"canal_id": "MB1", "length_mm": 20.0},
        work_item_id=proc.id,
    ))
    await care_service.finish_session(patient.id, s1.id, schemas.CareSessionFinish())

    # 2. Visit 2: Carries measurement 20 from Visit 1
    s2 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 2"))
    assert s2.status == "in_progress"

    # Verify carried observation initially in DB has 20.0
    s2_carried = next(o for o in s2.observations if o.reference_source_observation_id == obs1.id)
    assert s2_carried.structured_value["length_mm"] == 20.0

    # 3. Correct original source in Visit 1 to 21.0
    amended_obs1 = await care_service.amend_observation(
        patient.id,
        obs1.id,
        schemas.CareObservationAmend(
            structured_value={"canal_id": "MB1", "length_mm": 21.0},
            reason="Corrected apex locator calibration",
        ),
    )
    assert amended_obs1.structured_value["length_mm"] == 21.0

    # 4. Read active session for Visit 2 via get_active_session()
    active_s2 = await care_service.get_active_session(patient.id)
    assert active_s2 is not None
    assert active_s2.id == s2.id
    active_obs = next(o for o in active_s2.observations if o.id == s2_carried.id)
    # Clinical UI receives the projected effective value: 21.0!
    assert active_obs.structured_value["length_mm"] == 21.0

    # Read via get_session() also returns projected effective value 21.0
    got_s2 = await care_service.get_session(patient.id, s2.id)
    got_obs = next(o for o in got_s2.observations if o.id == s2_carried.id)
    assert got_obs.structured_value["length_mm"] == 21.0

    # Read via list_observations() returns projected effective value 21.0
    listed_obs = await care_service.list_observations(patient.id, s2.id, include_superseded=False)
    assert listed_obs[0].structured_value["length_mm"] == 21.0

    # 5. Crucial verification: stored historical row in the database remains 20.0!
    await async_db_session.flush()
    db_stmt = select(models.CareObservation).where(models.CareObservation.id == s2_carried.id)
    raw_db_obs = (await async_db_session.execute(db_stmt)).scalar_one()
    assert not async_db_session.is_modified(raw_db_obs)

    # 6. Archive export in the same AsyncSession must export stored historical 20.0, NOT projected 21.0!
    from backend.services.tenant_archive_export import export_clinic_archive_data
    export_payload = await export_clinic_archive_data(async_db_session, tenant.id, validate_restore=False)
    exported_obs = export_payload["data"]["care_observations"]
    exported_carried = next(o for o in exported_obs if o["id"] == s2_carried.id)
    assert exported_carried["structured_value"]["length_mm"] == 20.0


async def test_round5_issue2_accepted_correction_to_carried_reference_preserved_next_visit(async_db_session, setup_test_env):
    """
    Review 5 Issue 2:
    Reproduction: Correcting a carried measurement in visit 2 from 20 to 21 succeeds.
    The next visit (visit 3) receives 21 (NOT 20!).
    Amendment lineage in visit 2 takes precedence over reference provenance.
    """
    env = setup_test_env
    patient = env["patient"]
    tenant = env["tenant"]
    doctor = env["doctor"]

    care_service = CareSessionService(async_db_session, tenant.id, doctor)

    proc = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(proc)
    await async_db_session.flush()

    # 1. Visit 1: Record initial measurement 20.0
    s1 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 1"))
    obs1 = await care_service.add_observation(patient.id, s1.id, schemas.CareObservationCreate(
        observation_code="working_length",
        tooth_key="16",
        canal_id="MB1",
        structured_value={"canal_id": "MB1", "length_mm": 20.0},
        work_item_id=proc.id,
    ))
    await care_service.finish_session(patient.id, s1.id, schemas.CareSessionFinish())

    # 2. Visit 2: Carries measurement 20.0
    s2 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 2"))
    s2_carried = next(o for o in s2.observations if o.reference_source_observation_id == obs1.id)
    assert s2_carried.structured_value["length_mm"] == 20.0

    # In Visit 2: Doctor corrects the carried measurement to 21.0
    s2_corrected = await care_service.amend_observation(
        patient.id,
        s2_carried.id,
        schemas.CareObservationAmend(
            structured_value={"canal_id": "MB1", "length_mm": 21.0},
            reason="Canal remeasured chairside in visit 2",
        ),
    )
    assert s2_corrected.structured_value["length_mm"] == 21.0
    assert s2_corrected.reference_source_observation_id is None

    # Complete Visit 2
    await care_service.finish_session(patient.id, s2.id, schemas.CareSessionFinish())

    # 3. Visit 3: Starts next visit!
    s3 = await care_service.start_session(patient.id, schemas.CareSessionCreate(work_item_ids=[proc.id], notes="Visit 3"))

    # Crucial assertion: Visit 3 receives 21.0 (the accepted correction from Visit 2), NOT 20.0!
    assert len(s3.observations) >= 1
    s3_carried = next(o for o in s3.observations if o.tooth_key == "16")
    assert s3_carried.structured_value["length_mm"] == 21.0
    assert s3_carried.reference_source_session_id == s2.id
    assert s3_carried.reference_source_observation_id == s2_corrected.id


@pytest.mark.parametrize("read_path", ["active", "session", "sessions", "observations"])
@pytest.mark.parametrize("clear_targets", [False, True], ids=["corrected-targets", "cleared-targets"])
async def test_effective_observation_projection_preserves_identity_and_history(
    async_db_session, setup_test_env, read_path, clear_targets
):
    """Effective clinical fields agree while reference identity and stored history stay intact."""
    from backend.services.tenant_archive_export import export_clinic_archive_data

    env = setup_test_env
    tenant_id = env["tenant"].id
    patient_id = env["patient"].id
    work_item = models.ClinicalWorkItem(
        tenant_id=tenant_id,
        patient_id=patient_id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=env["doctor"].id,
    )
    async_db_session.add(work_item)
    await async_db_session.flush()
    service = CareSessionService(async_db_session, tenant_id, env["doctor"])

    source_visit = await service.start_session(
        patient_id, schemas.CareSessionCreate(work_item_ids=[work_item.id])
    )
    historical_value = {
        "length_mm": 20,
        "surface_code": "B",
        "root_id": "mesiobuccal",
        "canal_id": "MB1",
        "extra": {"readings": [20]},
    }
    source = await service.add_observation(
        patient_id,
        source_visit.id,
        schemas.CareObservationCreate(
            work_item_id=work_item.id,
            observation_code="working_length",
            tooth_key="16",
            structured_value=historical_value,
            notes="Original measurement",
        ),
    )
    await service.finish_session(patient_id, source_visit.id, schemas.CareSessionFinish())
    continued_visit = await service.start_session(
        patient_id, schemas.CareSessionCreate(resume_work_item_id=work_item.id)
    )
    reference = continued_visit.observations[0]
    reference_snapshot = schemas.CareObservationRead.model_validate(reference).model_dump()
    effective_targets = {
        "surface_code": None if clear_targets else "L",
        "root_id": None if clear_targets else "mesial",
        "canal_id": None if clear_targets else "ML1",
    }
    corrected = await service.amend_observation(
        patient_id,
        source.id,
        schemas.CareObservationAmend(
            observation_code="canal_measurement",
            tooth_key="26",
            structured_value={
                "length_mm": 21,
                "extra": {"readings": [21]},
                **effective_targets,
            },
            notes="Corrected measurement identity",
            reason="Correct transcription of the measurement and its target",
        ),
    )

    if read_path == "observations":
        observations = await service.list_observations(patient_id, continued_visit.id)
    else:
        if read_path == "active":
            visit = await service.get_active_session(patient_id)
        elif read_path == "session":
            visit = await service.get_session(patient_id, continued_visit.id)
        else:
            visits = await service.list_sessions(patient_id)
            visit = next(v for v in visits if v.id == continued_visit.id)
        observations = schemas.CareSessionRead.model_validate(visit).observations
    projected = schemas.CareObservationRead.model_validate(
        next(o for o in observations if o.id == reference.id)
    )

    assert projected.observation_code == "canal_measurement"
    assert projected.tooth_key == "26"
    assert projected.structured_value == corrected.structured_value
    assert {key: getattr(projected, key) for key in effective_targets} == effective_targets
    assert projected.notes == corrected.notes
    for field in (
        "id", "tenant_id", "patient_id", "care_session_id", "step_id", "work_item_id",
        "recorded_at", "recorded_by_user_id", "created_at", "reference_source_session_id",
        "reference_source_date", "reference_source_observation_id",
    ):
        assert getattr(projected, field) == reference_snapshot[field], field

    # Presentation edits must not mutate nested values on the effective ORM measurement.
    projected.structured_value["extra"]["readings"].append(99)
    assert corrected.structured_value["extra"]["readings"] == [21]
    await async_db_session.flush()
    persisted = (
        await async_db_session.execute(
            select(models.CareObservation.__table__.c.structured_value).where(
                models.CareObservation.__table__.c.id == reference.id
            )
        )
    ).scalar_one()
    assert persisted == historical_value
    reference_entity = (
        await async_db_session.execute(
            select(models.CareObservation).where(models.CareObservation.id == reference.id)
        )
    ).scalar_one()
    assert reference_entity.structured_value == historical_value
    assert not async_db_session.is_modified(reference_entity)

    # Export from the same unit of work must retain all stored historical values.
    archive = await export_clinic_archive_data(async_db_session, tenant_id)
    archived = {row["id"]: row for row in archive["data"]["care_observations"]}
    assert archived[reference.id]["structured_value"] == historical_value
    assert archived[source.id]["structured_value"] == historical_value
    assert archived[corrected.id]["structured_value"] == corrected.structured_value





