"""
End-to-End Multi-Visit RCT Scenario and Care Session Resume Engine Tests (Slice S21).
Covers:
- G10-M12: Build resume engine
- G10-M13: Continue-treatment card data integration
- G10-M14: Deterministic clinical summary generation
- G10-M19: Migration away from free-text-only session model
- G10-M20: Full multi-visit RCT scenario integration test (closing Phase G10)
"""

from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend import models, schemas
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService


@pytest.fixture
async def seed_data(async_db_session):
    """Seed tenant, users, patient, and feature flag for RCT testing."""
    tenant_1 = models.Tenant(name="Apex Dental Clinic", domain="apex.example.com", is_active=True)
    tenant_2 = models.Tenant(name="Other Clinic", domain="other.example.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="dr_endo",
        email="endo@apex.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="dr_other",
        email="other@other.com",
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
    async_db_session.add_all([patient_1, patient_2])
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
    }


async def test_resumable_endpoint_gated_by_feature_flag(async_db_session, seed_data):
    """G10-M12: Gated behind clinical_vnext_native_writes -> 404 when disabled."""
    data = seed_data
    # Turn OFF feature flag for tenant 1
    await FeatureFlagService.set_tenant_override(
        async_db_session,
        data["tenant_1"].id,
        FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
        False,
    )
    await async_db_session.commit()

    service = CareSessionService(async_db_session, data["tenant_1"].id, data["doctor_1"])
    with pytest.raises(HTTPException) as exc_info:
        await service.get_resumable_context(data["patient_1"].id)
    assert exc_info.value.status_code == 404


async def test_resumable_endpoint_tenant_isolation(async_db_session, seed_data):
    """G10-M12: Cross-tenant access to resumable context returns 404."""
    data = seed_data
    # Doctor 2 from Tenant 2 attempts to access Patient 1 from Tenant 1
    await FeatureFlagService.set_tenant_override(
        async_db_session,
        data["tenant_2"].id,
        FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
        True,
    )
    await async_db_session.commit()

    service_other = CareSessionService(async_db_session, data["tenant_2"].id, data["doctor_2"])
    with pytest.raises(HTTPException) as exc_info:
        await service_other.get_resumable_context(data["patient_1"].id)
    assert exc_info.value.status_code == 404


async def test_deterministic_summary_generation(async_db_session, seed_data):
    """G10-M14: Verify deterministic summary generator produces formatted string."""
    data = seed_data
    service = CareSessionService(async_db_session, data["tenant_1"].id, data["doctor_1"])

    session = await service.start_session(
        data["patient_1"].id, schemas.CareSessionCreate(notes="Diagnostic evaluation")
    )
    # Apply template
    await service.apply_template(
        data["patient_1"].id, session.id, schemas.CareSessionTemplateApply(template_code="ENDO_RCT")
    )
    steps = await service.list_steps(data["patient_1"].id, session.id)

    # Complete first two steps
    await service.update_step(data["patient_1"].id, session.id, steps[0].id, schemas.CareSessionStepUpdate(status="completed"))
    await service.update_step(data["patient_1"].id, session.id, steps[1].id, schemas.CareSessionStepUpdate(status="completed"))

    # Record canal measurement
    await service.add_observation(
        data["patient_1"].id,
        session.id,
        schemas.CareObservationCreate(
            observation_code="working_length",
            tooth_key="46",
            canal_id="MB",
            structured_value={"length_mm": 20.5, "reference_point": "Incisal", "maf": 25},
        ),
    )

    summary = service.generate_session_summary(await service.get_session(data["patient_1"].id, session.id))
    assert "Tooth 46" in summary
    assert "2/6 steps completed" in summary
    assert "Canals: MB: 20.5mm" in summary
    assert "MAF 25" in summary
    assert "ref Incisal" in summary


async def test_full_multi_visit_rct_scenario_e2e(async_db_session, seed_data):
    """
    G10-M20: Full RCT Multi-Visit Scenario Acceptance Test.
    Proves:
    1. Visit 1: Start session -> template steps -> record canal observations -> partial finish.
    2. Summary generation deterministically records steps and canal measurements.
    3. Resume engine exposes unfinished RCT, steps, and canal lengths without reading notes.
    4. Visit 2: Resuming carries forward past canal measurements and remaining steps.
    5. Final finish completes procedure with zero duplicate billing and invariant preservation.
    """
    data = seed_data
    tenant_id = data["tenant_1"].id
    patient_id = data["patient_1"].id
    doctor = data["doctor_1"]

    service = CareSessionService(async_db_session, tenant_id, doctor)

    # 1. Doctor creates an active ClinicalWorkItem for Tooth 46 RCT
    work_item = models.ClinicalWorkItem(
        tenant_id=tenant_id,
        patient_id=patient_id,
        kind="procedure",
        code="ENDO_RCT",
        status="active",
        created_by_user_id=doctor.id,
    )
    async_db_session.add(work_item)
    await async_db_session.flush()

    wi_target = models.ClinicalWorkItemTarget(
        tenant_id=tenant_id,
        work_item_id=work_item.id,
        target_kind="tooth",
        tooth_key="46",
    )
    async_db_session.add(wi_target)
    await async_db_session.commit()

    # -----------------------------------------------------------------------
    # VISIT 1: Diagnosis, Access, Canal Measurement & Instrumentation
    # -----------------------------------------------------------------------
    session_1 = await service.start_session(
        patient_id,
        schemas.CareSessionCreate(notes="Visit 1: Emergency access and working length determination"),
    )
    assert session_1.status == "in_progress"

    # Populate RCT steps linked to the work item
    template_steps = await service.apply_template(
        patient_id,
        session_1.id,
        schemas.CareSessionTemplateApply(template_code="ENDO_RCT", work_item_id=work_item.id),
    )
    assert len(template_steps) == 6

    # Complete Step 1: Pre-op assessment
    await service.update_step(
        patient_id,
        session_1.id,
        template_steps[0].id,
        schemas.CareSessionStepUpdate(status="completed", notes="Pulpal necrosis confirmed"),
    )

    # Complete Step 2: Access cavity
    await service.update_step(
        patient_id,
        session_1.id,
        template_steps[1].id,
        schemas.CareSessionStepUpdate(status="completed", notes="Pulp chamber de-roofed, straight-line access achieved"),
    )

    # Record structured canal measurements on Tooth 46 (G10-M09, G10-M10)
    await service.add_observation(
        patient_id,
        session_1.id,
        schemas.CareObservationCreate(
            observation_code="working_length",
            step_id=template_steps[2].id,
            work_item_id=work_item.id,
            tooth_key="46",
            canal_id="MB",
            root_id="MB",
            structured_value={"length_mm": 20.0, "reference_point": "MB Cusp", "maf": 25},
            notes="Patent to apex",
        ),
    )
    await service.add_observation(
        patient_id,
        session_1.id,
        schemas.CareObservationCreate(
            observation_code="working_length",
            step_id=template_steps[2].id,
            work_item_id=work_item.id,
            tooth_key="46",
            canal_id="ML",
            root_id="ML",
            structured_value={"length_mm": 20.5, "reference_point": "ML Cusp", "maf": 25},
            notes="Normal curvature",
        ),
    )
    await service.add_observation(
        patient_id,
        session_1.id,
        schemas.CareObservationCreate(
            observation_code="working_length",
            step_id=template_steps[2].id,
            work_item_id=work_item.id,
            tooth_key="46",
            canal_id="D",
            root_id="D",
            structured_value={"length_mm": 21.0, "reference_point": "Distal Cusp", "maf": 30},
            notes="Wide canal",
        ),
    )

    # Complete Step 3: Canal measurement
    await service.update_step(
        patient_id,
        session_1.id,
        template_steps[2].id,
        schemas.CareSessionStepUpdate(status="completed"),
    )

    # Mark Step 4: Cleaning & shaping as partial (G10-M05)
    await service.update_step(
        patient_id,
        session_1.id,
        template_steps[3].id,
        schemas.CareSessionStepUpdate(status="partial", notes="Initial rotary prep up to size 25"),
    )

    # Finish Session 1 with notes
    finished_session_1 = await service.finish_session(
        patient_id,
        session_1.id,
        schemas.CareSessionFinish(notes="Canals medicated with calcium hydroxide; temporized with Cavit. Scheduled for obturation."),
    )
    assert finished_session_1.status == "completed"
    assert finished_session_1.summary is not None
    assert "Tooth 46" in finished_session_1.summary
    assert "MB: 20.0mm" in finished_session_1.summary
    assert "ML: 20.5mm" in finished_session_1.summary
    assert "D: 21.0mm" in finished_session_1.summary

    # Verify finalization audit event exists
    events_stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.care_session_id == session_1.id,
        models.ClinicalEvent.event_type == "care_session_finished",
    )
    finish_event = (await async_db_session.execute(events_stmt)).scalars().first()
    assert finish_event is not None
    assert finish_event.payload.get("status") == "completed"
    assert "summary" in finish_event.payload

    # Verify zero legacy finance mutations
    legacy_treatments = (await async_db_session.execute(select(models.Treatment).where(models.Treatment.patient_id == patient_id))).scalars().all()
    assert len(legacy_treatments) == 0

    # -----------------------------------------------------------------------
    # RESUME CHECK (Between visits): G10-M12 Resume Engine
    # -----------------------------------------------------------------------
    resumable = await service.get_resumable_context(patient_id)
    assert resumable["has_resumable"] is True
    assert resumable["active_session"] is None
    assert len(resumable["items"]) >= 1

    item = resumable["items"][0]
    assert item["work_item_id"] == work_item.id
    assert item["tooth_key"] == "46"
    assert item["procedure_code"] == "ENDO_RCT"
    assert item["completed_steps_count"] == 3
    assert item["total_steps"] == 6
    assert len(item["observations"]) == 3
    # Check that canal lengths are immediately readable without digging through notes
    measured_canals = {o.canal_id: o.structured_value["length_mm"] for o in item["observations"]}
    assert measured_canals == {"MB": 20.0, "ML": 20.5, "D": 21.0}

    # -----------------------------------------------------------------------
    # VISIT 2: Resume Treatment in New Care Session (G10-M12, G10-M19)
    # -----------------------------------------------------------------------
    session_2 = await service.start_session(
        patient_id,
        schemas.CareSessionCreate(
            resume_work_item_id=work_item.id,
            notes="Visit 2: Obturation and core restoration",
        ),
    )
    assert session_2.status == "in_progress"

    # Verify steps were carried forward automatically into session 2
    session_2_steps = await service.list_steps(patient_id, session_2.id)
    assert len(session_2_steps) == 6
    assert session_2_steps[0].status == "completed"  # assessment
    assert session_2_steps[1].status == "completed"  # access
    assert session_2_steps[2].status == "completed"  # canal_measurement

    # Verify canal observations were carried forward into session 2
    session_2_obs = await service.list_observations(patient_id, session_2.id)
    assert len(session_2_obs) == 3
    s2_canals = {o.canal_id: o.structured_value["length_mm"] for o in session_2_obs}
    assert s2_canals == {"MB": 20.0, "ML": 20.5, "D": 21.0}

    # Doctor completes the remaining steps in Visit 2
    # Step 4: Cleaning & Shaping
    await service.update_step(
        patient_id,
        session_2.id,
        session_2_steps[3].id,
        schemas.CareSessionStepUpdate(status="completed", notes="Final irrigation with 5.25% NaOCl and 17% EDTA"),
    )
    # Step 5: Obturation
    await service.update_step(
        patient_id,
        session_2.id,
        session_2_steps[4].id,
        schemas.CareSessionStepUpdate(status="completed", notes="Warm vertical compaction, AH Plus sealer"),
    )
    # Step 6: Restoration
    await service.update_step(
        patient_id,
        session_2.id,
        session_2_steps[5].id,
        schemas.CareSessionStepUpdate(status="completed", notes="Composite core build-up completed"),
    )

    # Finish Session 2
    finished_session_2 = await service.finish_session(
        patient_id,
        session_2.id,
        schemas.CareSessionFinish(notes="Endodontic therapy completed successfully. Post-op PA X-ray confirmed excellent obturation."),
    )
    assert finished_session_2.status == "completed"
    assert "6/6 steps completed" in finished_session_2.summary

    # Mark work item completed
    work_item.status = "completed"
    await async_db_session.commit()

    # Verify resumable context now shows no unfinished items
    post_completion_resumable = await service.get_resumable_context(patient_id)
    assert post_completion_resumable["has_resumable"] is False
    assert len(post_completion_resumable["items"]) == 0
