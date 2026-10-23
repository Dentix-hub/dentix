"""
Unit and Integration Tests for Clinical Charge Service & Endpoints (Slice S33).

Covers:
- Pending row on native completion (flag ON)
- None when flag OFF
- Idempotent on repeat PATCH (only one charge created)
- None for legacy-synced item
- None and structured warning log when price unresolved
- Charge failure does not block completion (savepoint error tolerance, D6)
- Other tenant gets 404 (tenant isolation)
- State machine (invoiced -> * and voided -> * return 409)
- Optimistic version conflict returns 409
- Endpoints 404 when flag is OFF (clinical_vnext_finance_read / clinical_vnext_native_writes)
- RBAC: Receptionist allowed, Doctor denied 403
- Billing projection (G14-M03: legacy_treatment, clinical_charge, none)
- Finance invariance: patient balance, payments, and invoice outputs identical before and after.
"""

from decimal import Decimal
import logging
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from backend import models, schemas
from backend.auth import create_access_token
from backend.main import app
from backend.models.clinical_core import (
    CLINICAL_CHARGE_STATUS_INVOICED,
    CLINICAL_CHARGE_STATUS_PENDING,
    CLINICAL_CHARGE_STATUS_VOIDED,
    ClinicalCharge,
    ClinicalEvent,
    ClinicalWorkItem,
)
from backend.services.clinical_charge_service import (
    FEATURE_FLAG_CLINICAL_FINANCE_READ,
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    ClinicalChargeService,
)
from backend.services.feature_service import FeatureFlagService


@pytest.fixture
async def seed_data(async_db_session):
    """Seed test tenants, users, and patients."""
    tenant_1 = models.Tenant(name="Clinic Alpha", domain="alpha.example.com", is_active=True)
    tenant_2 = models.Tenant(name="Clinic Beta", domain="beta.example.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="doc_alpha",
        email="doc1@alpha.com",
        hashed_password="hashed-pass-1",
        role="doctor",
        is_active=True,
    )
    receptionist_1 = models.User(
        tenant_id=tenant_1.id,
        username="recep_alpha",
        email="recep1@alpha.com",
        hashed_password="hashed-pass-2",
        role="receptionist",
        is_active=True,
    )
    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="doc_beta",
        email="doc2@beta.com",
        hashed_password="hashed-pass-3",
        role="doctor",
        is_active=True,
    )
    receptionist_2 = models.User(
        tenant_id=tenant_2.id,
        username="recep_beta",
        email="recep2@beta.com",
        hashed_password="hashed-pass-4",
        role="receptionist",
        is_active=True,
    )
    async_db_session.add_all([doctor_1, receptionist_1, doctor_2, receptionist_2])
    await async_db_session.flush()

    patient_1 = models.Patient(
        tenant_id=tenant_1.id,
        name="Patient One",
        age=30,
        phone="+1234567890",
        medical_history="No history",
        notes="Patient 1 notes",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_2 = models.Patient(
        tenant_id=tenant_2.id,
        name="Patient Two",
        age=28,
        phone="+1987654321",
        medical_history="No history",
        notes="Patient 2 notes",
        assigned_doctor_id=doctor_2.id,
        is_deleted=False,
    )
    async_db_session.add_all([patient_1, patient_2])
    await async_db_session.flush()

    # Seed procedures with prices
    proc_composite = models.Procedure(
        tenant_id=tenant_1.id,
        name="REST_COMPOSITE",
        price=150.00,
    )
    proc_exam = models.Procedure(
        tenant_id=tenant_1.id,
        name="ENDO_RCT",
        price=300.00,
    )
    proc_unpriced = models.Procedure(
        tenant_id=tenant_1.id,
        name="SURG_EXTRACTION",
        price=0.00,
    )
    async_db_session.add_all([proc_composite, proc_exam, proc_unpriced])
    await async_db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "doctor_1": doctor_1,
        "receptionist_1": receptionist_1,
        "doctor_2": doctor_2,
        "receptionist_2": receptionist_2,
        "patient_1": patient_1,
        "patient_2": patient_2,
        "proc_composite": proc_composite,
        "proc_exam": proc_exam,
    }


def make_headers(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


async def set_feature_flag(db, tenant_id: int, flag_key: str, enabled: bool):
    stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == flag_key)
    flag = (await db.execute(stmt)).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key=flag_key,
            description=f"Flag {flag_key}",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        db.add(flag)
        await db.commit()
        await db.refresh(flag)
    await FeatureFlagService.set_tenant_override(db, tenant_id, flag_key, enabled)


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_pending_charge_created_on_native_completion(async_db_session, seed_data, async_client):
    """D1 & D2: Completing a native procedure creates a pending charge with resolved price."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    # 1. Create a planned procedure
    create_res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={
            "code": "REST_COMPOSITE",
            "status": "planned",
            "targets": [{"target_kind": "tooth", "tooth_key": "18"}],
        },
        headers=doc_hdrs,
    )
    assert create_res.status_code == 201
    wi_id = create_res.json()["data"]["id"]

    # Verify no charge row created yet
    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id)
    ch_before = (await async_db_session.execute(stmt_ch)).scalars().first()
    assert ch_before is None

    # 2. PATCH status to completed
    patch_res = await async_client.patch(
        f"/api/v1/patients/{p1}/clinical-work-items/{wi_id}",
        json={"status": "completed", "expected_version_id": 1},
        headers=doc_hdrs,
    )
    assert patch_res.status_code == 200

    # 3. Verify pending charge row exists
    ch_after = (await async_db_session.execute(stmt_ch)).scalars().first()
    assert ch_after is not None
    assert ch_after.tenant_id == t1
    assert ch_after.patient_id == p1
    assert ch_after.work_item_id == wi_id
    assert ch_after.status == CLINICAL_CHARGE_STATUS_PENDING
    assert Decimal(str(ch_after.amount)) == Decimal("150.00")
    assert Decimal(str(ch_after.discount)) == Decimal("0.00")
    assert ch_after.version_id == 1


@pytest.mark.asyncio
async def test_pending_charge_created_on_direct_completion(async_db_session, seed_data, async_client):
    """Native procedure created directly with status=completed produces a pending charge."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={
            "code": "REST_COMPOSITE",
            "status": "completed",
            "targets": [{"target_kind": "tooth", "tooth_key": "16"}],
        },
        headers=doc_hdrs,
    )
    assert res.status_code == 201
    wi_id = res.json()["data"]["id"]

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id)
    charge = (await async_db_session.execute(stmt_ch)).scalars().first()
    assert charge is not None
    assert charge.status == CLINICAL_CHARGE_STATUS_PENDING
    assert Decimal(str(charge.amount)) == Decimal("150.00")


@pytest.mark.asyncio
async def test_no_charge_when_native_writes_flag_off(async_db_session, seed_data, async_client):
    """When clinical_vnext_native_writes is OFF, command endpoints return 404 and no charge is created."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, False)

    res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={
            "code": "REST_COMPOSITE",
            "status": "completed",
            "targets": [{"target_kind": "tooth", "tooth_key": "16"}],
        },
        headers=doc_hdrs,
    )
    assert res.status_code == 404

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.tenant_id == t1)
    charges = (await async_db_session.execute(stmt_ch)).scalars().all()
    assert len(charges) == 0


@pytest.mark.asyncio
async def test_idempotent_on_repeat_patch(async_db_session, seed_data, async_client):
    """Repeating PATCH on an already-completed procedure does not duplicate charge rows."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    create_res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={
            "code": "REST_COMPOSITE",
            "status": "planned",
            "targets": [{"target_kind": "tooth", "tooth_key": "18"}],
        },
        headers=doc_hdrs,
    )
    wi_id = create_res.json()["data"]["id"]

    # First PATCH -> completed
    patch1 = await async_client.patch(
        f"/api/v1/patients/{p1}/clinical-work-items/{wi_id}",
        json={"status": "completed", "expected_version_id": 1},
        headers=doc_hdrs,
    )
    assert patch1.status_code == 200

    # Second PATCH -> update notes while keeping completed status
    patch2 = await async_client.patch(
        f"/api/v1/patients/{p1}/clinical-work-items/{wi_id}",
        json={"status": "completed", "notes": "Updated note", "expected_version_id": 2},
        headers=doc_hdrs,
    )
    assert patch2.status_code == 200

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id)
    charges = (await async_db_session.execute(stmt_ch)).scalars().all()
    assert len(charges) == 1


@pytest.mark.asyncio
async def test_no_charge_for_findings(async_db_session, seed_data, async_client):
    """D2: Only kind == 'procedure' work items produce charges. Findings produce no charge."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-findings",
        json={
            "code": "CARIES",
            "status": "completed",
            "targets": [{"target_kind": "surface", "tooth_key": "16", "surface_code": "O"}],
        },
        headers=doc_hdrs,
    )
    assert res.status_code == 201
    wi_id = res.json()["data"]["id"]

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id)
    charges = (await async_db_session.execute(stmt_ch)).scalars().all()
    assert len(charges) == 0


@pytest.mark.asyncio
async def test_no_charge_for_legacy_synced_item(async_db_session, seed_data):
    """D4: Legacy-synced work items get no charge row."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    # Create a legacy-synced work item (has ClinicalEvent with treatment_id)
    wi = ClinicalWorkItem(
        tenant_id=t1,
        patient_id=p1,
        kind="procedure",
        code="REST_COMPOSITE",
        status="completed",
        version_id=1,
    )
    async_db_session.add(wi)
    await async_db_session.flush()

    ev = ClinicalEvent(
        tenant_id=t1,
        patient_id=p1,
        work_item_id=wi.id,
        event_type="procedure_recorded",
        payload={"treatment_id": 999, "kind": "procedure"},
    )
    async_db_session.add(ev)
    await async_db_session.commit()

    service = ClinicalChargeService(async_db_session, t1, seed_data["doctor_1"])
    charge = await service.create_pending_for_work_item(wi.id)
    assert charge is None

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi.id)
    res = (await async_db_session.execute(stmt_ch)).scalars().all()
    assert len(res) == 0


@pytest.mark.asyncio
async def test_unresolved_price_emits_warning_log_and_no_charge(async_db_session, seed_data, async_client, caplog):
    """D3: If no price resolves, create no row, emit structured warning log with work_item_id and tenant_id."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    with caplog.at_level(logging.WARNING):
        res = await async_client.post(
            f"/api/v1/patients/{p1}/clinical-procedures",
            json={
                "code": "SURG_EXTRACTION",  # priced at 0.00
                "status": "completed",
                "targets": [{"target_kind": "tooth", "tooth_key": "17"}],
            },
            headers=doc_hdrs,
        )
    assert res.status_code == 201
    wi_id = res.json()["data"]["id"]

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id)
    charge = (await async_db_session.execute(stmt_ch)).scalars().first()
    assert charge is None

    # Check warning log contains work_item_id and tenant_id
    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING and "clinical_charge_skipped_unresolved_price" in r.message]
    assert len(warning_records) >= 1
    rec = warning_records[0]
    assert str(wi_id) in rec.message
    assert str(t1) in rec.message


@pytest.mark.asyncio
async def test_charge_failure_never_blocks_completion(async_db_session, seed_data, async_client):
    """D6: Charge creation failure inside savepoint never blocks clinical completion."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    create_res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={
            "code": "REST_COMPOSITE",
            "status": "planned",
            "targets": [{"target_kind": "tooth", "tooth_key": "18"}],
        },
        headers=doc_hdrs,
    )
    wi_id = create_res.json()["data"]["id"]

    # Mock charge creation to simulate an unexpected error
    with patch(
        "backend.services.clinical_charge_service.ClinicalChargeService.create_pending_for_work_item",
        side_effect=Exception("Simulated charge failure"),
    ):
        patch_res = await async_client.patch(
            f"/api/v1/patients/{p1}/clinical-work-items/{wi_id}",
            json={"status": "completed", "expected_version_id": 1},
            headers=doc_hdrs,
        )
        # Clinical completion MUST succeed regardless of charge creation failure
        assert patch_res.status_code == 200
        assert patch_res.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_reception_invoice_and_void_state_machine(async_db_session, seed_data, async_client):
    """D5: Reception moves pending -> invoiced and pending -> voided. Other transitions 409."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])
    recep_hdrs = make_headers(seed_data["receptionist_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    # 1. Create two completed procedures -> 2 pending charges
    res1 = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "REST_COMPOSITE", "status": "completed", "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
        headers=doc_hdrs,
    )
    res2 = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "ENDO_RCT", "status": "completed", "targets": [{"target_kind": "tooth", "tooth_key": "12"}]},
        headers=doc_hdrs,
    )
    wi_1 = res1.json()["data"]["id"]
    wi_2 = res2.json()["data"]["id"]

    stmt1 = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_1)
    ch1 = (await async_db_session.execute(stmt1)).scalars().first()
    stmt2 = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_2)
    ch2 = (await async_db_session.execute(stmt2)).scalars().first()

    # 2. Invoice charge 1
    inv_res = await async_client.post(
        f"/api/v1/clinical-charges/{ch1.id}/invoice",
        json={"expected_version_id": 1, "notes": "Invoiced by front desk"},
        headers=recep_hdrs,
    )
    assert inv_res.status_code == 200
    assert inv_res.json()["data"]["status"] == CLINICAL_CHARGE_STATUS_INVOICED
    assert inv_res.json()["data"]["version_id"] == 2

    # Invoiced -> Invoiced or Voided must return 409
    repeat_inv = await async_client.post(
        f"/api/v1/clinical-charges/{ch1.id}/invoice",
        headers=recep_hdrs,
    )
    assert repeat_inv.status_code == 409

    void_inv = await async_client.post(
        f"/api/v1/clinical-charges/{ch1.id}/void",
        headers=recep_hdrs,
    )
    assert void_inv.status_code == 409

    # 3. Void charge 2
    void_res = await async_client.post(
        f"/api/v1/clinical-charges/{ch2.id}/void",
        json={"expected_version_id": 1, "notes": "Voided by front desk"},
        headers=recep_hdrs,
    )
    assert void_res.status_code == 200
    assert void_res.json()["data"]["status"] == CLINICAL_CHARGE_STATUS_VOIDED
    assert void_res.json()["data"]["version_id"] == 2

    # Voided -> Invoiced or Voided must return 409
    inv_void = await async_client.post(
        f"/api/v1/clinical-charges/{ch2.id}/invoice",
        headers=recep_hdrs,
    )
    assert inv_void.status_code == 409


@pytest.mark.asyncio
async def test_version_conflict_409(async_db_session, seed_data, async_client):
    """Optimistic lock: stale expected_version_id returns 409."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])
    recep_hdrs = make_headers(seed_data["receptionist_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "REST_COMPOSITE", "status": "completed", "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
        headers=doc_hdrs,
    )
    wi_id = res.json()["data"]["id"]
    ch = (await async_db_session.execute(select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id))).scalars().first()

    # Pass expected_version_id = 999
    conflict_res = await async_client.post(
        f"/api/v1/clinical-charges/{ch.id}/invoice",
        json={"expected_version_id": 999},
        headers=recep_hdrs,
    )
    assert conflict_res.status_code == 409
    assert "Stale version" in conflict_res.json()["detail"]


@pytest.mark.asyncio
async def test_endpoints_fail_closed_when_flags_off(async_db_session, seed_data, async_client):
    """D7: GET fails closed on clinical_vnext_finance_read; POST actions fail closed on clinical_vnext_native_writes."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    recep_hdrs = make_headers(seed_data["receptionist_1"])

    # Ensure flags are OFF
    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_FINANCE_READ, False)
    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, False)

    # 1. GET /patients/{id}/clinical-charges -> 404
    get_res = await async_client.get(
        f"/api/v1/patients/{p1}/clinical-charges",
        headers=recep_hdrs,
    )
    assert get_res.status_code == 404

    # 2. POST /clinical-charges/{id}/invoice -> 404
    inv_res = await async_client.post(
        f"/api/v1/clinical-charges/1/invoice",
        headers=recep_hdrs,
    )
    assert inv_res.status_code == 404

    # 3. POST /clinical-charges/{id}/void -> 404
    void_res = await async_client.post(
        f"/api/v1/clinical-charges/1/void",
        headers=recep_hdrs,
    )
    assert void_res.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_404(async_db_session, seed_data, async_client):
    """Tenant isolation: users from Clinic Beta cannot read or mutate charges belonging to Clinic Alpha."""
    t1 = seed_data["tenant_1"].id
    t2 = seed_data["tenant_2"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs_t1 = make_headers(seed_data["doctor_1"])
    recep_hdrs_t2 = make_headers(seed_data["receptionist_2"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)
    await set_feature_flag(async_db_session, t2, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)
    await set_feature_flag(async_db_session, t2, FEATURE_FLAG_CLINICAL_FINANCE_READ, True)

    # Create charge in tenant 1
    res = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "REST_COMPOSITE", "status": "completed", "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
        headers=doc_hdrs_t1,
    )
    wi_id = res.json()["data"]["id"]
    ch = (await async_db_session.execute(select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id))).scalars().first()

    # Tenant 2 receptionist attempts to access Tenant 1 patient charges -> 404
    cross_get = await async_client.get(
        f"/api/v1/patients/{p1}/clinical-charges",
        headers=recep_hdrs_t2,
    )
    assert cross_get.status_code == 404

    # Tenant 2 receptionist attempts to invoice Tenant 1 charge -> 404
    cross_inv = await async_client.post(
        f"/api/v1/clinical-charges/{ch.id}/invoice",
        headers=recep_hdrs_t2,
    )
    assert cross_inv.status_code == 404


@pytest.mark.asyncio
async def test_rbac_reception_allowed_doctor_denied(async_db_session, seed_data, async_client):
    """RBAC: Receptionist has RECEIVABLE_READ and can access charges; Doctor does not and gets 403."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])
    recep_hdrs = make_headers(seed_data["receptionist_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_FINANCE_READ, True)
    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)

    # Doctor gets 403 on charges read
    doc_get = await async_client.get(
        f"/api/v1/patients/{p1}/clinical-charges",
        headers=doc_hdrs,
    )
    assert doc_get.status_code == 403

    # Receptionist gets 200
    recep_get = await async_client.get(
        f"/api/v1/patients/{p1}/clinical-charges",
        headers=recep_hdrs,
    )
    assert recep_get.status_code == 200


@pytest.mark.asyncio
async def test_billing_projection_sources(async_db_session, seed_data, async_client):
    """G14-M03: Projection correctly categorizes work items into legacy_treatment, clinical_charge, none."""
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])
    recep_hdrs = make_headers(seed_data["receptionist_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)
    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_FINANCE_READ, True)

    # 1. Legacy treatment + synced work item
    tx = models.Treatment(
        tenant_id=t1,
        patient_id=p1,
        procedure="Composite Filling",
        cost=200.00,
        discount=20.00,
        status="Done",
    )
    async_db_session.add(tx)
    await async_db_session.flush()

    wi_legacy = ClinicalWorkItem(
        tenant_id=t1,
        patient_id=p1,
        kind="procedure",
        code="REST_COMPOSITE",
        status="completed",
        version_id=1,
    )
    async_db_session.add(wi_legacy)
    await async_db_session.flush()

    ev_legacy = ClinicalEvent(
        tenant_id=t1,
        patient_id=p1,
        work_item_id=wi_legacy.id,
        event_type="procedure_recorded",
        payload={"treatment_id": tx.id, "kind": "procedure"},
    )
    async_db_session.add(ev_legacy)
    await async_db_session.commit()

    # 2. Native completed procedure (clinical_charge)
    res_native = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "ENDO_RCT", "status": "completed", "targets": [{"target_kind": "tooth", "tooth_key": "12"}]},
        headers=doc_hdrs,
    )
    wi_native_id = res_native.json()["data"]["id"]

    # 3. Planned procedure (no charge)
    res_planned = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "REST_COMPOSITE", "status": "planned", "targets": [{"target_kind": "tooth", "tooth_key": "14"}]},
        headers=doc_hdrs,
    )
    wi_planned_id = res_planned.json()["data"]["id"]

    # Call GET clinical-charges
    get_res = await async_client.get(
        f"/api/v1/patients/{p1}/clinical-charges",
        headers=recep_hdrs,
    )
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    projection = data["projection"]

    proj_map = {item["work_item_id"]: item for item in projection}

    # Item 1: Legacy treatment
    item_legacy = proj_map[wi_legacy.id]
    assert item_legacy["source"] == "legacy_treatment"
    assert item_legacy["amount"] == 200.0
    assert item_legacy["discount"] == 20.0
    assert item_legacy["treatment_id"] == tx.id
    assert item_legacy["charge_id"] is None

    # Item 2: Native charge
    item_native = proj_map[wi_native_id]
    assert item_native["source"] == "clinical_charge"
    assert item_native["amount"] == 300.0
    assert item_native["discount"] == 0.0
    assert item_native["status"] == "pending"
    assert item_native["charge_id"] is not None
    assert item_native["treatment_id"] is None

    # Item 3: Planned (none)
    item_planned = proj_map[wi_planned_id]
    assert item_planned["source"] == "none"
    assert item_planned["amount"] is None
    assert item_planned["discount"] is None
    assert item_planned["charge_id"] is None
    assert item_planned["treatment_id"] is None


@pytest.mark.asyncio
async def test_finance_invariance(async_db_session, seed_data, async_client):
    """
    Finance Invariance Guarantee:
    Creating, invoicing, or voiding a clinical charge NEVER modifies Treatment rows,
    Payment rows, or patient balance. Legacy finance outputs are 100% identical before and after.
    """
    t1 = seed_data["tenant_1"].id
    p1 = seed_data["patient_1"].id
    doc_hdrs = make_headers(seed_data["doctor_1"])
    recep_hdrs = make_headers(seed_data["receptionist_1"])

    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True)
    await set_feature_flag(async_db_session, t1, FEATURE_FLAG_CLINICAL_FINANCE_READ, True)

    # Seed an existing Treatment and Payment for patient_1
    treatment_1 = models.Treatment(
        tenant_id=t1,
        patient_id=p1,
        procedure="Crown Preparation",
        cost=500.00,
        discount=50.00,
        status="Done",
    )
    payment_1 = models.Payment(
        tenant_id=t1,
        patient_id=p1,
        amount=200.00,
        notes="Initial payment",
    )
    async_db_session.add_all([treatment_1, payment_1])
    await async_db_session.commit()

    # Capture initial financial state
    stmt_tx_count = select(func.count(models.Treatment.id)).where(models.Treatment.tenant_id == t1)
    stmt_pmt_count = select(func.count(models.Payment.id)).where(models.Payment.tenant_id == t1)

    initial_tx_count = (await async_db_session.execute(stmt_tx_count)).scalar()
    initial_pmt_count = (await async_db_session.execute(stmt_pmt_count)).scalar()

    # Capture initial patient payments endpoint response
    res_pmts_before = await async_client.get(
        f"/api/v1/patients/{p1}/payments",
        headers=recep_hdrs,
    )
    assert res_pmts_before.status_code == 200
    pmts_data_before = res_pmts_before.json()

    # Capture initial patient invoice endpoint response
    res_inv_before = await async_client.get(
        f"/api/v1/patients/{p1}/invoice",
        headers=recep_hdrs,
    )
    assert res_inv_before.status_code == 200
    inv_data_before = res_inv_before.json()

    # Now perform native procedure completion -> creates pending charge
    res_proc = await async_client.post(
        f"/api/v1/patients/{p1}/clinical-procedures",
        json={"code": "REST_COMPOSITE", "status": "completed", "targets": [{"target_kind": "tooth", "tooth_key": "11"}]},
        headers=doc_hdrs,
    )
    assert res_proc.status_code == 201
    wi_id = res_proc.json()["data"]["id"]

    stmt_ch = select(ClinicalCharge).where(ClinicalCharge.work_item_id == wi_id)
    charge = (await async_db_session.execute(stmt_ch)).scalars().first()
    assert charge is not None

    # Perform reception invoice action
    res_inv_action = await async_client.post(
        f"/api/v1/clinical-charges/{charge.id}/invoice",
        json={"expected_version_id": 1},
        headers=recep_hdrs,
    )
    assert res_inv_action.status_code == 200

    # Verify counts remain 100% identical
    final_tx_count = (await async_db_session.execute(stmt_tx_count)).scalar()
    final_pmt_count = (await async_db_session.execute(stmt_pmt_count)).scalar()

    assert final_tx_count == initial_tx_count
    assert final_pmt_count == initial_pmt_count

    # Verify patient payments response data is identical
    res_pmts_after = await async_client.get(
        f"/api/v1/patients/{p1}/payments",
        headers=recep_hdrs,
    )
    assert res_pmts_after.json()["data"] == pmts_data_before["data"]

    # Verify patient invoice response data is identical
    res_inv_after = await async_client.get(
        f"/api/v1/patients/{p1}/invoice",
        headers=recep_hdrs,
    )
    assert res_inv_after.json()["data"] == inv_data_before["data"]
