"""Regression coverage for tenant-safe permanent patient deletion."""

import pytest
from sqlalchemy import select

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.crud.patient import (
    PATIENT_CLINICAL_DELETE_ORDER,
    delete_patient_permanently,
)
import json
from backend.services.export_service import export_tenant_data
from backend.services.import_service import delete_tenant_data, restore_tenant_from_json


def test_delete_order_covers_every_direct_clinical_patient_foreign_key():
    direct_patient_models = {
        mapper.class_
        for mapper in models.Base.registry.mappers
        if mapper.class_.__module__ == "backend.models.clinical_core"
        and "patient_id" in mapper.local_table.c
        and any(
            foreign_key.target_fullname == "patients.id"
            for foreign_key in mapper.local_table.c.patient_id.foreign_keys
        )
    }

    assert set(PATIENT_CLINICAL_DELETE_ORDER) == direct_patient_models


@pytest.mark.asyncio
async def test_full_replacement_cleanup_removes_only_matching_tenant_rows(
    async_db_session,
):
    tenant_a = models.Tenant(name="Import Replace Clinic A")
    tenant_b = models.Tenant(name="Import Replace Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    patient_a = models.Patient(
        tenant_id=tenant_a.id,
        name="Replace Me",
        age=30,
        phone="01000000011",
        medical_history="None",
        notes="",
    )
    patient_b = models.Patient(
        tenant_id=tenant_b.id,
        name="Keep Me",
        age=31,
        phone="01000000012",
        medical_history="None",
        notes="",
    )
    async_db_session.add_all([patient_a, patient_b])
    await async_db_session.flush()

    item_a = models.ClinicalWorkItem(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        kind="procedure",
        code="PROS_CROWN",
    )
    item_b = models.ClinicalWorkItem(
        tenant_id=tenant_b.id,
        patient_id=patient_b.id,
        kind="procedure",
        code="PROS_CROWN",
    )
    async_db_session.add_all([item_a, item_b])
    await async_db_session.commit()

    patient_a_id = patient_a.id
    patient_b_id = patient_b.id
    item_b_id = item_b.id
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id
    token = set_current_tenant_id(tenant_a_id)
    try:
        await delete_tenant_data(async_db_session, tenant_a_id)
        await async_db_session.commit()
    finally:
        clear_tenant_context(tenant_token=token)

    remaining_a = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_a_id
        )
    )
    remaining_b = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_b_id
        )
    )
    assert remaining_a.scalars().all() == []
    assert [item.id for item in remaining_b.scalars().all()] == [item_b_id]
    assert await async_db_session.get(models.Patient, patient_a_id) is None
    assert await async_db_session.get(models.Patient, patient_b_id) is not None


@pytest.mark.asyncio
async def test_permanent_delete_removes_only_matching_tenant_clinical_rows(
    async_db_session,
):
    tenant_a = models.Tenant(name="Hard Delete Clinic A")
    tenant_b = models.Tenant(name="Hard Delete Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    patient_a = models.Patient(
        tenant_id=tenant_a.id,
        name="Delete Me",
        age=30,
        phone="01000000001",
        medical_history="None",
        notes="",
    )
    patient_b = models.Patient(
        tenant_id=tenant_b.id,
        name="Keep Me",
        age=31,
        phone="01000000002",
        medical_history="None",
        notes="",
    )
    async_db_session.add_all([patient_a, patient_b])
    await async_db_session.flush()

    work_item_a = models.ClinicalWorkItem(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        kind="procedure",
        code="CROWN",
    )
    work_item_b = models.ClinicalWorkItem(
        tenant_id=tenant_b.id,
        patient_id=patient_b.id,
        kind="procedure",
        code="CROWN",
    )
    coverage_a = models.ClinicalProjectionCoverage(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        domain="treatments",
        status="PARTIAL",
    )
    async_db_session.add_all([work_item_a, work_item_b, coverage_a])
    await async_db_session.commit()

    patient_a_id = patient_a.id
    patient_b_id = patient_b.id
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id
    token = set_current_tenant_id(tenant_a_id)
    try:
        deleted = await delete_patient_permanently(
            async_db_session,
            patient_a_id,
            tenant_a_id,
        )
    finally:
        clear_tenant_context(tenant_token=token)

    assert deleted is not None
    assert await async_db_session.get(models.Patient, patient_a_id) is None
    assert await async_db_session.get(models.Patient, patient_b_id) is not None

    remaining_a = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_a_id,
            models.ClinicalWorkItem.patient_id == patient_a_id,
        )
    )
    assert remaining_a.scalars().all() == []

    remaining_b = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_b_id,
            models.ClinicalWorkItem.patient_id == patient_b_id,
        )
    )
    assert [item.id for item in remaining_b.scalars().all()] == [work_item_b.id]


@pytest.mark.asyncio
async def test_export_and_replacement_import_roundtrip_clinical_vnext(
    async_db_session,
):
    """Full-replacement backup integrity: Clinical VNext rows serialize and restore safely."""
    tenant_a = models.Tenant(name="Export Roundtrip Clinic A")
    tenant_b = models.Tenant(name="Export Roundtrip Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    user_a = models.User(
        tenant_id=tenant_a.id,
        full_name="Dr. Alice",
        username="dralice",
        email="alice@clinica.com",
        hashed_password="hashed_pw_alice",
        role="doctor",
    )
    user_b = models.User(
        tenant_id=tenant_b.id,
        full_name="Dr. Bob",
        username="drbob",
        email="bob@clinicb.com",
        hashed_password="hashed_pw_bob",
        role="doctor",
    )
    patient_a = models.Patient(
        tenant_id=tenant_a.id,
        name="Patient Alice",
        age=30,
        phone="01000000021",
        medical_history="None",
        notes="",
    )
    patient_b = models.Patient(
        tenant_id=tenant_b.id,
        name="Patient Bob",
        age=40,
        phone="01000000022",
        medical_history="None",
        notes="",
    )
    async_db_session.add_all([user_a, user_b, patient_a, patient_b])
    await async_db_session.flush()

    # Create full set of Clinical VNext entities for Tenant A
    wt_a = models.WorkflowTemplate(
        tenant_id=tenant_a.id,
        template_code="TEST_WT_A",
        version=1,
        title="Template A",
        description="Desc A",
        definition={"steps": [1, 2]},
    )
    wi_a = models.ClinicalWorkItem(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="planned",
        created_by_user_id=user_a.id,
    )
    async_db_session.add_all([wt_a, wi_a])
    await async_db_session.flush()

    wit_a = models.ClinicalWorkItemTarget(
        tenant_id=tenant_a.id,
        work_item_id=wi_a.id,
        target_kind="surface",
        tooth_key="16",
        surface_code="M",
    )
    plan_a = models.ClinicalTreatmentPlan(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        title="Comprehensive Plan A",
        created_by_user_id=user_a.id,
    )
    async_db_session.add_all([wit_a, plan_a])
    await async_db_session.flush()

    phase_a = models.ClinicalTreatmentPlanPhase(
        tenant_id=tenant_a.id,
        plan_id=plan_a.id,
        phase_order=1,
        name="Phase 1",
    )
    async_db_session.add(phase_a)
    await async_db_session.flush()

    tpi_a = models.ClinicalTreatmentPlanItem(
        tenant_id=tenant_a.id,
        phase_id=phase_a.id,
        work_item_id=wi_a.id,
        item_order=1,
    )
    session_a = models.CareSession(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        provider_user_id=user_a.id,
        status="completed",
    )
    async_db_session.add_all([tpi_a, session_a])
    await async_db_session.flush()

    step_a = models.CareSessionStep(
        tenant_id=tenant_a.id,
        care_session_id=session_a.id,
        work_item_id=wi_a.id,
        step_order=1,
        step_code="STEP_PREP",
        title="Preparation",
    )
    async_db_session.add(step_a)
    await async_db_session.flush()

    obs_a = models.CareObservation(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        care_session_id=session_a.id,
        step_id=step_a.id,
        work_item_id=wi_a.id,
        observation_code="COLOR_SHADE",
        tooth_key="16",
        structured_value={"shade": "A2"},
    )
    event_a = models.ClinicalEvent(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        work_item_id=wi_a.id,
        care_session_id=session_a.id,
        event_type="procedure_recorded",
        payload={"canonical_code": "REST_COMPOSITE"},
    )
    nvr_a = models.NextVisitRequest(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        care_session_id=session_a.id,
        work_item_id=wi_a.id,
        reason="Follow up",
    )
    cov_a = models.ClinicalProjectionCoverage(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        domain="teeth",
        status="COMPLETE",
    )
    att_a = models.Attachment(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        filename="xray_a.png",
        file_path="/files/xray_a.png",
        file_type="image/png",
    )
    async_db_session.add_all([obs_a, event_a, nvr_a, cov_a, att_a])
    await async_db_session.flush()

    ev_target_a = models.ClinicalEventTarget(
        tenant_id=tenant_a.id,
        event_id=event_a.id,
        target_kind="surface",
        tooth_key="16",
        surface_code="M",
    )
    cal_a = models.ClinicalAttachmentLink(
        tenant_id=tenant_a.id,
        attachment_id=att_a.id,
        patient_id=patient_a.id,
        work_item_id=wi_a.id,
        care_session_id=session_a.id,
        clinical_event_id=event_a.id,
        tooth_key="16",
        purpose_code="DIAGNOSTIC_XRAY",
    )
    async_db_session.add_all([ev_target_a, cal_a])

    # Add Tenant B data that must remain untouched
    wi_b = models.ClinicalWorkItem(
        tenant_id=tenant_b.id,
        patient_id=patient_b.id,
        kind="procedure",
        code="PROS_CROWN",
        status="planned",
    )
    async_db_session.add(wi_b)
    await async_db_session.commit()

    wi_b_id = wi_b.id
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id

    token = set_current_tenant_id(tenant_a_id)
    try:
        # 1. Export Tenant A
        backup_data = await export_tenant_data(async_db_session, tenant_a_id)
        assert "clinical_work_items" in backup_data["data"]
        assert len(backup_data["data"]["clinical_work_items"]) == 1
        assert len(backup_data["data"]["care_sessions"]) == 1
        assert len(backup_data["data"]["clinical_treatment_plans"]) == 1
        assert len(backup_data["data"]["clinical_projection_coverages"]) == 1

        # 2. Restore Tenant A from JSON (Full replacement)
        json_str = json.dumps(backup_data)
        result = await restore_tenant_from_json(async_db_session, tenant_a_id, json_str)
        assert result["success"] is True, result.get("error")
    finally:
        clear_tenant_context(tenant_token=token)

    # 3. Verify Tenant Isolation: Tenant B untouched
    res_b = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.tenant_id == tenant_b_id)
    )
    items_b = res_b.scalars().all()
    assert len(items_b) == 1
    assert items_b[0].id == wi_b_id

    # 4. Verify Tenant A Restored Entities and Relationships
    res_wi = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.tenant_id == tenant_a_id)
    )
    restored_wis = res_wi.scalars().all()
    assert len(restored_wis) == 1
    new_wi = restored_wis[0]
    assert new_wi.code == "REST_COMPOSITE"

    res_wit = await async_db_session.execute(
        select(models.ClinicalWorkItemTarget).where(models.ClinicalWorkItemTarget.tenant_id == tenant_a_id)
    )
    restored_wits = res_wit.scalars().all()
    assert len(restored_wits) == 1
    assert restored_wits[0].work_item_id == new_wi.id
    assert restored_wits[0].surface_code == "M"

    res_plan = await async_db_session.execute(
        select(models.ClinicalTreatmentPlan).where(models.ClinicalTreatmentPlan.tenant_id == tenant_a_id)
    )
    restored_plans = res_plan.scalars().all()
    assert len(restored_plans) == 1

    res_phase = await async_db_session.execute(
        select(models.ClinicalTreatmentPlanPhase).where(models.ClinicalTreatmentPlanPhase.tenant_id == tenant_a_id)
    )
    restored_phases = res_phase.scalars().all()
    assert len(restored_phases) == 1
    assert restored_phases[0].plan_id == restored_plans[0].id

    res_tpi = await async_db_session.execute(
        select(models.ClinicalTreatmentPlanItem).where(models.ClinicalTreatmentPlanItem.tenant_id == tenant_a_id)
    )
    restored_tpis = res_tpi.scalars().all()
    assert len(restored_tpis) == 1
    assert restored_tpis[0].phase_id == restored_phases[0].id
    assert restored_tpis[0].work_item_id == new_wi.id

    res_session = await async_db_session.execute(
        select(models.CareSession).where(models.CareSession.tenant_id == tenant_a_id)
    )
    restored_sessions = res_session.scalars().all()
    assert len(restored_sessions) == 1
    new_session = restored_sessions[0]

    res_step = await async_db_session.execute(
        select(models.CareSessionStep).where(models.CareSessionStep.tenant_id == tenant_a_id)
    )
    restored_steps = res_step.scalars().all()
    assert len(restored_steps) == 1
    assert restored_steps[0].care_session_id == new_session.id
    assert restored_steps[0].work_item_id == new_wi.id

    res_obs = await async_db_session.execute(
        select(models.CareObservation).where(models.CareObservation.tenant_id == tenant_a_id)
    )
    restored_obs = res_obs.scalars().all()
    assert len(restored_obs) == 1
    assert restored_obs[0].care_session_id == new_session.id
    assert restored_obs[0].step_id == restored_steps[0].id
    assert restored_obs[0].work_item_id == new_wi.id
    assert restored_obs[0].structured_value == {"shade": "A2"}

    res_event = await async_db_session.execute(
        select(models.ClinicalEvent).where(models.ClinicalEvent.tenant_id == tenant_a_id)
    )
    restored_events = res_event.scalars().all()
    assert len(restored_events) == 1
    new_event = restored_events[0]
    assert new_event.work_item_id == new_wi.id
    assert new_event.care_session_id == new_session.id

    res_cet = await async_db_session.execute(
        select(models.ClinicalEventTarget).where(models.ClinicalEventTarget.tenant_id == tenant_a_id)
    )
    restored_cets = res_cet.scalars().all()
    assert len(restored_cets) == 1
    assert restored_cets[0].event_id == new_event.id

    res_cal = await async_db_session.execute(
        select(models.ClinicalAttachmentLink).where(models.ClinicalAttachmentLink.tenant_id == tenant_a_id)
    )
    restored_cals = res_cal.scalars().all()
    assert len(restored_cals) == 1
    assert restored_cals[0].work_item_id == new_wi.id
    assert restored_cals[0].care_session_id == new_session.id
    assert restored_cals[0].clinical_event_id == new_event.id

    res_cpc = await async_db_session.execute(
        select(models.ClinicalProjectionCoverage).where(models.ClinicalProjectionCoverage.tenant_id == tenant_a_id)
    )
    restored_cpcs = res_cpc.scalars().all()
    assert len(restored_cpcs) == 1
    assert restored_cpcs[0].domain == "teeth"
    assert restored_cpcs[0].status == "COMPLETE"


@pytest.mark.asyncio
async def test_replacement_import_backward_compatible_without_clinical_sections(
    async_db_session,
):
    tenant = models.Tenant(name="Legacy Backup Clinic")
    async_db_session.add(tenant)
    await async_db_session.flush()

    token = set_current_tenant_id(tenant.id)
    try:
        # Legacy backup format containing only legacy fields
        legacy_backup = {
            "version": "1.0",
            "tenant_id": tenant.id,
            "export_date": "2026-09-10T00:00:00",
            "data": {
                "patients": [
                    {
                        "id": 1,
                        "name": "Legacy Patient",
                        "age": 45,
                        "phone": "0123456789",
                        "medical_history": "None",
                        "notes": "",
                        "created_at": "2026-09-10 00:00:00",
                    }
                ],
                "users": [],
            },
        }
        res = await restore_tenant_from_json(
            async_db_session, tenant.id, json.dumps(legacy_backup)
        )
        assert res["success"] is True, res.get("error")
    finally:
        clear_tenant_context(tenant_token=token)

    res_p = await async_db_session.execute(
        select(models.Patient).where(models.Patient.tenant_id == tenant.id)
    )
    patients = res_p.scalars().all()
    assert len(patients) == 1
    assert patients[0].name == "Legacy Patient"
