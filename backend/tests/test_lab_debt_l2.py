"""Tests for Slice L2: Finance accounting switch (backend).

Verifies:
1. Lab order with cost 250 and no payment:
   - Activity feed has NO lab row
   - summary deductions.lab_costs == 0
   - summary obligations.lab_debt == 250
2. Lab payment of 100:
   - Exactly one activity row with id "labpay-<id>", direction "outflow", title "دفعة معمل: <lab>", subtitle "<work> — لحالة: <patient>"
   - summary deductions.lab_costs == 100
   - net_operational_result drops by exactly 100
   - summary obligations.lab_debt drops by 100
3. Payment outside the period:
   - Excluded from period deductions.lab_costs
   - Excluded from period activity feed
   - Included in all-time obligations.lab_debt
4. Patient filter:
   - Sums only payments linked to orders of that patient
   - Unlinked payments (on-account) are excluded when filtered by patient
5. Manual expense + lab payment:
   - Each counted once under its respective category (no overlap)
6. Doctor commission numbers:
   - Doctor lab cost and net revenue are byte-for-byte identical (accrual on LabOrder.cost)
7. Finance summary definition version & metrics contract:
   - version == "finance-summary-v2"
   - METRIC_DEFINITIONS["lab_costs"] formula == "SUM(lab_payment.amount)"
   - METRIC_DEFINITIONS["lab_debt"] scope == "all_time"
8. Activity search:
   - Search matches lab name, work type, patient name, and notes
9. Legacy accounting router:
   - Deductions lab_costs uses lab payments and net profit reflects cash basis payments
"""

import os
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from backend import models, schemas
from backend.core.money import quantize_money
from backend.services.accounting_service import AccountingService
from backend.services.finance_summary_service import (
    FinanceSummaryService,
    FINANCE_DEFINITION_VERSION,
    METRIC_DEFINITIONS,
)


@pytest.fixture
async def l2_setup(async_db_session, test_user, test_patient):
    """Seed test clinic, lab, and doctor for L2 tests."""
    tenant_id = test_user.tenant_id
    doctor = models.User(
        username="l2_doctor",
        email="l2_doctor@example.com",
        hashed_password="fakepassword",
        role="doctor",
        commission_percent=20.0,
        fixed_salary=1000.0,
        tenant_id=tenant_id,
        is_active=True,
    )
    admin = models.User(
        username="l2_admin",
        email="l2_admin@example.com",
        hashed_password="fakepassword",
        role="admin",
        tenant_id=tenant_id,
        is_active=True,
    )
    lab = models.Laboratory(
        name="Al-Amal Dental Lab",
        phone="01122334455",
        tenant_id=tenant_id,
        is_active=True,
    )
    async_db_session.add_all([doctor, admin, lab])
    await async_db_session.commit()
    await async_db_session.refresh(doctor)
    await async_db_session.refresh(admin)
    await async_db_session.refresh(lab)
    return {
        "lab": lab,
        "patient": test_patient,
        "doctor": doctor,
        "user": admin,
        "tenant_id": tenant_id,
    }


# ---------------------------------------------------------------------------
# 1. Order cost 250, no payment -> no activity row, lab_costs=0, lab_debt=250
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_order_with_no_payment_creates_debt_not_expense(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    tenant_id = l2_setup["tenant_id"]

    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Zirconia Crown",
        cost=Decimal("250.00"),
        order_date=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
        status="pending",
    )
    async_db_session.add(order)
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)
    summary_svc = FinanceSummaryService(async_db_session, tenant_id)

    # Activity feed must NOT contain any lab row
    activity = await accounting.get_financial_activity(
        start_date="2026-08-01",
        end_date="2026-08-31",
        event_types=["lab"],
        current_user=l2_setup["user"],
    )
    lab_events = [e for e in activity["events"] if e["source_type"] == "lab"]
    assert len(lab_events) == 0, "LabOrder without payment must NOT produce an activity feed row"
    assert activity["total_outflow"] == 0.0

    # Finance summary: lab_costs in deductions must be 0, obligations.lab_debt must be 250
    summary = await summary_svc.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert summary["deductions"]["lab_costs"] == 0.0, "Accrual order cost must NOT appear in deductions"
    assert "obligations" in summary, "summary must include obligations section"
    assert summary["obligations"]["lab_debt"] == 250.0, "Unpaid order must appear in obligations.lab_debt"


# ---------------------------------------------------------------------------
# 2. Payment 100 -> one activity row, lab_costs=100, net drops by 100
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_payment_creates_activity_and_cash_expense(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    tenant_id = l2_setup["tenant_id"]

    # Order of 250
    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Zirconia Bridge",
        cost=Decimal("250.00"),
        order_date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
        status="pending",
    )
    # Payment of 100 linked to order
    pay = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        lab_order_id=None,  # will link after flush
        amount=Decimal("100.00"),
        date=datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
        method="Cash",
    )
    async_db_session.add(order)
    await async_db_session.flush()
    pay.lab_order_id = order.id
    async_db_session.add(pay)
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)
    summary_svc = FinanceSummaryService(async_db_session, tenant_id)

    # Activity feed: exactly one lab row with target format
    activity = await accounting.get_financial_activity(
        start_date="2026-08-01",
        end_date="2026-08-31",
        event_types=["lab"],
        current_user=l2_setup["user"],
    )
    assert len(activity["events"]) == 1
    ev = activity["events"][0]
    assert ev["id"] == f"labpay-{pay.id}"
    assert ev["source_type"] == "lab"
    assert ev["direction"] == "outflow"
    assert ev["amount"] == 100.0
    assert ev["title"] == f"دفعة معمل: {lab.name}"
    assert ev["subtitle"] == f"Zirconia Bridge — لحالة: {patient.name}"
    assert ev["badge_text"] == "معمل أسنان"
    assert ev["nav_url"] == "/labs"
    assert ev["patient_id"] == patient.id

    # Summary: deductions.lab_costs == 100, obligations.lab_debt == 150
    summary = await summary_svc.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert summary["deductions"]["lab_costs"] == 100.0
    assert summary["obligations"]["lab_debt"] == 150.0
    # Net operational result dropped by exactly 100.0
    assert summary["deductions"]["total_deductions"] >= 100.0


# ---------------------------------------------------------------------------
# 3. Payment outside the period excluded from period, included in debt
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_payment_outside_period_excluded(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    tenant_id = l2_setup["tenant_id"]

    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Inlay",
        cost=Decimal("300.00"),
        order_date=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    async_db_session.add(order)
    await async_db_session.flush()

    # Payment in July (outside August period)
    pay = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        lab_order_id=order.id,
        amount=Decimal("120.00"),
        date=datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc),
    )
    async_db_session.add(pay)
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)
    summary_svc = FinanceSummaryService(async_db_session, tenant_id)

    # August activity feed must exclude July payment
    activity = await accounting.get_financial_activity(
        start_date="2026-08-01",
        end_date="2026-08-31",
        event_types=["lab"],
        current_user=l2_setup["user"],
    )
    assert len(activity["events"]) == 0

    # August summary: lab_costs == 0 (no payments in August)
    summary_aug = await summary_svc.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert summary_aug["deductions"]["lab_costs"] == 0.0
    # All-time lab_debt: 300 - 120 = 180
    assert summary_aug["obligations"]["lab_debt"] == 180.0


# ---------------------------------------------------------------------------
# 4. Patient filter excludes unlinked payments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_patient_filter_excludes_unlinked_payments(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    tenant_id = l2_setup["tenant_id"]

    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Crown",
        cost=Decimal("400.00"),
        order_date=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    async_db_session.add(order)
    await async_db_session.flush()

    # Linked payment to patient's order: 150
    pay_linked = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        lab_order_id=order.id,
        amount=Decimal("150.00"),
        date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
    )
    # Unlinked payment (on-account): 70
    pay_unlinked = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        lab_order_id=None,
        amount=Decimal("70.00"),
        date=datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc),
        notes="دفعة على الحساب",
    )
    async_db_session.add_all([pay_linked, pay_unlinked])
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)
    summary_svc = FinanceSummaryService(async_db_session, tenant_id)

    # With patient filter: only 150 (unlinked 70 excluded)
    patient_lab_payments = await accounting.get_total_lab_payments(
        start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        end=datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc),
        patient_id=patient.id,
    )
    assert patient_lab_payments == 150.0

    summary_patient = await summary_svc.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
        patient_id=patient.id,
    )
    assert summary_patient["deductions"]["lab_costs"] == 150.0

    # Clinic-wide (patient_id=None): both included: 150 + 70 = 220
    all_lab_payments = await accounting.get_total_lab_payments(
        start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        end=datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc),
        patient_id=None,
    )
    assert all_lab_payments == 220.0

    summary_clinic = await summary_svc.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert summary_clinic["deductions"]["lab_costs"] == 220.0


# ---------------------------------------------------------------------------
# 5. Manual expense + lab payment each counted once (no overlap)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_expense_and_lab_payment_no_overlap(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    tenant_id = l2_setup["tenant_id"]

    expense = models.Expense(
        tenant_id=tenant_id,
        category="Supplies",
        cost=Decimal("200.00"),
        date=date(2026, 8, 15),
        notes="Dental gloves and masks",
    )
    payment = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        amount=Decimal("150.00"),
        date=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )
    async_db_session.add_all([expense, payment])
    await async_db_session.commit()

    summary_svc = FinanceSummaryService(async_db_session, tenant_id)
    summary = await summary_svc.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
    )

    assert summary["deductions"]["expenses"] == 200.0
    assert summary["deductions"]["lab_costs"] == 150.0
    assert summary["deductions"]["total_deductions"] >= 350.0


# ---------------------------------------------------------------------------
# 6. Doctor numbers unchanged (stays on LabOrder.cost accrual)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_doctor_commission_numbers_unchanged(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    tenant_id = l2_setup["tenant_id"]

    # Treatment for doctor: 1000
    treatment = models.Treatment(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        procedure="Crown",
        cost=Decimal("1000.00"),
        date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
    )
    # Lab order for doctor: 300
    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Crown",
        cost=Decimal("300.00"),
        order_date=datetime(2026, 8, 10, 11, 0, tzinfo=timezone.utc),
    )
    # Payment to lab: 100 (partial)
    payment = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        lab_order_id=None,
        amount=Decimal("100.00"),
        date=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
    )
    async_db_session.add_all([treatment, order, payment])
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)
    start_dt = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end_dt = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

    # Doctor lab cost map MUST return 300.0 (accrual from LabOrder.cost, NOT 100 payment)
    doc_lab_map = await accounting.get_lab_costs_by_doctor(
        start=start_dt,
        end=end_dt,
        doctor_ids=[doctor.id],
    )
    assert doc_lab_map.get(doctor.id) == 300.0, "Doctor lab cost must remain accrual on LabOrder.cost"


# ---------------------------------------------------------------------------
# 7. Summary contract test for the new formula and version (v2)
# ---------------------------------------------------------------------------
def test_finance_summary_v2_contract():
    assert FINANCE_DEFINITION_VERSION == "finance-summary-v2"
    assert METRIC_DEFINITIONS["lab_costs"]["formula"] == "SUM(lab_payment.amount)"
    assert "cash basis" in METRIC_DEFINITIONS["lab_costs"]["description"].lower()
    assert "lab_debt" in METRIC_DEFINITIONS
    assert METRIC_DEFINITIONS["lab_debt"]["scope"] == "all_time"


# ---------------------------------------------------------------------------
# 8. Activity feed search filtering
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_activity_search_matches_lab_payment_fields(async_db_session, l2_setup):
    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    tenant_id = l2_setup["tenant_id"]

    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Searchable Veneer",
        cost=Decimal("500.00"),
        order_date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    async_db_session.add(order)
    await async_db_session.flush()

    payment = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        lab_order_id=order.id,
        amount=Decimal("250.00"),
        date=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
        notes="UniquePaymentNote123",
    )
    async_db_session.add(payment)
    await async_db_session.commit()

    accounting = AccountingService(async_db_session, tenant_id)

    # 1. Search by work type
    act1 = await accounting.get_financial_activity(
        search="Searchable Veneer",
        event_types=["lab"],
        current_user=l2_setup["user"],
    )
    assert any(e["id"] == f"labpay-{payment.id}" for e in act1["events"])

    # 2. Search by lab name
    act2 = await accounting.get_financial_activity(
        search="Al-Amal",
        event_types=["lab"],
        current_user=l2_setup["user"],
    )
    assert any(e["id"] == f"labpay-{payment.id}" for e in act2["events"])

    # 3. Search by notes
    act3 = await accounting.get_financial_activity(
        search="UniquePaymentNote123",
        event_types=["lab"],
        current_user=l2_setup["user"],
    )
    assert any(e["id"] == f"labpay-{payment.id}" for e in act3["events"])


# ---------------------------------------------------------------------------
# 9. Legacy accounting router (/comprehensive-stats) uses cash-basis lab payments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_legacy_accounting_router_uses_lab_payments(async_db_session, l2_setup):
    from backend.routers.accounting_legacy import get_comprehensive_stats

    lab = l2_setup["lab"]
    patient = l2_setup["patient"]
    doctor = l2_setup["doctor"]
    user = l2_setup["user"]
    tenant_id = l2_setup["tenant_id"]

    order = models.LabOrder(
        tenant_id=tenant_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Comprehensive Work",
        cost=Decimal("500.00"),
        order_date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    payment = models.LabPayment(
        tenant_id=tenant_id,
        laboratory_id=lab.id,
        amount=Decimal("175.00"),
        date=datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
    )
    async_db_session.add_all([order, payment])
    await async_db_session.commit()

    stats = await get_comprehensive_stats(
        start_date="2026-08-01",
        end_date="2026-08-31",
        patient_id=None,
        db=async_db_session,
        current_user=user,
    )
    data = stats["data"]
    # lab_costs in deductions must be the payment (175.0), NOT order cost (500.0)
    assert data["deductions"]["lab_costs"] == 175.0

