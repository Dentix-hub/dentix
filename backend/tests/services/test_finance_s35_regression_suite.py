"""
S35: Legacy Lab Double-Charge Detector, Doctor-Share Compatibility & Finance Regression Suite.

Matrix Coverage:
- G14-M09: Detect legacy lab double-charge cases (duplicate manual treatments, orphaned links, multiple links, price mismatches).
- G14-M10: Add deterministic remediation workflow (read-only admin inspection report with actionable remediation guidance).
- G14-M11: Add doctor-share compatibility tests (AccountingService & DecimalSafeAccountingService compatibility with ClinicalCharges).
- G14-M13: Keep payments stable (models.Payment rows and BillingService remain strictly invariant).
- G14-M14: Financial regression suite (end-to-end multi-tenant financial invariance).
"""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from backend import models, schemas
from backend.auth import create_access_token
from backend.core.permissions import Role
from backend.crud.billing import get_treatments, get_payments
from backend.main import app
from backend.services.accounting_service import AccountingService
from backend.services.accounting_decimal_service import DecimalSafeAccountingService
from backend.services.billing_service import BillingService
from backend.services.finance_parity_service import FinanceParityService, TREATMENT_LINK_PREFIX


# ===========================================================================
# Fixtures & Data Helpers
# ===========================================================================

@pytest.fixture
async def s35_seed(async_db_session):
    """Seed tenants, users, patients, and labs for S35 financial verification."""
    # Tenants
    t1 = models.Tenant(name="S35 Clinic Alpha", is_active=True)
    t2 = models.Tenant(name="S35 Clinic Beta", is_active=True)
    async_db_session.add_all([t1, t2])
    await async_db_session.flush()

    # Users
    super_admin = models.User(
        id=35001,
        username="s35_superadmin",
        email="s35_superadmin@test.com",
        full_name="Super Admin",
        hashed_password="hash",
        role="super_admin",
        tenant_id=None,
        is_active=True,
    )
    doc_1 = models.User(
        id=35002,
        username="s35_doc1",
        email="s35_doc1@test.com",
        full_name="Dr. Alpha",
        hashed_password="hash",
        role="doctor",
        tenant_id=t1.id,
        is_active=True,
    )
    rec_1 = models.User(
        id=35003,
        username="s35_rec1",
        email="s35_rec1@test.com",
        full_name="Receptionist Alpha",
        hashed_password="hash",
        role="receptionist",
        tenant_id=t1.id,
        is_active=True,
    )
    doc_2 = models.User(
        id=35004,
        username="s35_doc2",
        email="s35_doc2@test.com",
        full_name="Dr. Beta",
        hashed_password="hash",
        role="doctor",
        tenant_id=t2.id,
        is_active=True,
    )
    async_db_session.add_all([super_admin, doc_1, rec_1, doc_2])
    await async_db_session.flush()

    # Patients
    pat_1 = models.Patient(
        name="Patient Alpha One",
        age=30,
        phone="01011110001",
        medical_history="None",
        notes="",
        tenant_id=t1.id,
        is_deleted=False,
    )
    pat_2 = models.Patient(
        name="Patient Alpha Two",
        age=35,
        phone="01011110002",
        medical_history="None",
        notes="",
        tenant_id=t1.id,
        is_deleted=False,
    )
    pat_beta = models.Patient(
        name="Patient Beta One",
        age=40,
        phone="01022220001",
        medical_history="None",
        notes="",
        tenant_id=t2.id,
        is_deleted=False,
    )
    async_db_session.add_all([pat_1, pat_2, pat_beta])
    await async_db_session.flush()

    # Laboratories
    lab_1 = models.Laboratory(
        name="Alpha Dental Lab",
        tenant_id=t1.id,
        is_active=True,
    )
    lab_2 = models.Laboratory(
        name="Beta Dental Lab",
        tenant_id=t2.id,
        is_active=True,
    )
    async_db_session.add_all([lab_1, lab_2])
    await async_db_session.commit()

    return {
        "tenant_1": t1,
        "tenant_2": t2,
        "super_admin": super_admin,
        "doc_1": doc_1,
        "rec_1": rec_1,
        "doc_2": doc_2,
        "pat_1": pat_1,
        "pat_2": pat_2,
        "pat_beta": pat_beta,
        "lab_1": lab_1,
        "lab_2": lab_2,
    }


def _auth_headers(user: models.User) -> dict:
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "tenant_id": user.tenant_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# G14-M09 & G14-M10: Lab Double-Charge Anomaly Detector & Remediation Report
# ===========================================================================

@pytest.mark.asyncio
async def test_g14_m09_detect_duplicate_manual_treatment(async_db_session, s35_seed):
    """
    Test G14-M09: Detect duplicate manual treatment alongside linked lab order treatment.
    Doctor has a LabOrder (price_to_patient=600) with a linked treatment, and ALSO
    created a manual treatment on tooth 14 charging 600, causing a 600 overcharge.
    """
    t1 = s35_seed["tenant_1"]
    pat1 = s35_seed["pat_1"]
    doc1 = s35_seed["doc_1"]
    lab1 = s35_seed["lab_1"]

    now = datetime.now(timezone.utc)
    # 1. Lab order with price_to_patient=600
    lab_order = models.LabOrder(
        patient_id=pat1.id,
        laboratory_id=lab1.id,
        doctor_id=doc1.id,
        work_type="Zirconia Crown",
        tooth_number="14",
        cost=Decimal("250.00"),
        price_to_patient=Decimal("600.00"),
        status="in_progress",
        order_date=now,
        tenant_id=t1.id,
    )
    async_db_session.add(lab_order)
    await async_db_session.flush()

    # 2. Linked synthetic treatment created by legacy flow
    linked_t = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        tooth_number=14,
        procedure="Zirconia Crown",
        cost=Decimal("600.00"),
        discount=Decimal("0.00"),
        date=now,
        notes=f"{TREATMENT_LINK_PREFIX}{lab_order.id}",
        tenant_id=t1.id,
    )
    # 3. Manual duplicate treatment entered by doctor on the same tooth
    manual_t = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        tooth_number=14,
        procedure="تركيبة زيركون",
        cost=Decimal("600.00"),
        discount=Decimal("0.00"),
        date=now + timedelta(hours=1),
        notes="Patient billed separately for crown",
        tenant_id=t1.id,
    )
    async_db_session.add_all([linked_t, manual_t])
    await async_db_session.commit()

    service = FinanceParityService(async_db_session)
    report = await service.detect_lab_double_charge_anomalies(tenant_id=t1.id)

    assert report.tenant_id == t1.id
    assert report.total_anomalies_count == 1
    assert report.patients_affected_count == 1
    assert report.total_potential_overcharge == Decimal("600.00")

    anomaly = report.anomalies[0]
    assert anomaly.patient_id == pat1.id
    assert anomaly.anomaly_type == "duplicate_manual_treatment"
    assert anomaly.lab_order_id == lab_order.id
    assert anomaly.linked_treatment_id == linked_t.id
    assert anomaly.candidate_treatment_ids == [manual_t.id]
    assert anomaly.estimated_overcharge_amount == Decimal("600.00")
    assert "Soft-delete" in anomaly.remediation_suggestion or "soft-delete" in anomaly.remediation_suggestion


@pytest.mark.asyncio
async def test_g14_m09_detect_orphaned_linked_treatment(async_db_session, s35_seed):
    """
    Test G14-M09: Detect orphaned linked treatments where referenced lab order
    does not exist or has been deleted/zeroed out.
    """
    t1 = s35_seed["tenant_1"]
    pat1 = s35_seed["pat_1"]
    doc1 = s35_seed["doc_1"]

    now = datetime.now(timezone.utc)
    orphaned_t = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        tooth_number=21,
        procedure="Porcelain Crown",
        cost=Decimal("450.00"),
        discount=Decimal("0.00"),
        date=now,
        notes=f"{TREATMENT_LINK_PREFIX}999888",  # Non-existent lab order
        tenant_id=t1.id,
    )
    async_db_session.add(orphaned_t)
    await async_db_session.commit()

    service = FinanceParityService(async_db_session)
    report = await service.detect_lab_double_charge_anomalies(tenant_id=t1.id)

    assert report.total_anomalies_count == 1
    anomaly = report.anomalies[0]
    assert anomaly.anomaly_type == "orphaned_linked_treatment"
    assert anomaly.lab_order_id == 999888
    assert anomaly.candidate_treatment_ids == [orphaned_t.id]
    assert anomaly.estimated_overcharge_amount == Decimal("450.00")


@pytest.mark.asyncio
async def test_g14_m09_detect_multiple_linked_treatments(async_db_session, s35_seed):
    """
    Test G14-M09: Detect multiple treatments linking to the exact same LabOrder.
    """
    t1 = s35_seed["tenant_1"]
    pat2 = s35_seed["pat_2"]
    doc1 = s35_seed["doc_1"]
    lab1 = s35_seed["lab_1"]

    now = datetime.now(timezone.utc)
    lab_order = models.LabOrder(
        patient_id=pat2.id,
        laboratory_id=lab1.id,
        doctor_id=doc1.id,
        work_type="E-Max Inlay",
        tooth_number="16",
        cost=Decimal("200.00"),
        price_to_patient=Decimal("500.00"),
        status="completed",
        order_date=now,
        tenant_id=t1.id,
    )
    async_db_session.add(lab_order)
    await async_db_session.flush()

    t_link_1 = models.Treatment(
        patient_id=pat2.id,
        doctor_id=doc1.id,
        tooth_number=16,
        procedure="E-Max Inlay",
        cost=Decimal("500.00"),
        date=now,
        notes=f"{TREATMENT_LINK_PREFIX}{lab_order.id}",
        tenant_id=t1.id,
    )
    t_link_2 = models.Treatment(
        patient_id=pat2.id,
        doctor_id=doc1.id,
        tooth_number=16,
        procedure="E-Max Inlay (Duplicate)",
        cost=Decimal("500.00"),
        date=now,
        notes=f"{TREATMENT_LINK_PREFIX}{lab_order.id}",
        tenant_id=t1.id,
    )
    async_db_session.add_all([t_link_1, t_link_2])
    await async_db_session.commit()

    service = FinanceParityService(async_db_session)
    report = await service.detect_lab_double_charge_anomalies(tenant_id=t1.id)

    assert report.total_anomalies_count == 1
    anomaly = report.anomalies[0]
    assert anomaly.anomaly_type == "multiple_linked_treatments"
    assert anomaly.lab_order_id == lab_order.id
    assert anomaly.candidate_treatment_ids == [t_link_2.id]
    assert anomaly.estimated_overcharge_amount == Decimal("500.00")


@pytest.mark.asyncio
async def test_g14_m09_detect_price_mismatch(async_db_session, s35_seed):
    """
    Test G14-M09: Detect price mismatch between LabOrder.price_to_patient and linked treatment cost.
    """
    t1 = s35_seed["tenant_1"]
    pat1 = s35_seed["pat_1"]
    doc1 = s35_seed["doc_1"]
    lab1 = s35_seed["lab_1"]

    now = datetime.now(timezone.utc)
    lab_order = models.LabOrder(
        patient_id=pat1.id,
        laboratory_id=lab1.id,
        doctor_id=doc1.id,
        work_type="Bridge",
        tooth_number="11, 12",
        cost=Decimal("400.00"),
        price_to_patient=Decimal("1200.00"),
        status="in_progress",
        order_date=now,
        tenant_id=t1.id,
    )
    async_db_session.add(lab_order)
    await async_db_session.flush()

    linked_t = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        tooth_number=11,
        procedure="Bridge",
        cost=Decimal("1000.00"),  # 200 mismatch!
        date=now,
        notes=f"{TREATMENT_LINK_PREFIX}{lab_order.id}",
        tenant_id=t1.id,
    )
    async_db_session.add(linked_t)
    await async_db_session.commit()

    service = FinanceParityService(async_db_session)
    report = await service.detect_lab_double_charge_anomalies(tenant_id=t1.id)

    assert report.total_anomalies_count == 1
    anomaly = report.anomalies[0]
    assert anomaly.anomaly_type == "linked_treatment_price_mismatch"
    assert anomaly.lab_order_id == lab_order.id
    assert anomaly.estimated_overcharge_amount == Decimal("200.00")


@pytest.mark.asyncio
async def test_g14_m09_detect_unlinked_lab_with_manual_treatment(async_db_session, s35_seed):
    """
    Test G14-M09: Detect unlinked lab order with price_to_patient > 0 where manual treatment exists.
    """
    t1 = s35_seed["tenant_1"]
    pat1 = s35_seed["pat_1"]
    doc1 = s35_seed["doc_1"]
    lab1 = s35_seed["lab_1"]

    now = datetime.now(timezone.utc)
    lab_order = models.LabOrder(
        patient_id=pat1.id,
        laboratory_id=lab1.id,
        doctor_id=doc1.id,
        work_type="Denture",
        tooth_number="Upper",
        cost=Decimal("500.00"),
        price_to_patient=Decimal("1500.00"),
        status="in_progress",
        order_date=now,
        tenant_id=t1.id,
    )
    async_db_session.add(lab_order)
    await async_db_session.flush()

    # Manual treatment exists for the same service, but no link note
    manual_t = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        tooth_number=None,
        procedure="طقم أسنان علوي",
        cost=Decimal("1500.00"),
        date=now,
        notes="Manual denture record",
        tenant_id=t1.id,
    )
    async_db_session.add(manual_t)
    await async_db_session.commit()

    service = FinanceParityService(async_db_session)
    report = await service.detect_lab_double_charge_anomalies(tenant_id=t1.id)

    assert report.total_anomalies_count == 1
    anomaly = report.anomalies[0]
    assert anomaly.anomaly_type == "unlinked_lab_with_manual_treatment"
    assert anomaly.candidate_treatment_ids == [manual_t.id]


@pytest.mark.asyncio
async def test_g14_m09_clean_case_zero_anomalies(async_db_session, s35_seed):
    """
    Test G14-M09: Clean lab order + single exact linked treatment yields 0 anomalies.
    """
    t2 = s35_seed["tenant_2"]
    pat_beta = s35_seed["pat_beta"]
    doc2 = s35_seed["doc_2"]
    lab2 = s35_seed["lab_2"]

    now = datetime.now(timezone.utc)
    lab_order = models.LabOrder(
        patient_id=pat_beta.id,
        laboratory_id=lab2.id,
        doctor_id=doc2.id,
        work_type="Zirconia Crown",
        tooth_number="24",
        cost=Decimal("200.00"),
        price_to_patient=Decimal("550.00"),
        status="completed",
        order_date=now,
        tenant_id=t2.id,
    )
    async_db_session.add(lab_order)
    await async_db_session.flush()

    linked_t = models.Treatment(
        patient_id=pat_beta.id,
        doctor_id=doc2.id,
        tooth_number=24,
        procedure="Zirconia Crown",
        cost=Decimal("550.00"),
        discount=Decimal("0.00"),
        date=now,
        notes=f"{TREATMENT_LINK_PREFIX}{lab_order.id}",
        tenant_id=t2.id,
    )
    async_db_session.add(linked_t)
    await async_db_session.commit()

    service = FinanceParityService(async_db_session)
    report = await service.detect_lab_double_charge_anomalies(tenant_id=t2.id)

    assert report.tenant_id == t2.id
    assert report.total_anomalies_count == 0
    assert report.patients_affected_count == 0
    assert report.total_potential_overcharge == Decimal("0.00")
    assert report.anomalies == []


@pytest.mark.asyncio
async def test_g14_m10_read_only_mutation_invariance(async_db_session, s35_seed):
    """
    Test G14-M10: Verify that running the anomaly detector makes EXACTLY ZERO database mutations.
    """
    t1 = s35_seed["tenant_1"]

    async def _snapshot_counts():
        t_cnt = (await async_db_session.execute(select(func.count(models.Treatment.id)))).scalar_one()
        lo_cnt = (await async_db_session.execute(select(func.count(models.LabOrder.id)))).scalar_one()
        p_cnt = (await async_db_session.execute(select(func.count(models.Payment.id)))).scalar_one()
        cc_cnt = (await async_db_session.execute(select(func.count(models.ClinicalCharge.id)))).scalar_one()
        return t_cnt, lo_cnt, p_cnt, cc_cnt

    before = await _snapshot_counts()

    service = FinanceParityService(async_db_session)
    await service.detect_lab_double_charge_anomalies(tenant_id=t1.id)

    after = await _snapshot_counts()
    assert before == after, "Zero database mutations strictly preserved during anomaly detection!"


@pytest.mark.asyncio
async def test_g14_m09_endpoint_and_rbac(async_db_session, s35_seed):
    """
    Test G14-M09 & G14-M10 HTTP endpoint:
    - Super-admin: 200 OK
    - Doctor: 403 Forbidden
    - Receptionist: 403 Forbidden
    - Missing tenant: 404 Not Found
    """
    t1 = s35_seed["tenant_1"]
    super_admin = s35_seed["super_admin"]
    doc1 = s35_seed["doc_1"]
    rec1 = s35_seed["rec_1"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Super-admin -> 200 OK
        res_admin = await client.get(
            f"/api/v1/admin/finance-parity/{t1.id}/lab-anomalies",
            headers=_auth_headers(super_admin),
        )
        assert res_admin.status_code == 200
        data = res_admin.json()
        assert data["tenant_id"] == t1.id
        assert "anomalies" in data
        assert "total_anomalies_count" in data

        # 2. Doctor -> 403 Forbidden
        res_doc = await client.get(
            f"/api/v1/admin/finance-parity/{t1.id}/lab-anomalies",
            headers=_auth_headers(doc1),
        )
        assert res_doc.status_code == 403

        # 3. Receptionist -> 403 Forbidden
        res_rec = await client.get(
            f"/api/v1/admin/finance-parity/{t1.id}/lab-anomalies",
            headers=_auth_headers(rec1),
        )
        assert res_rec.status_code == 403

        # 4. Non-existent tenant -> 404
        res_missing = await client.get(
            "/api/v1/admin/finance-parity/9999999/lab-anomalies",
            headers=_auth_headers(super_admin),
        )
        assert res_missing.status_code == 404


# ===========================================================================
# G14-M11: Doctor-Share Compatibility Tests (AccountingService)
# ===========================================================================

@pytest.mark.asyncio
async def test_g14_m11_doctor_share_compatibility_with_clinical_charges(async_db_session, s35_seed):
    """
    Test G14-M11: Doctor revenue, lab deductions, and doctor compensation queries
    in AccountingService and DecimalSafeAccountingService remain 100% compatible
    and unchanged when ClinicalCharge rows exist.
    """
    t1 = s35_seed["tenant_1"]
    pat1 = s35_seed["pat_1"]
    doc1 = s35_seed["doc_1"]
    lab1 = s35_seed["lab_1"]

    now = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
    t_date_str = "2026-08-18"

    # Add legacy treatments & payments for doctor 1
    t1_row = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        procedure="Composite Filling",
        cost=Decimal("1000.00"),
        discount=Decimal("100.00"),
        date=now,
        tenant_id=t1.id,
    )
    p1_row = models.Payment(
        patient_id=pat1.id,
        amount=Decimal("900.00"),
        date=now,
        tenant_id=t1.id,
    )
    # Lab order for doctor 1
    lo_row = models.LabOrder(
        patient_id=pat1.id,
        laboratory_id=lab1.id,
        doctor_id=doc1.id,
        work_type="Crown",
        cost=Decimal("200.00"),
        price_to_patient=Decimal("0.00"),
        order_date=now,
        tenant_id=t1.id,
    )
    async_db_session.add_all([t1_row, p1_row, lo_row])
    await async_db_session.commit()

    # 1. Baseline accounting calculation
    acc_service = AccountingService(async_db_session, t1.id)
    start_d, end_d = acc_service.parse_date_range(t_date_str, t_date_str)

    base_analytics = await acc_service.get_doctor_revenue_analytics(start_d, end_d)
    doc_base = next(r for r in base_analytics if r["doctor_id"] == doc1.id)
    assert doc_base["revenue"] == 900.0
    assert doc_base["lab_cost"] == 200.0

    # Decimal-safe accounting facade baseline
    dec_service = DecimalSafeAccountingService(async_db_session, t1.id)
    dec_analytics = await dec_service.get_doctor_revenue_analytics(start_d, end_d)
    doc_dec_base = next(r for r in dec_analytics if r["doctor_id"] == doc1.id)
    assert float(doc_dec_base["revenue"]) == 900.0
    assert float(doc_dec_base["lab_cost"]) == 200.0

    # 2. Add native ClinicalCharge rows (pending, invoiced, voided)
    wi1 = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=pat1.id, kind="procedure", code="REST_COMPOSITE", status="completed", version_id=1
    )
    wi2 = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=pat1.id, kind="procedure", code="ENDO_RCT", status="completed", version_id=1
    )
    wi3 = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=pat1.id, kind="procedure", code="PROS_CROWN", status="completed", version_id=1
    )
    async_db_session.add_all([wi1, wi2, wi3])
    await async_db_session.flush()

    cc_pending = models.ClinicalCharge(
        tenant_id=t1.id,
        patient_id=pat1.id,
        doctor_id=doc1.id,
        work_item_id=wi1.id,
        amount=Decimal("3000.00"),
        discount=Decimal("0.00"),
        status="pending",
    )
    cc_invoiced = models.ClinicalCharge(
        tenant_id=t1.id,
        patient_id=pat1.id,
        doctor_id=doc1.id,
        work_item_id=wi2.id,
        amount=Decimal("5000.00"),
        discount=Decimal("500.00"),
        status="invoiced",
    )
    cc_voided = models.ClinicalCharge(
        tenant_id=t1.id,
        patient_id=pat1.id,
        doctor_id=doc1.id,
        work_item_id=wi3.id,
        amount=Decimal("1500.00"),
        discount=Decimal("0.00"),
        status="voided",
    )
    async_db_session.add_all([cc_pending, cc_invoiced, cc_voided])
    await async_db_session.commit()

    # 3. Re-evaluate accounting service with ClinicalCharges present
    new_analytics = await acc_service.get_doctor_revenue_analytics(start_d, end_d)
    doc_new = next(r for r in new_analytics if r["doctor_id"] == doc1.id)
    assert doc_new["revenue"] == doc_base["revenue"] == 900.0, "ClinicalCharges did NOT alter doctor revenue!"
    assert doc_new["lab_cost"] == doc_base["lab_cost"] == 200.0

    # DecimalSafe service verification
    new_dec_analytics = await dec_service.get_doctor_revenue_analytics(start_d, end_d)
    doc_dec_new = next(r for r in new_dec_analytics if r["doctor_id"] == doc1.id)
    assert float(doc_dec_new["revenue"]) == float(doc_dec_base["revenue"]) == 900.0
    assert float(doc_dec_new["lab_cost"]) == float(doc_dec_base["lab_cost"]) == 200.0


# ===========================================================================
# G14-M13 & G14-M14: Payments Stability & Financial Regression Suite
# ===========================================================================

@pytest.mark.asyncio
async def test_g14_m13_payments_stability_and_balance_invariance(async_db_session, s35_seed):
    """
    Test G14-M13: models.Payment records, payment queries, and BillingService patient
    balance remain strictly invariant and unaffected by ClinicalCharges and parity tools.
    """
    t1 = s35_seed["tenant_1"]
    pat2 = s35_seed["pat_2"]
    doc1 = s35_seed["doc_1"]

    now = datetime.now(timezone.utc)
    t_row = models.Treatment(
        patient_id=pat2.id,
        doctor_id=doc1.id,
        procedure="Root Canal Treatment",
        cost=Decimal("2500.00"),
        discount=Decimal("200.00"),
        date=now,
        tenant_id=t1.id,
    )
    p_row = models.Payment(
        patient_id=pat2.id,
        amount=Decimal("1500.00"),
        date=now,
        tenant_id=t1.id,
    )
    async_db_session.add_all([t_row, p_row])
    await async_db_session.commit()

    # Baseline BillingService calculations
    billing_service = BillingService(async_db_session, t1.id)
    base_balance = await billing_service.get_outstanding_balance(patient_id=pat2.id)
    assert base_balance == 800.0  # (2500 - 200) - 1500 = 800

    treatments_before = await get_treatments(async_db_session, patient_id=pat2.id, tenant_id=t1.id)
    payments_before = await get_payments(async_db_session, patient_id=pat2.id, tenant_id=t1.id)
    assert len(treatments_before) == 1
    assert len(payments_before) == 1

    # Create various ClinicalCharge records
    wi_a = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=pat2.id, kind="procedure", code="REST_COMPOSITE", status="completed", version_id=1
    )
    wi_b = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=pat2.id, kind="procedure", code="ENDO_RCT", status="completed", version_id=1
    )
    async_db_session.add_all([wi_a, wi_b])
    await async_db_session.flush()

    cc1 = models.ClinicalCharge(
        tenant_id=t1.id,
        patient_id=pat2.id,
        work_item_id=wi_a.id,
        amount=Decimal("10000.00"),
        discount=Decimal("0.00"),
        status="pending",
    )
    cc2 = models.ClinicalCharge(
        tenant_id=t1.id,
        patient_id=pat2.id,
        work_item_id=wi_b.id,
        amount=Decimal("20000.00"),
        discount=Decimal("0.00"),
        status="invoiced",
    )
    async_db_session.add_all([cc1, cc2])
    await async_db_session.commit()

    # Re-evaluate BillingService and CRUD queries
    new_balance = await billing_service.get_outstanding_balance(patient_id=pat2.id)
    treatments_after = await get_treatments(async_db_session, patient_id=pat2.id, tenant_id=t1.id)
    payments_after = await get_payments(async_db_session, patient_id=pat2.id, tenant_id=t1.id)

    assert new_balance == base_balance == 800.0, "Patient balance remained strictly invariant!"
    assert len(treatments_after) == len(treatments_before) == 1
    assert len(payments_after) == len(payments_before) == 1
    assert payments_after[0].amount == Decimal("1500.00")


@pytest.mark.asyncio
async def test_g14_m14_multi_tenant_financial_isolation_regression(async_db_session, s35_seed):
    """
    Test G14-M14: Financial regression suite - multi-tenant financial isolation.
    Tenant Alpha transactions, lab charges, and parity/anomaly reports NEVER
    leak into or alter Tenant Beta metrics.
    """
    t1 = s35_seed["tenant_1"]
    t2 = s35_seed["tenant_2"]
    pat1 = s35_seed["pat_1"]
    pat_beta = s35_seed["pat_beta"]
    doc1 = s35_seed["doc_1"]
    doc2 = s35_seed["doc_2"]

    now = datetime.now(timezone.utc)
    # Tenant 1: 50,000 charge and 30,000 payment
    t1_t = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        cost=Decimal("50000.00"),
        discount=Decimal("0.00"),
        date=now,
        tenant_id=t1.id,
    )
    t1_p = models.Payment(
        patient_id=pat1.id,
        amount=Decimal("30000.00"),
        date=now,
        tenant_id=t1.id,
    )
    # Tenant 2: 1,000 charge and 1,000 payment
    t2_t = models.Treatment(
        patient_id=pat_beta.id,
        doctor_id=doc2.id,
        cost=Decimal("1000.00"),
        discount=Decimal("0.00"),
        date=now,
        tenant_id=t2.id,
    )
    t2_p = models.Payment(
        patient_id=pat_beta.id,
        amount=Decimal("1000.00"),
        date=now,
        tenant_id=t2.id,
    )
    async_db_session.add_all([t1_t, t1_p, t2_t, t2_p])
    await async_db_session.commit()

    parity_service = FinanceParityService(async_db_session)

    # Parity reports for both tenants
    rep1 = await parity_service.compute_tenant_parity(tenant_id=t1.id)
    rep2 = await parity_service.compute_tenant_parity(tenant_id=t2.id)

    assert rep1.total_legacy_charges == Decimal("50000.00")
    assert rep1.total_payments == Decimal("30000.00")
    assert rep1.total_legacy_balance == Decimal("20000.00")

    assert rep2.total_legacy_charges == Decimal("1000.00")
    assert rep2.total_payments == Decimal("1000.00")
    assert rep2.total_legacy_balance == Decimal("0.00")

    # Anomaly reports for both tenants
    anom1 = await parity_service.detect_lab_double_charge_anomalies(tenant_id=t1.id)
    anom2 = await parity_service.detect_lab_double_charge_anomalies(tenant_id=t2.id)

    assert anom1.tenant_id == t1.id
    assert anom2.tenant_id == t2.id


@pytest.mark.asyncio
async def test_treatment_id_linked_lab_order_treated_as_single_charge_no_double_counting(async_db_session, s35_seed):
    """
    Step 3 test: Verify that finance_parity_service treats a treatment_id-linked LabOrder
    as ONE charge (no double counting with the linked treatment's cost) and generates zero anomalies.
    """
    t1 = s35_seed["tenant_1"]
    doc1 = s35_seed["doc_1"]
    pat1 = s35_seed["pat_1"]
    now = datetime.now(timezone.utc)

    # 1. Laboratory and lab payment
    lab = models.Laboratory(name="Master Dental Lab", tenant_id=t1.id)
    async_db_session.add(lab)
    await async_db_session.flush()

    lab_payment = models.LabPayment(
        laboratory_id=lab.id,
        amount=Decimal("450.00"),
        date=now,
        notes="B2B lab payment for crown fabrication",
        tenant_id=t1.id,
    )
    async_db_session.add(lab_payment)

    # 2. Clinical Treatment (Crown recorded on tooth 16, cost = 2500.00)
    treatment = models.Treatment(
        patient_id=pat1.id,
        doctor_id=doc1.id,
        tooth_number=16,
        procedure="تركيبة زيركون (Crown Zirconia)",
        cost=Decimal("2500.00"),
        discount=Decimal("0.00"),
        date=now,
        notes="Clinical crown preparation",
        tenant_id=t1.id,
    )
    async_db_session.add(treatment)
    await async_db_session.flush()

    # 3. LabOrder linked directly via treatment_id (no synthetic treatment)
    lab_order = models.LabOrder(
        patient_id=pat1.id,
        laboratory_id=lab.id,
        treatment_id=treatment.id,
        doctor_id=doc1.id,
        work_type="Crown",
        tooth_number="16",
        shade="A2",
        material="Zirconia",
        cost=Decimal("450.00"),
        price_to_patient=Decimal("0.00"),  # Lab fee absorbed into procedure price
        status="in_progress",
        order_date=now,
        tenant_id=t1.id,
    )
    async_db_session.add(lab_order)
    await async_db_session.commit()

    parity_service = FinanceParityService(async_db_session)

    # 4. Parity computation: patient has exactly ONE legacy charge of 2500.00
    parity_detail = await parity_service.compute_patient_parity(tenant_id=t1.id, patient_id=pat1.id)
    assert parity_detail.legacy_charges == Decimal("2500.00"), "Must be exactly ONE charge for the treatment (no double counting)"

    # 5. Anomaly audit: zero anomalies, zero overcharge
    anom_report = await parity_service.detect_lab_double_charge_anomalies(tenant_id=t1.id)
    pat_anomalies = [a for a in anom_report.anomalies if a.patient_id == pat1.id]
    assert len(pat_anomalies) == 0, f"Expected 0 anomalies for treatment_id-linked order, got: {pat_anomalies}"

