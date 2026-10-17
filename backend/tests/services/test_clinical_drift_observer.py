"""
Tests for Clinical Drift and Mapping Error Observer Service (G16-M04, G16-M05).

Verifies:
1. Super-admin 200 on backfilled tenant: asserts len(missing_in_native_treatment_ids) == 0
   and verifies tooth_status_unbackfilled_count is reported separately (PD01b).
2. Tenant with un-backfilled treatment -> accurately reports missing_in_native_treatment_ids
   and patients_with_drift >= 1.
3. Tenant with unmapped procedure / invalid FDI -> increments unmapped_issue_count (G16-M04).
4. Tenant isolation: scanning Tenant 1 never reads or reports Tenant 2 patients.
5. Non-super-admin (Role.DOCTOR, Role.ADMIN with tenant_id=1) -> 403.
6. Non-existent tenant_id -> 404.
7. Zero-mutation proof: count of Treatment, ClinicalWorkItem, ClinicalEvent, Payment,
   and ClinicalProjectionCoverage before == after.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import func, select

from backend import models
from backend.services.clinical_drift_observer_service import ClinicalDriftObserverService


@pytest.fixture
async def observer_seed_data(async_db_session):
    """Seed tenants, users, patients, treatments, tooth status, work items and events."""
    db = async_db_session

    # Tenants
    t1 = models.Tenant(id=1, name="Clinic Alpha", is_active=True)
    t2 = models.Tenant(id=2, name="Clinic Beta", is_active=True)
    db.add_all([t1, t2])
    await db.flush()

    # Users
    u1 = models.User(
        id=10,
        username="dr_alpha",
        email="dr_alpha@example.com",
        hashed_password="fakehash",
        tenant_id=1,
        role="doctor",
    )
    u2 = models.User(
        id=20,
        username="dr_beta",
        email="dr_beta@example.com",
        hashed_password="fakehash",
        tenant_id=2,
        role="doctor",
    )
    db.add_all([u1, u2])
    await db.flush()

    # Patients
    p1 = models.Patient(
        id=1,
        name="Patient Alpha 1",
        age=30,
        phone="0123456789",
        medical_history="None",
        notes="",
        tenant_id=1,
    )
    p2 = models.Patient(
        id=2,
        name="Patient Beta 1",
        age=40,
        phone="0123456788",
        medical_history="None",
        notes="",
        tenant_id=2,
    )
    db.add_all([p1, p2])
    await db.flush()

    # Tenant 1: Backfilled Treatment 101 on Tooth 16 (Composite Filling)
    t101 = models.Treatment(
        id=101,
        tenant_id=1,
        patient_id=1,
        tooth_number=16,
        procedure="Composite Filling",
        status="Done",
        date=datetime.now(timezone.utc).replace(tzinfo=None),
        cost=200.0,
        discount=0.0,
        is_deleted=False,
    )
    db.add(t101)
    await db.flush()

    # Native work item and event for Treatment 101
    wi101 = models.ClinicalWorkItem(
        id=1001,
        tenant_id=1,
        patient_id=1,
        kind="procedure",
        code="REST_COMPOSITE",
        status="completed",
        notes="Backfilled",
    )
    db.add(wi101)
    await db.flush()

    ev101 = models.ClinicalEvent(
        id=5001,
        tenant_id=1,
        patient_id=1,
        work_item_id=1001,
        event_type="procedure_recorded",
        occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
        actor_user_id=10,
        payload={"treatment_id": 101, "kind": "procedure", "canonical_code": "REST_COMPOSITE"},
    )
    db.add(ev101)
    await db.flush()

    # ToothStatus row on Tooth 11 for Patient 1 (unbackfilled into native event)
    ts1 = models.ToothStatus(
        id=201,
        tenant_id=1,
        patient_id=1,
        tooth_number=11,
        condition="Caries",
        notes="Mild caries",
    )
    db.add(ts1)
    await db.flush()

    # Payment row in Tenant 1 (for mutation check)
    pay1 = models.Payment(
        id=301,
        tenant_id=1,
        patient_id=1,
        amount=200.0,
    )
    db.add(pay1)

    # Coverage row in Tenant 1 (for mutation check)
    cov1 = models.ClinicalProjectionCoverage(
        id=401,
        tenant_id=1,
        patient_id=1,
        domain="teeth",
        status="PARTIAL",
    )
    db.add(cov1)

    await db.commit()
    return {"t1": t1, "t2": t2, "p1": p1, "p2": p2, "t101": t101, "wi101": wi101, "ts1": ts1}


@pytest.mark.asyncio
async def test_super_admin_200_on_backfilled_tenant(
    client, observer_seed_data, super_admin_headers
):
    """
    Super-admin 200 on backfilled tenant: asserts len(missing_in_native_treatment_ids) == 0
    and verifies tooth_status_unbackfilled_count is reported separately (PD01b).
    """
    res = client.get("/api/v1/admin/clinical-drift/1", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["tenant_id"] == 1
    assert data["patients_scanned"] == 1
    assert len(data["missing_in_native_treatment_ids"]) == 0
    assert data["legacy_procedure_count"] == 1
    assert data["native_procedure_count"] == 1
    assert data["patients_with_drift"] == 0  # Treatment drift only per PD01b
    assert data["tooth_status_unbackfilled_count"] == 1  # Tracked separately
    assert data["unmapped_issue_count"] == 0


@pytest.mark.asyncio
async def test_tenant_with_unbackfilled_treatment(
    client, async_db_session, observer_seed_data, super_admin_headers
):
    """
    Tenant with un-backfilled treatment -> accurately reports missing_in_native_treatment_ids
    and patients_with_drift >= 1.
    """
    db = async_db_session
    # Add an un-backfilled treatment for Patient 1
    t102 = models.Treatment(
        id=102,
        tenant_id=1,
        patient_id=1,
        tooth_number=21,
        procedure="Simple Extraction",
        status="Done",
        date=datetime.now(timezone.utc).replace(tzinfo=None),
        cost=150.0,
        discount=0.0,
        is_deleted=False,
    )
    db.add(t102)
    await db.commit()

    res = client.get("/api/v1/admin/clinical-drift/1", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert 102 in data["missing_in_native_treatment_ids"]
    assert data["patients_with_drift"] == 1
    assert data["legacy_procedure_count"] == 2
    assert data["native_procedure_count"] == 1
    assert len(data["patient_drifts"]) == 1
    p_drift = data["patient_drifts"][0]
    assert p_drift["patient_id"] == 1
    assert 102 in p_drift["missing_treatment_ids"]
    assert p_drift["has_drift"] is True


@pytest.mark.asyncio
async def test_tenant_with_unmapped_procedure_or_invalid_fdi(
    client, async_db_session, observer_seed_data, super_admin_headers
):
    """
    Tenant with unmapped procedure / invalid FDI -> increments unmapped_issue_count (G16-M04).
    """
    db = async_db_session
    # Treatment with invalid FDI notation (tooth 99)
    t_invalid_tooth = models.Treatment(
        id=103,
        tenant_id=1,
        patient_id=1,
        tooth_number=99,
        procedure="Composite Filling",
        status="Done",
        is_deleted=False,
    )
    # Treatment with unmapped procedure text
    t_unmapped_proc = models.Treatment(
        id=104,
        tenant_id=1,
        patient_id=1,
        tooth_number=14,
        procedure="Unrecognized Mystery Surgical Operation 12345",
        status="Done",
        is_deleted=False,
    )
    db.add_all([t_invalid_tooth, t_unmapped_proc])
    await db.commit()

    res = client.get("/api/v1/admin/clinical-drift/1", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["unmapped_issue_count"] >= 2


@pytest.mark.asyncio
async def test_tenant_isolation(
    client, async_db_session, observer_seed_data, super_admin_headers
):
    """
    Tenant isolation: scanning Tenant 1 never reads or reports Tenant 2 patients.
    """
    db = async_db_session
    # Add unbackfilled treatment to Tenant 2
    t201 = models.Treatment(
        id=201,
        tenant_id=2,
        patient_id=2,
        tooth_number=46,
        procedure="Pulpotomy",
        status="Done",
        is_deleted=False,
    )
    db.add(t201)
    await db.commit()

    # Scan Tenant 1
    res1 = client.get("/api/v1/admin/clinical-drift/1", headers=super_admin_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["tenant_id"] == 1
    assert data1["patients_scanned"] == 1
    assert 201 not in data1["missing_in_native_treatment_ids"]

    # Scan Tenant 2
    res2 = client.get("/api/v1/admin/clinical-drift/2", headers=super_admin_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["tenant_id"] == 2
    assert data2["patients_scanned"] == 1
    assert 201 in data2["missing_in_native_treatment_ids"]
    assert data2["patients_with_drift"] == 1


@pytest.mark.asyncio
async def test_non_super_admin_receives_403(client, observer_seed_data, auth_headers, admin_headers):
    """
    Non-super-admin (Role.DOCTOR, Role.ADMIN with tenant_id=1) -> 403.
    """
    # Doctor (Role.DOCTOR)
    res_doc = client.get("/api/v1/admin/clinical-drift/1", headers=auth_headers)
    assert res_doc.status_code == 403

    # Tenant Admin (Role.ADMIN with tenant_id=1)
    res_admin = client.get("/api/v1/admin/clinical-drift/1", headers=admin_headers)
    assert res_admin.status_code == 403

    # Anonymous
    res_anon = client.get("/api/v1/admin/clinical-drift/1")
    assert res_anon.status_code in (401, 403)


@pytest.mark.asyncio
async def test_non_existent_tenant_404(client, observer_seed_data, super_admin_headers):
    """
    Non-existent tenant_id -> 404.
    """
    res = client.get("/api/v1/admin/clinical-drift/999999", headers=super_admin_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_zero_mutation_proof(
    client, async_db_session, observer_seed_data, super_admin_headers
):
    """
    Zero-mutation proof: count of Treatment, ClinicalWorkItem, ClinicalEvent,
    Payment, and ClinicalProjectionCoverage before == after.
    """
    db = async_db_session

    async def get_table_counts():
        t_cnt = (await db.execute(select(func.count(models.Treatment.id)))).scalar()
        wi_cnt = (await db.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar()
        ev_cnt = (await db.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
        pay_cnt = (await db.execute(select(func.count(models.Payment.id)))).scalar()
        cov_cnt = (
            await db.execute(select(func.count(models.ClinicalProjectionCoverage.id)))
        ).scalar()
        return (t_cnt, wi_cnt, ev_cnt, pay_cnt, cov_cnt)

    counts_before = await get_table_counts()

    # Invoke observer via HTTP endpoint
    res = client.get("/api/v1/admin/clinical-drift/1", headers=super_admin_headers)
    assert res.status_code == 200

    # Invoke observer directly via service method
    svc = ClinicalDriftObserverService(db)
    report = await svc.compute_tenant_drift(tenant_id=1)
    assert report.tenant_id == 1

    # Invoke observer directly via classmethod
    report_cls = await ClinicalDriftObserverService.compute_tenant_drift_for_tenant(
        db, tenant_id=1
    )
    assert report_cls.tenant_id == 1

    counts_after = await get_table_counts()

    assert counts_before == counts_after, (
        f"Database mutated by read-only observer: before={counts_before}, after={counts_after}"
    )
