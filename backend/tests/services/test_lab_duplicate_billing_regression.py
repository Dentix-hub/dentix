"""
Duplicate Billing Regression Suite & Lab Status Sync Verification (Slice S29).

Covers:
- G12-M10: Add lab status mapping (Decision D4: 'completed' -> 'lab_ready', others -> 'unmapped').
- G12-M11: Reflect lab state in work item (lab_order_id, lab_status, lab_ready, shade, material).
- G12-M12: Prevent auto-complete when lab is ready (ClinicalWorkItem.status remains active).
- G12-M13: Add shade/material sync rules (bidirectional sync between care session observations and open lab orders).
- G12-M15: Add duplicate-billing regression test (lab handoff + delivery adds 0 duplicate treatments, 0 balance mutations).
"""

from decimal import Decimal
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend import models, schemas
from backend.clinical.catalog import map_lab_order_status
from backend.clinical.shade_material_sync import (
    sync_observation_to_open_lab_orders,
    sync_lab_order_to_active_care_session_observations,
)
from backend.routers.laboratories import (
    create_clinical_lab_handoff,
    update_lab_order,
)
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_workspace_service import (
    ClinicalWorkspaceService,
    FEATURE_FLAG_CLINICAL_PRIMARY,
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
)
from backend.services.feature_service import FeatureFlagService
from backend.services.lab_service import LabService


# ===========================================================================
# G12-M10: Lab Status Mapping (Unit Verification)
# ===========================================================================

def test_g12_m10_lab_status_mapping_d4():
    """Verify D4 mapping rule: 'completed' -> 'lab_ready', any other -> 'unmapped'."""
    assert map_lab_order_status("completed") == "lab_ready"
    assert map_lab_order_status("COMPLETED") == "lab_ready"
    assert map_lab_order_status(" Completed ") == "lab_ready"

    # All other status strings must map to unmapped (neutral in UI)
    assert map_lab_order_status("pending") == "unmapped"
    assert map_lab_order_status("in_progress") == "unmapped"
    assert map_lab_order_status("delivered") == "unmapped"
    assert map_lab_order_status("cancelled") == "unmapped"
    assert map_lab_order_status("custom_clinic_state") == "unmapped"
    assert map_lab_order_status(None) == "unmapped"
    assert map_lab_order_status("") == "unmapped"


# ===========================================================================
# Helpers & Fixtures
# ===========================================================================

async def _seed_lab_context(db):
    tenant = models.Tenant(name="S29 Clinic", is_active=True)
    db.add(tenant)
    await db.flush()

    doctor = models.User(
        username="s29_doctor",
        email="s29_doctor@example.com",
        hashed_password="test-hashed-password",
        tenant_id=tenant.id,
        role="doctor",
        is_active=True,
    )
    db.add(doctor)
    await db.flush()

    patient = models.Patient(
        name="S29 Patient",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor.id,
        age=35,
        phone="+966500000001",
        medical_history="",
        notes="",
        is_deleted=False,
    )
    db.add(patient)
    await db.flush()

    laboratory = models.Laboratory(
        name="S29 Dental Tech",
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(laboratory)
    await db.flush()

    for f_key in [FEATURE_FLAG_CLINICAL_PRIMARY, FEATURE_FLAG_CLINICAL_NATIVE_WRITES]:
        stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == f_key)
        flag = (await db.execute(stmt)).scalar_one_or_none()
        if not flag:
            flag = models.FeatureFlag(
                key=f_key,
                description=f_key,
                is_global_enabled=True,
                rollout_percentage=0,
            )
            db.add(flag)
            await db.flush()

        await FeatureFlagService.set_tenant_override(db, tenant.id, f_key, True)

    return tenant, doctor, patient, laboratory


# ===========================================================================
# G12-M11: Reflect Lab State in Work Item (Model Properties & Schema Parity)
# ===========================================================================

@pytest.mark.asyncio
async def test_g12_m11_work_item_reflects_lab_state(async_db_session):
    """Verify ClinicalWorkItem properties & ClinicalWorkItemRead reflect linked lab order."""
    db = async_db_session
    tenant, doctor, patient, lab = await _seed_lab_context(db)

    wi = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=doctor.id,
    )
    db.add(wi)
    await db.flush()

    # Before lab order: work item has no linked lab
    assert wi.lab_order_id is None
    assert wi.lab_status is None
    assert wi.lab_ready is False
    assert wi.shade is None
    assert wi.material is None

    # Create linked lab order (status = 'pending')
    order = models.LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_item_id=wi.id,
        work_type="Porcelain Crown",
        tooth_number="21",
        shade="A2",
        material="Zirconia",
        status="pending",
    )
    db.add(order)
    await db.commit()

    # Re-query work item
    stmt = (
        select(models.ClinicalWorkItem)
        .options(selectinload(models.ClinicalWorkItem.targets))
        .where(models.ClinicalWorkItem.id == wi.id)
    )
    reloaded_wi = (await db.execute(stmt)).scalar_one()

    assert reloaded_wi.lab_order_id == order.id
    assert reloaded_wi.lab_status == "unmapped"
    assert reloaded_wi.lab_ready is False
    assert reloaded_wi.shade == "A2"
    assert reloaded_wi.material == "Zirconia"

    # Schema parity
    schema_read = schemas.ClinicalWorkItemRead.model_validate(reloaded_wi)
    assert schema_read.lab_order_id == order.id
    assert schema_read.lab_status == "unmapped"
    assert schema_read.lab_ready is False
    assert schema_read.shade == "A2"
    assert schema_read.material == "Zirconia"

    # Now update lab order status to 'completed'
    order.status = "completed"
    await db.commit()

    reloaded_wi2 = (await db.execute(stmt)).scalar_one()
    assert reloaded_wi2.lab_status == "lab_ready"
    assert reloaded_wi2.lab_ready is True

    schema_read2 = schemas.ClinicalWorkItemRead.model_validate(reloaded_wi2)
    assert schema_read2.lab_status == "lab_ready"
    assert schema_read2.lab_ready is True


# ===========================================================================
# G12-M12: Prevent Auto-Complete When Lab Is Ready (D4 Invariant)
# ===========================================================================

@pytest.mark.asyncio
async def test_g12_m12_prevent_autocomplete_when_lab_is_ready(async_db_session):
    """
    Verify Invariant D4: When lab order is marked 'completed',
    ClinicalWorkItem.status MUST NOT auto-transition to 'completed'; it remains 'active'.
    """
    db = async_db_session
    tenant, doctor, patient, lab = await _seed_lab_context(db)

    wi = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=doctor.id,
    )
    db.add(wi)
    await db.flush()

    order = models.LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_item_id=wi.id,
        work_type="Crown",
        tooth_number="21",
        status="in_progress",
    )
    db.add(order)
    await db.commit()

    # Update lab order to 'completed' via update_lab_order
    order_update = schemas.LabOrderUpdate(status="completed")
    res = await update_lab_order(
        order_id=order.id,
        order_update=order_update,
        db=db,
        current_user=doctor,
    )
    assert res["success"] is True

    # Verify work item status remains active (NOT completed)
    stmt = select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == wi.id)
    reloaded_wi = (await db.execute(stmt)).scalar_one()

    assert reloaded_wi.status == "active"
    assert reloaded_wi.lab_ready is True
    assert reloaded_wi.lab_status == "lab_ready"


# ===========================================================================
# G12-M13: Bidirectional Shade/Material Sync Rules
# ===========================================================================

@pytest.mark.asyncio
async def test_g12_m13_sync_observation_to_open_lab_order(async_db_session):
    """Care session observation -> open lab order shade sync (G12-M13)."""
    db = async_db_session
    tenant, doctor, patient, lab = await _seed_lab_context(db)

    wi = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=doctor.id,
    )
    db.add(wi)
    await db.flush()

    order = models.LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_item_id=wi.id,
        work_type="Crown",
        tooth_number="21",
        shade="A1",
        material="PFM",
        status="pending",
    )
    db.add(order)
    await db.commit()

    # Record shade observation on work item
    updated_orders = await sync_observation_to_open_lab_orders(
        db=db,
        tenant_id=tenant.id,
        work_item_id=wi.id,
        observation_code="color_shade",
        structured_value={"shade": "3M2"},
        notes="Updated shade",
    )
    assert len(updated_orders) == 1
    assert updated_orders[0].shade == "3M2"

    # Also test material observation
    mat_orders = await sync_observation_to_open_lab_orders(
        db=db,
        tenant_id=tenant.id,
        work_item_id=wi.id,
        observation_code="material",
        structured_value={"material": "Zirconia High Translucency"},
    )
    assert len(mat_orders) == 1
    assert mat_orders[0].material == "Zirconia High Translucency"


@pytest.mark.asyncio
async def test_g12_m13_sync_lab_order_to_active_care_session_observations(async_db_session):
    """Lab order shade/material update -> active care session observation sync (G12-M13)."""
    db = async_db_session
    tenant, doctor, patient, lab = await _seed_lab_context(db)

    # Active care session
    cs = models.CareSession(
        tenant_id=tenant.id,
        patient_id=patient.id,
        status="in_progress",
        provider_user_id=doctor.id,
    )
    db.add(cs)

    wi = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=doctor.id,
    )
    db.add(wi)
    await db.flush()

    order = models.LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_item_id=wi.id,
        work_type="Crown",
        tooth_number="21",
        shade="B1",
        material="E-Max",
        status="pending",
    )
    db.add(order)
    await db.commit()

    # Trigger sync from lab order to care session
    synced_obs = await sync_lab_order_to_active_care_session_observations(
        db=db,
        tenant_id=tenant.id,
        order=order,
        actor_user_id=doctor.id,
    )
    assert len(synced_obs) == 2
    shade_obs = next(o for o in synced_obs if o.observation_code == "color_shade")
    mat_obs = next(o for o in synced_obs if o.observation_code == "material")

    assert shade_obs.structured_value == {"shade": "B1"}
    assert mat_obs.structured_value == {"material": "E-Max"}


# ===========================================================================
# G12-M15: Duplicate-Billing Regression Suite (Invariant R06 Across Lifecycle)
# ===========================================================================

@pytest.mark.asyncio
async def test_g12_m15_duplicate_billing_regression_full_lifecycle(async_db_session):
    """
    Verify Invariant R06:
    Across full lab lifecycle (1-tap handoff -> update -> completed delivery):
    - Exactly 0 duplicate models.Treatment rows are created.
    - models.Treatment sum & models.Payment records have 0 delta.
    - ClinicalWorkItem remains active and non-duplicated.
    """
    db = async_db_session
    tenant, doctor, patient, lab = await _seed_lab_context(db)

    # Baseline: create one real treatment & payment
    base_treatment = models.Treatment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        tooth_number=21,
        procedure="Crown Preparation",
        cost=Decimal("1500.00"),
        discount=Decimal("0.00"),
        status="Done",
        is_deleted=False,
    )
    db.add(base_treatment)
    await db.flush()

    base_payment = models.Payment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        amount=Decimal("1000.00"),
    )
    db.add(base_payment)

    wi = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=doctor.id,
    )
    db.add(wi)
    await db.commit()

    async def _get_treatment_stats():
        t_count = (await db.execute(select(func.count(models.Treatment.id)).where(models.Treatment.patient_id == patient.id))).scalar()
        t_sum = (await db.execute(select(func.coalesce(func.sum(models.Treatment.cost - models.Treatment.discount), Decimal(0))).where(models.Treatment.patient_id == patient.id))).scalar()
        p_count = (await db.execute(select(func.count(models.Payment.id)).where(models.Payment.patient_id == patient.id))).scalar()
        return t_count, t_sum, p_count

    init_t_count, init_t_sum, init_p_count = await _get_treatment_stats()
    assert init_t_count == 1
    assert init_t_sum == Decimal("1500.00")
    assert init_p_count == 1

    # Stage 1: 1-Tap Lab Handoff
    handoff_payload = schemas.LabHandoffCreate(
        laboratory_id=lab.id,
        work_type="Zirconia Crown",
        tooth_number="21",
        shade="A2",
        material="Zirconia",
        cost=Decimal("300.00"),
        price_to_patient=Decimal("600.00"),
    )
    handoff_res = await create_clinical_lab_handoff(
        patient_id=patient.id,
        work_item_id=wi.id,
        payload=handoff_payload,
        db=db,
        current_user=doctor,
    )
    assert handoff_res["success"] is True
    lab_order_id = handoff_res["data"]["id"]

    t_count1, t_sum1, p_count1 = await _get_treatment_stats()
    assert t_count1 == init_t_count, "Zero synthetic treatments on 1-tap handoff!"
    assert t_sum1 == init_t_sum, "Zero balance delta on 1-tap handoff!"
    assert p_count1 == init_p_count

    # Stage 2: Update Lab Order
    update_payload = schemas.LabOrderUpdate(
        status="in_progress",
        shade="A3",
        cost=Decimal("350.00"),
        price_to_patient=Decimal("700.00"),
    )
    update_res = await update_lab_order(
        order_id=lab_order_id,
        order_update=update_payload,
        db=db,
        current_user=doctor,
    )
    assert update_res["success"] is True

    t_count2, t_sum2, p_count2 = await _get_treatment_stats()
    assert t_count2 == init_t_count, "Zero synthetic treatments on lab update!"
    assert t_sum2 == init_t_sum, "Zero balance delta on lab update!"

    # Stage 3: Mark Lab Order 'completed' (Delivery to clinic)
    finish_payload = schemas.LabOrderUpdate(status="completed")
    finish_res = await update_lab_order(
        order_id=lab_order_id,
        order_update=finish_payload,
        db=db,
        current_user=doctor,
    )
    assert finish_res["success"] is True

    t_count3, t_sum3, p_count3 = await _get_treatment_stats()
    assert t_count3 == init_t_count, "Zero synthetic treatments on lab completion / delivery!"
    assert t_sum3 == init_t_sum, "Patient balance remained strictly invariant across full lab lifecycle!"
    assert p_count3 == init_p_count

    # Verify work item state
    target_wi_id = wi.id
    db.expire_all()
    wi_stmt = select(models.ClinicalWorkItem).where(models.ClinicalWorkItem.id == target_wi_id)
    final_wi = (await db.execute(wi_stmt)).scalar_one()
    assert final_wi.status == "active", "Work item was NOT auto-completed (G12-M12)!"
    assert final_wi.lab_ready is True
    assert final_wi.lab_status == "lab_ready"


# ===========================================================================
# Workspace Snapshot Integration Verification
# ===========================================================================

@pytest.mark.asyncio
async def test_g12_workspace_snapshot_includes_lab_state(async_db_session):
    """Verify ClinicalWorkspaceSnapshot projection exposes lab state on work items."""
    db = async_db_session
    tenant, doctor, patient, lab = await _seed_lab_context(db)

    wi = models.ClinicalWorkItem(
        tenant_id=tenant.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=doctor.id,
    )
    db.add(wi)
    await db.flush()

    target = models.ClinicalWorkItemTarget(
        tenant_id=tenant.id,
        work_item_id=wi.id,
        target_kind="tooth",
        tooth_key="21",
    )
    db.add(target)

    order = models.LabOrder(
        tenant_id=tenant.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_item_id=wi.id,
        work_type="Crown",
        tooth_number="21",
        shade="A2",
        material="Zirconia",
        status="completed",
    )
    db.add(order)
    await db.commit()

    ws_service = ClinicalWorkspaceService(db, tenant.id, doctor)
    snapshot = await ws_service.get_workspace_snapshot(patient.id)

    matching_wis = [w for w in snapshot.work_items if w.id == wi.id or str(w.id) == str(wi.id)]
    assert len(matching_wis) == 1
    wi_summary = matching_wis[0]

    assert wi_summary.lab_order_id == order.id
    assert wi_summary.lab_status == "lab_ready"
    assert wi_summary.lab_ready is True
    assert wi_summary.shade == "A2"
    assert wi_summary.material == "Zirconia"
