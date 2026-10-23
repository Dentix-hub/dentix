"""
Tests for Finance Parity and Shadow Calculator Service (G14-M06, G14-M07, G14-M08).

Verifies:
1. Zero-mutation proof: strictly read-only, count of all tables before == after.
2. Tenant isolation: scanning Tenant 1 never exposes Tenant 2 data.
3. Cross-tenant patient access returns 404. Non-existent tenant returns 404.
4. Exact Parity Match: Patient with legacy treatments backfilled into work items matches exactly (delta=0).
5. Shadow Surplus: Patient with new native completed procedure & ClinicalCharge not in legacy -> delta > 0.
6. Legacy Surplus: Patient with legacy treatment unbackfilled into work items -> delta < 0.
7. Voided Charge: Voided charge is excluded from shadow charges.
8. Unpriced Work Item: Native completed procedure without charge or treatment is flagged in discrepancies.
9. Deleted Treatment: Soft-deleted Treatment (is_deleted=True) is excluded from legacy charges.
10. Tenant Aggregation: Aggregates parity metrics across multiple patients.
11. Filtering and Pagination: discrepancies_only=True filters to drifted patients only; pagination works.
12. RBAC & Security: Super-admin gets 200; doctor/admin with tenant gets 403; anonymous gets 401/403.
"""

from decimal import Decimal
from datetime import datetime, timezone
import pytest
from sqlalchemy import func, select

from backend import models, schemas
from backend.services.finance_parity_service import FinanceParityService


@pytest.fixture
async def parity_seed_data(async_db_session):
    """Seed test tenants, users, patients, treatments, charges, work items and payments."""
    db = async_db_session

    # Tenants
    t1 = models.Tenant(id=1, name="Clinic Alpha", domain="alpha.test", is_active=True)
    t2 = models.Tenant(id=2, name="Clinic Beta", domain="beta.test", is_active=True)
    db.add_all([t1, t2])
    await db.flush()

    # Users
    u1 = models.User(
        id=10,
        username="dr_alpha",
        email="dr_alpha@test.com",
        hashed_password="fakehash",
        tenant_id=1,
        role="doctor",
    )
    u2 = models.User(
        id=20,
        username="dr_beta",
        email="dr_beta@test.com",
        hashed_password="fakehash",
        tenant_id=2,
        role="doctor",
    )
    db.add_all([u1, u2])
    await db.flush()

    # Patients in Tenant 1
    # P1: Exact Parity Match (1 backfilled treatment for 200, discount 20, net 180; payment 100)
    p1 = models.Patient(
        id=1,
        name="Patient Parity Match",
        age=30,
        phone="0123456789",
        medical_history="None",
        notes="",
        tenant_id=1,
    )
    # P2: Shadow Surplus (Native work item with ClinicalCharge 150; 0 legacy treatments; payment 50)
    p2 = models.Patient(
        id=2,
        name="Patient Shadow Surplus",
        age=35,
        phone="0123456788",
        medical_history="None",
        notes="",
        tenant_id=1,
    )
    # P3: Legacy Surplus (1 legacy treatment for 300 not backfilled; 0 work items; payment 0)
    p3 = models.Patient(
        id=3,
        name="Patient Legacy Surplus",
        age=40,
        phone="0123456787",
        medical_history="None",
        notes="",
        tenant_id=1,
    )
    # Patient in Tenant 2 (for isolation check)
    p4 = models.Patient(
        id=4,
        name="Patient Tenant Beta",
        age=25,
        phone="0123456786",
        medical_history="None",
        notes="",
        tenant_id=2,
    )
    db.add_all([p1, p2, p3, p4])
    await db.flush()

    # --- Setup P1: Exact Parity Match ---
    t101 = models.Treatment(
        id=101,
        tenant_id=1,
        patient_id=1,
        tooth_number=16,
        procedure="Composite Filling",
        status="Done",
        date=datetime.now(timezone.utc).replace(tzinfo=None),
        cost=200.0,
        discount=20.0,
        is_deleted=False,
    )
    db.add(t101)
    await db.flush()

    wi1001 = models.ClinicalWorkItem(
        id=1001,
        tenant_id=1,
        patient_id=1,
        kind="procedure",
        code="REST_COMPOSITE",
        status="completed",
        notes="Backfilled",
    )
    db.add(wi1001)
    await db.flush()

    ev1001 = models.ClinicalEvent(
        id=5001,
        tenant_id=1,
        patient_id=1,
        work_item_id=1001,
        event_type="procedure_recorded",
        occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
        actor_user_id=10,
        payload={"treatment_id": 101, "kind": "procedure", "canonical_code": "REST_COMPOSITE"},
    )
    db.add(ev1001)

    pay1 = models.Payment(
        id=301,
        tenant_id=1,
        patient_id=1,
        amount=100.0,
    )
    db.add(pay1)

    # --- Setup P2: Shadow Surplus ---
    wi1002 = models.ClinicalWorkItem(
        id=1002,
        tenant_id=1,
        patient_id=2,
        kind="procedure",
        code="REST_COMPOSITE",
        status="completed",
        notes="Native VNext",
    )
    db.add(wi1002)
    await db.flush()

    cc1 = models.ClinicalCharge(
        id=1,
        tenant_id=1,
        patient_id=2,
        work_item_id=1002,
        amount=150.0,
        discount=0.0,
        status="pending",
        version_id=1,
    )
    db.add(cc1)

    pay2 = models.Payment(
        id=302,
        tenant_id=1,
        patient_id=2,
        amount=50.0,
    )
    db.add(pay2)

    # --- Setup P3: Legacy Surplus ---
    t103 = models.Treatment(
        id=103,
        tenant_id=1,
        patient_id=3,
        tooth_number=21,
        procedure="Crown",
        status="Done",
        date=datetime.now(timezone.utc).replace(tzinfo=None),
        cost=300.0,
        discount=0.0,
        is_deleted=False,
    )
    db.add(t103)

    # --- Setup P4 in Tenant 2 ---
    t201 = models.Treatment(
        id=201,
        tenant_id=2,
        patient_id=4,
        tooth_number=11,
        procedure="Extraction",
        status="Done",
        cost=80.0,
        discount=0.0,
        is_deleted=False,
    )
    db.add(t201)

    await db.commit()
    return {"t1": t1, "t2": t2, "p1": p1, "p2": p2, "p3": p3, "p4": p4}


@pytest.mark.asyncio
async def test_zero_mutation_proof(client, async_db_session, parity_seed_data, super_admin_headers):
    """
    Zero-mutation proof: counts of Treatment, Payment, ClinicalCharge,
    ClinicalWorkItem, and Patient before == after calling finance parity.
    """
    db = async_db_session

    async def get_table_counts():
        t_cnt = (await db.execute(select(func.count(models.Treatment.id)))).scalar_one()
        p_cnt = (await db.execute(select(func.count(models.Payment.id)))).scalar_one()
        cc_cnt = (await db.execute(select(func.count(models.ClinicalCharge.id)))).scalar_one()
        wi_cnt = (await db.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar_one()
        pt_cnt = (await db.execute(select(func.count(models.Patient.id)))).scalar_one()
        return (t_cnt, p_cnt, cc_cnt, wi_cnt, pt_cnt)

    counts_before = await get_table_counts()

    # Invoke tenant parity via API
    res_tenant = client.get("/api/v1/admin/finance-parity/1", headers=super_admin_headers)
    assert res_tenant.status_code == 200

    # Invoke patient parity via API
    res_patient = client.get("/api/v1/admin/finance-parity/1/patients/1", headers=super_admin_headers)
    assert res_patient.status_code == 200

    # Invoke directly via service
    svc = FinanceParityService(db)
    await svc.compute_tenant_parity(tenant_id=1)
    await svc.compute_patient_parity(tenant_id=1, patient_id=1)

    counts_after = await get_table_counts()
    assert counts_before == counts_after


@pytest.mark.asyncio
async def test_exact_parity_match_patient(async_db_session, parity_seed_data):
    """Patient with backfilled treatment matching work item -> PARITY_MATCH (delta=0)."""
    svc = FinanceParityService(async_db_session)
    report = await svc.compute_patient_parity(tenant_id=1, patient_id=1)

    assert report.patient_id == 1
    assert report.legacy_charges == Decimal("180.00")
    assert report.shadow_charges == Decimal("180.00")
    assert report.charge_delta == Decimal("0.00")
    assert report.payments_total == Decimal("100.00")
    assert report.legacy_balance == Decimal("80.00")
    assert report.shadow_balance == Decimal("80.00")
    assert report.balance_delta == Decimal("0.00")
    assert report.is_parity_match is True
    assert report.status == "PARITY_MATCH"
    assert len(report.discrepancy_reasons) == 0
    assert report.legacy_treatments_count == 1
    assert len(report.work_item_projections) == 1
    assert report.work_item_projections[0]["source"] == "legacy_treatment"


@pytest.mark.asyncio
async def test_shadow_surplus_patient(async_db_session, parity_seed_data):
    """Patient with native VNext charge and no legacy treatments -> SHADOW_SURPLUS (delta=150)."""
    svc = FinanceParityService(async_db_session)
    report = await svc.compute_patient_parity(tenant_id=1, patient_id=2)

    assert report.patient_id == 2
    assert report.legacy_charges == Decimal("0.00")
    assert report.shadow_charges == Decimal("150.00")
    assert report.charge_delta == Decimal("150.00")
    assert report.payments_total == Decimal("50.00")
    assert report.legacy_balance == Decimal("-50.00")
    assert report.shadow_balance == Decimal("100.00")
    assert report.balance_delta == Decimal("150.00")
    assert report.is_parity_match is False
    assert report.status == "SHADOW_SURPLUS"
    assert len(report.discrepancy_reasons) == 1
    assert "native clinical charge" in report.discrepancy_reasons[0].lower()


@pytest.mark.asyncio
async def test_legacy_surplus_patient(async_db_session, parity_seed_data):
    """Patient with legacy treatment unbackfilled into work items -> LEGACY_SURPLUS (delta=-300)."""
    svc = FinanceParityService(async_db_session)
    report = await svc.compute_patient_parity(tenant_id=1, patient_id=3)

    assert report.patient_id == 3
    assert report.legacy_charges == Decimal("300.00")
    assert report.shadow_charges == Decimal("0.00")
    assert report.charge_delta == Decimal("-300.00")
    assert report.payments_total == Decimal("0.00")
    assert report.legacy_balance == Decimal("300.00")
    assert report.shadow_balance == Decimal("0.00")
    assert report.balance_delta == Decimal("-300.00")
    assert report.is_parity_match is False
    assert report.status == "LEGACY_SURPLUS"
    assert len(report.discrepancy_reasons) == 1
    assert "unlinked to work items" in report.discrepancy_reasons[0].lower()


@pytest.mark.asyncio
async def test_voided_charge_is_excluded(async_db_session, parity_seed_data):
    """Voided charge is excluded from shadow charges."""
    db = async_db_session
    # Add a voided charge to patient 1
    wi_voided = models.ClinicalWorkItem(
        id=1099,
        tenant_id=1,
        patient_id=1,
        kind="procedure",
        code="REST_COMPOSITE",
        status="cancelled",
    )
    db.add(wi_voided)
    await db.flush()

    cc_voided = models.ClinicalCharge(
        id=99,
        tenant_id=1,
        patient_id=1,
        work_item_id=1099,
        amount=500.0,
        discount=0.0,
        status="voided",
        version_id=2,
    )
    db.add(cc_voided)
    await db.commit()

    svc = FinanceParityService(db)
    report = await svc.compute_patient_parity(tenant_id=1, patient_id=1)

    # Shadow charges must remain 180 (the 500 voided charge is excluded)
    assert report.shadow_charges == Decimal("180.00")
    assert report.is_parity_match is True


@pytest.mark.asyncio
async def test_unpriced_completed_procedure_flagged(async_db_session, parity_seed_data):
    """Completed procedure with neither treatment nor charge is flagged in discrepancy_reasons."""
    db = async_db_session
    wi_unpriced = models.ClinicalWorkItem(
        id=1098,
        tenant_id=1,
        patient_id=1,
        kind="procedure",
        code="REST_COMPOSITE",
        status="completed",
        notes="Completed without charge",
    )
    db.add(wi_unpriced)
    await db.commit()

    svc = FinanceParityService(db)
    report = await svc.compute_patient_parity(tenant_id=1, patient_id=1)

    assert any("have no charge or treatment" in r for r in report.discrepancy_reasons)


@pytest.mark.asyncio
async def test_deleted_treatment_excluded_from_legacy(async_db_session, parity_seed_data):
    """Soft-deleted legacy treatments (is_deleted=True) are excluded from legacy_charges."""
    db = async_db_session
    t_del = models.Treatment(
        id=199,
        tenant_id=1,
        patient_id=1,
        tooth_number=18,
        procedure="Old Extraction",
        status="Done",
        cost=1000.0,
        discount=0.0,
        is_deleted=True,
    )
    db.add(t_del)
    await db.commit()

    svc = FinanceParityService(db)
    report = await svc.compute_patient_parity(tenant_id=1, patient_id=1)

    # Legacy charges must still be 180, not 1180
    assert report.legacy_charges == Decimal("180.00")
    assert report.is_parity_match is True


@pytest.mark.asyncio
async def test_tenant_parity_aggregation(async_db_session, parity_seed_data):
    """Tenant parity accurately aggregates legacy, shadow, delta, and counts across patients."""
    svc = FinanceParityService(async_db_session)
    tenant_report = await svc.compute_tenant_parity(tenant_id=1)

    assert tenant_report.tenant_id == 1
    assert tenant_report.tenant_name == "Clinic Alpha"
    assert tenant_report.total_patients_evaluated == 3
    assert tenant_report.patients_with_parity == 1  # P1 matches
    assert tenant_report.patients_with_discrepancy == 2  # P2 and P3 have drift
    assert tenant_report.is_tenant_parity_match is False

    # P1: 180 legacy, 180 shadow; P2: 0 legacy, 150 shadow; P3: 300 legacy, 0 shadow
    # Total legacy: 180 + 0 + 300 = 480.00
    # Total shadow: 180 + 150 + 0 = 330.00
    # Total charge delta: 330 - 480 = -150.00
    assert tenant_report.total_legacy_charges == Decimal("480.00")
    assert tenant_report.total_shadow_charges == Decimal("330.00")
    assert tenant_report.total_charge_delta == Decimal("-150.00")

    # Payments: P1 100 + P2 50 + P3 0 = 150.00
    assert tenant_report.total_payments == Decimal("150.00")
    assert tenant_report.total_legacy_balance == Decimal("330.00")
    assert tenant_report.total_shadow_balance == Decimal("180.00")
    assert tenant_report.total_balance_delta == Decimal("-150.00")


@pytest.mark.asyncio
async def test_tenant_discrepancies_only_filter(async_db_session, parity_seed_data):
    """discrepancies_only=True filters out matching patients from list."""
    svc = FinanceParityService(async_db_session)
    report = await svc.compute_tenant_parity(tenant_id=1, discrepancies_only=True)

    assert report.total_patients_evaluated == 3
    assert report.patients_with_parity == 1
    assert report.patients_with_discrepancy == 2
    # Only P2 and P3 returned in patients array
    assert len(report.patients) == 2
    returned_ids = {p.patient_id for p in report.patients}
    assert returned_ids == {2, 3}


@pytest.mark.asyncio
async def test_tenant_pagination(async_db_session, parity_seed_data):
    """limit_patients and after_patient_id cursor pagination behaves deterministically."""
    svc = FinanceParityService(async_db_session)

    # Page 1: limit 2
    page1 = await svc.compute_tenant_parity(tenant_id=1, limit_patients=2, after_patient_id=0)
    assert len(page1.patients) == 2
    assert [p.patient_id for p in page1.patients] == [1, 2]

    # Page 2: after_patient_id = 2, limit 2
    page2 = await svc.compute_tenant_parity(tenant_id=1, limit_patients=2, after_patient_id=2)
    assert len(page2.patients) == 1
    assert [p.patient_id for p in page2.patients] == [3]


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(client, parity_seed_data, super_admin_headers):
    """Tenant isolation: scanning Tenant 1 never includes Tenant 2 patient P4."""
    res1 = client.get("/api/v1/admin/finance-parity/1", headers=super_admin_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    p_ids_1 = [p["patient_id"] for p in data1["patients"]]
    assert 4 not in p_ids_1

    # Cross-tenant patient query: requesting Patient 4 under Tenant 1 -> 404
    res_cross = client.get("/api/v1/admin/finance-parity/1/patients/4", headers=super_admin_headers)
    assert res_cross.status_code == 404
    assert "not found" in res_cross.json()["detail"].lower()

    # Scanning Tenant 2
    res2 = client.get("/api/v1/admin/finance-parity/2", headers=super_admin_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["tenant_id"] == 2
    assert data2["total_patients_evaluated"] == 1
    assert data2["patients"][0]["patient_id"] == 4


@pytest.mark.asyncio
async def test_non_existent_tenant_404(client, parity_seed_data, super_admin_headers):
    """Non-existent tenant_id -> 404."""
    res_tenant = client.get("/api/v1/admin/finance-parity/99999", headers=super_admin_headers)
    assert res_tenant.status_code == 404

    res_patient = client.get("/api/v1/admin/finance-parity/99999/patients/1", headers=super_admin_headers)
    assert res_patient.status_code == 404


@pytest.mark.asyncio
async def test_rbac_super_admin_required(client, parity_seed_data, auth_headers, admin_headers):
    """Non-super-admin (Role.DOCTOR, Role.ADMIN with tenant_id) receives 403 Forbidden."""
    # Doctor -> 403
    res_doc = client.get("/api/v1/admin/finance-parity/1", headers=auth_headers)
    assert res_doc.status_code == 403

    res_doc_p = client.get("/api/v1/admin/finance-parity/1/patients/1", headers=auth_headers)
    assert res_doc_p.status_code == 403

    # Clinic admin (with tenant_id) -> 403
    res_admin = client.get("/api/v1/admin/finance-parity/1", headers=admin_headers)
    assert res_admin.status_code == 403

    # Anonymous -> 401/403
    res_anon = client.get("/api/v1/admin/finance-parity/1")
    assert res_anon.status_code in (401, 403)
