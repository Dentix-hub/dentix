"""
Deterministic Verification for Slice S28: Lab Requirement Definition, Ready Trigger,
One-Tap Handoff & Non-Duplicating Billing.

Covers:
- G12-M04: Lab requirement definition (PROS_CROWN, PROS_BRIDGE, IMPLANT_CROWN, PROS_DENTURE).
- G12-M05: Lab-ready trigger (workflow step signals lab handoff readiness).
- G12-M06: One-tap lab handoff sheet endpoint (POST /patients/{id}/clinical-work-items/{id}/lab-handoff).
- G12-M08: Create lab order without duplicate treatment (when work_item_id is set, creates 0 treatments).
- G12-M09: Decouple lab price from synthetic treatment creation (prevent double billing per R06).
- G12-M16: Handoff idempotency (duplicate submit returns existing order without creating duplicate rows).
- Invariant R06: Zero synthetic Treatment rows created on lab handoff.
"""

from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func

from backend import models, schemas
from backend.clinical.catalog import (
    LAB_REQUIRED_PROCEDURE_CODES,
    ProcedureCode,
    is_lab_required_procedure,
)
from backend.clinical.workflow_templates import (
    LAB_READY_STEP_CODES,
    is_lab_ready_step,
    is_procedure_lab_ready,
)
from backend.routers.laboratories import (
    create_clinical_lab_handoff,
    create_lab_order,
)
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService


# ===========================================================================
# Unit Tests: G12-M04 (Lab Requirement) & G12-M05 (Lab-Ready Trigger)
# ===========================================================================

def test_g12_m04_lab_requirement_definition():
    """Verify lab requirement metadata on catalog procedures (G12-M04)."""
    assert ProcedureCode.PROS_CROWN.value in LAB_REQUIRED_PROCEDURE_CODES
    assert ProcedureCode.PROS_BRIDGE.value in LAB_REQUIRED_PROCEDURE_CODES
    assert ProcedureCode.IMPLANT_CROWN.value in LAB_REQUIRED_PROCEDURE_CODES
    assert ProcedureCode.PROS_DENTURE.value in LAB_REQUIRED_PROCEDURE_CODES

    assert is_lab_required_procedure("PROS_CROWN") is True
    assert is_lab_required_procedure("PROS_BRIDGE") is True
    assert is_lab_required_procedure("IMPLANT_CROWN") is True
    assert is_lab_required_procedure("PROS_DENTURE") is True

    # Non-lab procedures must return False
    assert is_lab_required_procedure("REST_COMPOSITE") is False
    assert is_lab_required_procedure("ENDO_RCT") is False
    assert is_lab_required_procedure("SURG_EXTRACTION") is False
    assert is_lab_required_procedure("IMPLANT_FIXTURE") is False
    assert is_lab_required_procedure("UNKNOWN_CODE") is False
    assert is_lab_required_procedure("") is False


def test_g12_m05_lab_ready_step_triggers():
    """Verify lab-ready step trigger identification (G12-M05)."""
    for step in ("preparation", "abutment_preparation", "impression_scan", "impression", "lab"):
        assert is_lab_ready_step(step) is True
        assert step in LAB_READY_STEP_CODES

    # Non-lab steps must return False
    assert is_lab_ready_step("assessment") is False
    assert is_lab_ready_step("access") is False
    assert is_lab_ready_step("clean_shape") is False
    assert is_lab_ready_step("obturate") is False
    assert is_lab_ready_step("finish_polish") is False

    # Procedure-level readiness
    assert is_procedure_lab_ready("PROS_CROWN", ["preparation"]) is True
    assert is_procedure_lab_ready("PROS_CROWN", ["impression_scan"]) is True
    assert is_procedure_lab_ready("PROS_CROWN", ["assessment"]) is False
    assert is_procedure_lab_ready("REST_COMPOSITE", ["preparation"]) is False


# ===========================================================================
# Fixture: Multi-Tenant Data Setup with Gated Feature Flag
# ===========================================================================

@pytest.fixture
async def seed_lab_data(async_db_session):
    """Seed tenants, doctors, patients, laboratories, and clinical work items."""
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
        notes="",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_2 = models.Patient(
        tenant_id=tenant_2.id,
        name="Omar Farooq",
        age=42,
        phone="+966500000002",
        medical_history="None",
        notes="",
        assigned_doctor_id=doctor_2.id,
        is_deleted=False,
    )
    async_db_session.add_all([patient_1, patient_2])
    await async_db_session.flush()

    lab_1 = models.Laboratory(
        tenant_id=tenant_1.id,
        name="Apex Ceramic Lab",
        phone="0501112233",
        is_active=True,
    )
    lab_2 = models.Laboratory(
        tenant_id=tenant_2.id,
        name="Other City Lab",
        phone="0509998877",
        is_active=True,
    )
    async_db_session.add_all([lab_1, lab_2])
    await async_db_session.flush()

    # Clinical work item for Crown on tooth 21
    work_item_crown = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        code="PROS_CROWN",
        kind="procedure",
        status="active",
        created_by_user_id=doctor_1.id,
    )
    async_db_session.add(work_item_crown)
    await async_db_session.flush()

    target_21 = models.ClinicalWorkItemTarget(
        tenant_id=tenant_1.id,
        work_item_id=work_item_crown.id,
        target_kind="tooth",
        tooth_key="21",
    )
    async_db_session.add(target_21)
    await async_db_session.flush()

    # Enable native writes feature flag for Tenant 1
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
        "lab_1": lab_1,
        "lab_2": lab_2,
        "work_item_crown": work_item_crown,
    }


# ===========================================================================
# Integration Tests: G12-M06, G12-M08, G12-M09, G12-M16 (Non-Duplicating Billing & Idempotency)
# ===========================================================================

@pytest.mark.asyncio
async def test_lab_handoff_creates_lab_order_with_zero_synthetic_treatments(
    async_db_session, seed_lab_data
):
    """
    G12-M06, G12-M08, G12-M09 / Invariant R06:
    Calling 1-tap lab handoff endpoint creates a LabOrder linked to work_item_id
    and creates EXACTLY 0 synthetic Treatment rows.
    """
    t1 = seed_lab_data["tenant_1"]
    doc1 = seed_lab_data["doctor_1"]
    pat1 = seed_lab_data["patient_1"]
    lab1 = seed_lab_data["lab_1"]
    wi_crown = seed_lab_data["work_item_crown"]

    # Initial Treatment rows count must be 0
    initial_treatments_count = await async_db_session.scalar(
        select(func.count(models.Treatment.id)).where(
            models.Treatment.tenant_id == t1.id,
            models.Treatment.patient_id == pat1.id,
        )
    )
    assert initial_treatments_count == 0

    payload = schemas.LabHandoffCreate(
        laboratory_id=lab1.id,
        work_type="Crown Restoration",
        shade="A2",
        material="Zirconia",
        cost=Decimal("350.00"),
        price_to_patient=Decimal("1500.00"),
        notes="Please ensure tight contact with tooth 22",
    )

    response = await create_clinical_lab_handoff(
        patient_id=pat1.id,
        work_item_id=wi_crown.id,
        payload=payload,
        db=async_db_session,
        current_user=doc1,
    )

    # Validate response
    order_data = response.get("data")
    assert order_data is not None
    assert order_data["work_item_id"] == wi_crown.id
    assert order_data["patient_id"] == pat1.id
    assert order_data["laboratory_id"] == lab1.id
    assert order_data["tooth_number"] == "21"  # auto-extracted from work item targets
    assert order_data["shade"] == "A2"
    assert order_data["material"] == "Zirconia"
    assert float(order_data["cost"]) == 350.00
    assert float(order_data["price_to_patient"]) == 1500.00
    assert order_data["status"] == "pending"

    # INVARIANT R06: EXACTLY ZERO synthetic Treatment rows must be created!
    final_treatments_count = await async_db_session.scalar(
        select(func.count(models.Treatment.id)).where(
            models.Treatment.tenant_id == t1.id,
            models.Treatment.patient_id == pat1.id,
        )
    )
    assert final_treatments_count == 0, (
        f"Expected 0 synthetic Treatment rows, found {final_treatments_count}! "
        "Double-billing invariant R06 violated."
    )


@pytest.mark.asyncio
async def test_lab_handoff_idempotency_returns_existing_order(
    async_db_session, seed_lab_data
):
    """
    G12-M16:
    Calling 1-tap lab handoff multiple times with the same work item returns
    the existing LabOrder idempotently without creating duplicate rows.
    """
    t1 = seed_lab_data["tenant_1"]
    doc1 = seed_lab_data["doctor_1"]
    pat1 = seed_lab_data["patient_1"]
    lab1 = seed_lab_data["lab_1"]
    wi_crown = seed_lab_data["work_item_crown"]

    payload = schemas.LabHandoffCreate(
        laboratory_id=lab1.id,
        work_type="Crown Restoration",
        shade="A1",
        material="E-Max",
        cost=Decimal("400.00"),
        price_to_patient=Decimal("1800.00"),
    )

    # First dispatch
    res1 = await create_clinical_lab_handoff(
        patient_id=pat1.id,
        work_item_id=wi_crown.id,
        payload=payload,
        db=async_db_session,
        current_user=doc1,
    )
    order_id_1 = res1["data"]["id"]

    # Second dispatch (simulating double click or network retry)
    res2 = await create_clinical_lab_handoff(
        patient_id=pat1.id,
        work_item_id=wi_crown.id,
        payload=payload,
        db=async_db_session,
        current_user=doc1,
    )
    order_id_2 = res2["data"]["id"]

    # Must be identical order ID
    assert order_id_1 == order_id_2

    # Exactly 1 LabOrder row in the database
    orders_count = await async_db_session.scalar(
        select(func.count(models.LabOrder.id)).where(
            models.LabOrder.tenant_id == t1.id,
            models.LabOrder.work_item_id == wi_crown.id,
        )
    )
    assert orders_count == 1

    # Exactly 0 Treatment rows
    treatments_count = await async_db_session.scalar(
        select(func.count(models.Treatment.id)).where(
            models.Treatment.tenant_id == t1.id,
            models.Treatment.patient_id == pat1.id,
        )
    )
    assert treatments_count == 0


@pytest.mark.asyncio
async def test_create_lab_order_with_work_item_creates_zero_synthetic_treatments(
    async_db_session, seed_lab_data
):
    """
    G12-M08, G12-M09 / R06 via standard POST /api/v1/lab-orders:
    When work_item_id is provided, 0 synthetic treatments are created.
    When work_item_id is NOT provided, legacy behavior creates 1 synthetic treatment.
    """
    t1 = seed_lab_data["tenant_1"]
    doc1 = seed_lab_data["doctor_1"]
    pat1 = seed_lab_data["patient_1"]
    lab1 = seed_lab_data["lab_1"]
    wi_crown = seed_lab_data["work_item_crown"]

    # 1. Native V-Next order with work_item_id
    native_order_req = schemas.LabOrderCreate(
        patient_id=pat1.id,
        laboratory_id=lab1.id,
        work_item_id=wi_crown.id,
        work_type="Crown Restoration",
        tooth_number="21",
        price_to_patient=Decimal("1200.00"),
        cost=Decimal("300.00"),
    )
    res_native = await create_lab_order(
        order=native_order_req,
        db=async_db_session,
        current_user=doc1,
    )
    assert res_native["data"]["work_item_id"] == wi_crown.id

    # ZERO treatments created for native order
    native_treatments_count = await async_db_session.scalar(
        select(func.count(models.Treatment.id)).where(
            models.Treatment.tenant_id == t1.id,
            models.Treatment.patient_id == pat1.id,
        )
    )
    assert native_treatments_count == 0

    # 2. Pure legacy order without work_item_id
    legacy_order_req = schemas.LabOrderCreate(
        patient_id=pat1.id,
        laboratory_id=lab1.id,
        work_item_id=None,
        work_type="Legacy Denture",
        tooth_number="11",
        price_to_patient=Decimal("500.00"),
        cost=Decimal("150.00"),
    )
    res_legacy = await create_lab_order(
        order=legacy_order_req,
        db=async_db_session,
        current_user=doc1,
    )
    assert res_legacy["data"]["work_item_id"] is None

    # Exactly 1 treatment created for legacy order
    legacy_treatments_count = await async_db_session.scalar(
        select(func.count(models.Treatment.id)).where(
            models.Treatment.tenant_id == t1.id,
            models.Treatment.patient_id == pat1.id,
        )
    )
    assert legacy_treatments_count == 1


@pytest.mark.asyncio
async def test_lab_handoff_fails_closed_when_native_writes_disabled(
    async_db_session, seed_lab_data
):
    """Fail-closed gate: returns 404 when clinical_vnext_native_writes is OFF."""
    t1 = seed_lab_data["tenant_1"]
    doc1 = seed_lab_data["doctor_1"]
    pat1 = seed_lab_data["patient_1"]
    lab1 = seed_lab_data["lab_1"]
    wi_crown = seed_lab_data["work_item_crown"]

    # Disable flag
    await FeatureFlagService.set_tenant_override(
        async_db_session, t1.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, False
    )
    await async_db_session.commit()

    payload = schemas.LabHandoffCreate(laboratory_id=lab1.id)

    with pytest.raises(HTTPException) as exc_info:
        await create_clinical_lab_handoff(
            patient_id=pat1.id,
            work_item_id=wi_crown.id,
            payload=payload,
            db=async_db_session,
            current_user=doc1,
        )
    assert exc_info.value.status_code == 404
    assert "Clinical native writes are disabled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_lab_handoff_tenant_isolation(async_db_session, seed_lab_data):
    """Cross-tenant access fails closed with 404."""
    doc2 = seed_lab_data["doctor_2"]  # Tenant 2 doctor
    pat1 = seed_lab_data["patient_1"]  # Tenant 1 patient
    lab2 = seed_lab_data["lab_2"]      # Tenant 2 lab
    wi_crown = seed_lab_data["work_item_crown"]  # Tenant 1 work item

    payload = schemas.LabHandoffCreate(laboratory_id=lab2.id)

    # Tenant 2 doctor cannot access Tenant 1 patient or work item
    with pytest.raises(HTTPException) as exc_info:
        await create_clinical_lab_handoff(
            patient_id=pat1.id,
            work_item_id=wi_crown.id,
            payload=payload,
            db=async_db_session,
            current_user=doc2,
        )
    assert exc_info.value.status_code == 404
