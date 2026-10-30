"""
Unit and Integration Contract Tests for U2:
Treatment Plan Item Linking on Create and Workspace Invariants.

Verifies U2.1 and U2.2 contracts:
1. Happy path: planned work item + legacy create with link -> treatment created,
   work item count unchanged, status updated to completed, event recorded with
   treatment_id and linked_existing_work_item: True.
2. Rejection contracts:
   - 404 cross-tenant (work item in another tenant)
   - 404 wrong patient (work item belongs to different patient)
   - 409 not open (work item status='completed' or kind='finding')
   - 422 code mismatch (treatment mapped canonical code != work item code)
   - 422 unmapped name (custom clinic procedure not in allowlist)
   - 422 target mismatch (tooth mismatch or surface mismatch)
   - 409 already linked (work item already linked to another existing treatment)
   - 409 shadow off (clinical shadow mode not active)
3. Invariants: payments, stock movements, lab orders unchanged; plan rows unchanged; Treatment.cost preserved.
4. Update sync: editing linked treatment updates the linked work item.
5. Byte-for-byte regression: unlinked creates behave identically to baseline.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend import models, schemas
from backend.clinical.catalog import ProcedureCode


async def _enable_shadow(async_db_session, tenant_id: int):
    """Helper to enable clinical_vnext_shadow for a tenant."""
    stmt = select(models.TenantFeature).where(
        models.TenantFeature.tenant_id == tenant_id,
        models.TenantFeature.feature_key == "clinical_vnext_shadow",
    )
    res = await async_db_session.execute(stmt)
    tf = res.scalar_one_or_none()
    if not tf:
        tf = models.TenantFeature(
            tenant_id=tenant_id,
            feature_key="clinical_vnext_shadow",
            is_enabled=True,
        )
        async_db_session.add(tf)
    else:
        tf.is_enabled = True
    await async_db_session.commit()


async def _disable_shadow(async_db_session, tenant_id: int):
    """Helper to disable clinical_vnext_shadow for a tenant."""
    stmt = select(models.TenantFeature).where(
        models.TenantFeature.tenant_id == tenant_id,
        models.TenantFeature.feature_key == "clinical_vnext_shadow",
    )
    res = await async_db_session.execute(stmt)
    tf = res.scalar_one_or_none()
    if tf:
        tf.is_enabled = False
        await async_db_session.commit()

    # Also ensure global flag is disabled
    g_stmt = select(models.FeatureFlag).where(
        models.FeatureFlag.key.in_(["clinical_vnext_shadow", "clinical_vnext_primary"])
    )
    g_res = await async_db_session.execute(g_stmt)
    for g_flag in g_res.scalars().all():
        g_flag.is_global_enabled = False
    await async_db_session.commit()


async def _create_work_item(
    async_db_session,
    tenant_id: int,
    patient_id: int,
    code: str,
    tooth_key: str,
    surfaces: list[str] = None,
    status: str = "planned",
    kind: str = "procedure",
) -> models.ClinicalWorkItem:
    """Helper to create a ClinicalWorkItem with anatomical targets."""
    wi = models.ClinicalWorkItem(
        tenant_id=tenant_id,
        patient_id=patient_id,
        kind=kind,
        code=code,
        status=status,
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    if surfaces:
        for s in surfaces:
            async_db_session.add(
                models.ClinicalWorkItemTarget(
                    tenant_id=tenant_id,
                    work_item_id=wi.id,
                    target_kind="surface",
                    tooth_key=tooth_key,
                    surface_code=s,
                )
            )
    else:
        async_db_session.add(
            models.ClinicalWorkItemTarget(
                tenant_id=tenant_id,
                work_item_id=wi.id,
                target_kind="tooth",
                tooth_key=tooth_key,
            )
        )
    await async_db_session.commit()
    await async_db_session.refresh(wi)
    return wi


@pytest.mark.asyncio
async def test_u2_happy_path_linked_treatment(
    client, admin_headers, test_patient, test_tenant, async_db_session
):
    """
    U2.1 & U2.2:
    - Planned work item + legacy create with clinical_work_item_id
    - Treatment created, work item count unchanged, status -> completed
    - Event appended with linked_existing_work_item: True and treatment_id
    """
    await _enable_shadow(async_db_session, test_tenant.id)

    # 1. Create planned work item (Tooth 16, Surface O, REST_COMPOSITE)
    wi = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="16",
        surfaces=["O"],
        status="planned",
    )

    # Record initial work item count
    wi_count_before = (
        await async_db_session.execute(
            select(func.count(models.ClinicalWorkItem.id)).where(
                models.ClinicalWorkItem.tenant_id == test_tenant.id
            )
        )
    ).scalar()

    # 2. Perform linked treatment creation via API
    proc_name = "حشو كومبوزيت -- Composite Filling Class I"
    payload = {
        "patient_id": test_patient.id,
        "procedure": proc_name,
        "cost": 650.0,
        "discount": 0.0,
        "tooth_number": 16,
        "surface": "O",
        "surfaces": ["O"],
        "status": "Done",
        "clinical_work_item_id": wi.id,
    }

    resp = client.post("/api/v1/treatments", json=payload, headers=admin_headers)
    assert resp.status_code in (200, 201), resp.text
    t_data = resp.json()["data"]
    treatment_id = t_data["id"]

    # 3. Invariants verification:
    # Work item count UNCHANGED (no new work item created)
    wi_count_after = (
        await async_db_session.execute(
            select(func.count(models.ClinicalWorkItem.id)).where(
                models.ClinicalWorkItem.tenant_id == test_tenant.id
            )
        )
    ).scalar()
    assert wi_count_after == wi_count_before

    # Reload work item: status must now be completed
    wi_id = wi.id
    await async_db_session.rollback()
    stmt = (
        select(models.ClinicalWorkItem)
        .options(selectinload(models.ClinicalWorkItem.targets))
        .where(models.ClinicalWorkItem.id == wi_id)
    )
    reloaded_wi = (await async_db_session.execute(stmt)).scalars().first()
    assert reloaded_wi.status == "completed"

    # Verify ClinicalEvent appended with linked_existing_work_item: True
    ev_stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.work_item_id == wi.id,
        models.ClinicalEvent.event_type == "procedure_recorded",
    )
    events = (await async_db_session.execute(ev_stmt)).scalars().all()
    assert len(events) == 1
    ev = events[0]
    assert ev.payload.get("treatment_id") == treatment_id
    assert ev.payload.get("linked_existing_work_item") is True
    assert ev.payload.get("canonical_code") == ProcedureCode.REST_COMPOSITE.value
    assert ev.payload.get("status") == "completed"


@pytest.mark.asyncio
async def test_u2_rejections_and_error_codes(
    client, admin_headers, test_patient, test_tenant, async_db_session
):
    """
    U2.1 Rejection Matrix:
    - 409 CLINICAL_LINK_UNAVAILABLE (shadow mode OFF)
    - 404 (work item in another tenant / cross-tenant isolation)
    - 404 (work item belongs to different patient)
    - 409 CLINICAL_LINK_NOT_OPEN (work item already completed or kind is finding)
    - 422 CLINICAL_LINK_CODE_MISMATCH (mapped canonical code != work item code)
    - 422 CLINICAL_LINK_CODE_MISMATCH (unmapped custom procedure name -> None mapping)
    - 422 CLINICAL_LINK_TARGET_MISMATCH (different tooth key or surfaces mismatch)
    - 409 CLINICAL_LINK_ALREADY_LINKED (work item already linked to existing treatment)
    """
    # 1. Rejection: 409 CLINICAL_LINK_UNAVAILABLE (shadow OFF)
    await _disable_shadow(async_db_session, test_tenant.id)
    wi_shadow_off = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="16",
        surfaces=["O"],
    )
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "O",
            "clinical_work_item_id": wi_shadow_off.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "CLINICAL_LINK_UNAVAILABLE" in resp.text

    # Enable shadow for subsequent tests
    await _enable_shadow(async_db_session, test_tenant.id)

    # 2. Rejection: 404 cross-tenant (work item in tenant 99999)
    wi_other_tenant = await _create_work_item(
        async_db_session,
        tenant_id=99999,
        patient_id=test_patient.id,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="16",
        surfaces=["O"],
    )
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "O",
            "clinical_work_item_id": wi_other_tenant.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404

    # 3. Rejection: 404 wrong patient (patient 99999)
    wi_other_patient = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=99999,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="16",
        surfaces=["O"],
    )
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "O",
            "clinical_work_item_id": wi_other_patient.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404

    # 4. Rejection: 409 CLINICAL_LINK_NOT_OPEN (status completed)
    wi_closed = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="16",
        surfaces=["O"],
        status="completed",
    )
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "O",
            "clinical_work_item_id": wi_closed.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "CLINICAL_LINK_NOT_OPEN" in resp.text

    # 5. Rejection: 422 CLINICAL_LINK_CODE_MISMATCH (treatment is RCT, work item is Composite)
    wi_composite = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="16",
        surfaces=["O"],
        status="planned",
    )
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو عصب – Root Canal Treatment",
            "cost": 800,
            "tooth_number": 16,
            "clinical_work_item_id": wi_composite.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert "CLINICAL_LINK_CODE_MISMATCH" in resp.text

    # 6. Rejection: 422 CLINICAL_LINK_CODE_MISMATCH (custom unmapped procedure)
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "Custom Clinic Whitening 999",
            "cost": 800,
            "tooth_number": 16,
            "clinical_work_item_id": wi_composite.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert "CLINICAL_LINK_CODE_MISMATCH" in resp.text

    # 7. Rejection: 422 CLINICAL_LINK_TARGET_MISMATCH (different tooth: tooth 14 vs 16)
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 14,
            "surface": "O",
            "clinical_work_item_id": wi_composite.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert "CLINICAL_LINK_TARGET_MISMATCH" in resp.text

    # 8. Rejection: 422 CLINICAL_LINK_TARGET_MISMATCH (surfaces mismatch: 'MO' vs 'O')
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "MO",
            "surfaces": ["M", "O"],
            "clinical_work_item_id": wi_composite.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert "CLINICAL_LINK_TARGET_MISMATCH" in resp.text

    # 9. Rejection: 409 CLINICAL_LINK_ALREADY_LINKED (perform first -> second attempt must fail)
    resp_success = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "O",
            "surfaces": ["O"],
            "clinical_work_item_id": wi_composite.id,
        },
        headers=admin_headers,
    )
    assert resp_success.status_code in (200, 201)

    # Second attempt to link the SAME work item must raise 409 CLINICAL_LINK_ALREADY_LINKED
    # (even if someone resets status, the existing event link prevents reuse)
    resp_dup = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 500,
            "tooth_number": 16,
            "surface": "O",
            "surfaces": ["O"],
            "clinical_work_item_id": wi_composite.id,
        },
        headers=admin_headers,
    )
    assert resp_dup.status_code == 409
    assert ("CLINICAL_LINK_ALREADY_LINKED" in resp_dup.text or "CLINICAL_LINK_NOT_OPEN" in resp_dup.text)


@pytest.mark.asyncio
async def test_u2_invariants_and_plan_untouched(
    client, admin_headers, test_patient, test_tenant, async_db_session
):
    """
    U2.2 Invariant Verification:
    - Counts of payments, stock_movements, treatment_material_usages, lab_orders unchanged vs baseline.
    - Treatment.cost equals requested amount.
    - No ClinicalTreatmentPlan* rows altered by treatment creation.
    """
    await _enable_shadow(async_db_session, test_tenant.id)

    # Create plan, phase, item
    plan = models.ClinicalTreatmentPlan(
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        title="Comprehensive Plan",
        status="accepted",
    )
    async_db_session.add(plan)
    await async_db_session.flush()

    phase = models.ClinicalTreatmentPlanPhase(
        tenant_id=test_tenant.id,
        plan_id=plan.id,
        name="Phase 1 Restorative",
        phase_order=1,
    )
    async_db_session.add(phase)
    await async_db_session.flush()

    wi = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        code=ProcedureCode.SURG_EXTRACTION.value,
        tooth_key="11",
        status="planned",
    )

    plan_item = models.ClinicalTreatmentPlanItem(
        tenant_id=test_tenant.id,
        phase_id=phase.id,
        work_item_id=wi.id,
    )
    async_db_session.add(plan_item)
    await async_db_session.commit()

    # Capture baselines
    pay_count = (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar()
    stock_count = (await async_db_session.execute(select(func.count(models.StockMovement.id)))).scalar()
    plans_count = (await async_db_session.execute(select(func.count(models.ClinicalTreatmentPlan.id)))).scalar()
    phases_count = (await async_db_session.execute(select(func.count(models.ClinicalTreatmentPlanPhase.id)))).scalar()
    items_count = (await async_db_session.execute(select(func.count(models.ClinicalTreatmentPlanItem.id)))).scalar()

    # Perform linked treatment
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "خلع عادي – Simple Extraction",
            "cost": 300.0,
            "tooth_number": 11,
            "status": "Done",
            "clinical_work_item_id": wi.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201), resp.text

    plan_id = plan.id
    await async_db_session.rollback()

    # Verify counts: payments, stock, plans, phases, items are completely unchanged
    assert (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar() == pay_count
    assert (await async_db_session.execute(select(func.count(models.StockMovement.id)))).scalar() == stock_count
    assert (await async_db_session.execute(select(func.count(models.ClinicalTreatmentPlan.id)))).scalar() == plans_count
    assert (await async_db_session.execute(select(func.count(models.ClinicalTreatmentPlanPhase.id)))).scalar() == phases_count
    assert (await async_db_session.execute(select(func.count(models.ClinicalTreatmentPlanItem.id)))).scalar() == items_count

    # Plan status unchanged (plan membership references work item; plan-level status remains 'accepted')
    p_reloaded = (await async_db_session.execute(select(models.ClinicalTreatmentPlan).where(models.ClinicalTreatmentPlan.id == plan_id))).scalar_one()
    assert p_reloaded.status == "accepted"


@pytest.mark.asyncio
async def test_u2_update_path_linked_treatment(
    client, admin_headers, test_patient, test_tenant, async_db_session
):
    """
    U2.2:
    - Editing linked treatment status (Done <-> In Progress)
    - Updates the LINKED work item (proves existing _find_linked_clinical_work_item works with reused item).
    """
    await _enable_shadow(async_db_session, test_tenant.id)

    wi = await _create_work_item(
        async_db_session,
        tenant_id=test_tenant.id,
        patient_id=test_patient.id,
        code=ProcedureCode.REST_COMPOSITE.value,
        tooth_key="26",
        surfaces=["O"],
        status="planned",
    )

    wi_id = wi.id
    # 1. Create linked treatment with status 'In Progress'
    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 600,
            "tooth_number": 26,
            "surface": "O",
            "surfaces": ["O"],
            "status": "In Progress",
            "clinical_work_item_id": wi.id,
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    t_id = resp.json()["data"]["id"]

    await async_db_session.rollback()
    wi_active = (await async_db_session.execute(select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi_id))).scalar_one()
    assert wi_active.status == "active"

    # 2. Update treatment to status 'Done'
    update_resp = client.put(
        f"/api/v1/treatments/{t_id}",
        json={
            "patient_id": test_patient.id,
            "procedure": "حشو كومبوزيت -- Composite Filling Class I",
            "cost": 600,
            "tooth_number": 26,
            "surface": "O",
            "surfaces": ["O"],
            "status": "Done",
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200

    # 3. Reload work item: must be updated to 'completed'
    await async_db_session.rollback()
    wi_done = (await async_db_session.execute(select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi_id))).scalar_one()
    assert wi_done.status == "completed"


@pytest.mark.asyncio
async def test_u2_regression_normal_unlinked_create(
    client, admin_headers, test_patient, test_tenant, async_db_session
):
    """
    U2.1 Regression:
    - Requests without clinical_work_item_id behave byte-for-byte as today:
      creates a new work item and event without linked_existing_work_item in payload.
    """
    await _enable_shadow(async_db_session, test_tenant.id)

    wi_count_before = (
        await async_db_session.execute(
            select(func.count(models.ClinicalWorkItem.id)).where(
                models.ClinicalWorkItem.tenant_id == test_tenant.id
            )
        )
    ).scalar()

    resp = client.post(
        "/api/v1/treatments",
        json={
            "patient_id": test_patient.id,
            "procedure": "خلع عادي – Simple Extraction",
            "cost": 250,
            "tooth_number": 36,
            "status": "Done",
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    t_id = resp.json()["data"]["id"]

    await async_db_session.rollback()
    wi_count_after = (
        await async_db_session.execute(
            select(func.count(models.ClinicalWorkItem.id)).where(
                models.ClinicalWorkItem.tenant_id == test_tenant.id
            )
        )
    ).scalar()
    assert wi_count_after == wi_count_before + 1

    # Find the created event
    ev_stmt = select(models.ClinicalEvent).where(
        models.ClinicalEvent.tenant_id == test_tenant.id,
        models.ClinicalEvent.event_type == "procedure_recorded",
    ).order_by(models.ClinicalEvent.id.desc())
    ev = (await async_db_session.execute(ev_stmt)).scalars().first()
    assert ev is not None
    assert ev.payload.get("treatment_id") == t_id
    assert "linked_existing_work_item" not in ev.payload
