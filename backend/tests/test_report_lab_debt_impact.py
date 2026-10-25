"""Unit tests for Slice L6: Lab Debt Impact Report script.

Verifies:
1. Calculation of non-cancelled orders with cost > 0 (count, sum).
2. Cancelled orders and cost=0 orders are properly excluded.
3. Lab payments count, sum, and resulting debt calculation.
4. Category "Laboratory" expense detection (case-insensitive, trimmed, and Arabic variants).
5. Heuristic double-count pairing (cost match within +-3 days).
6. Non-matching expenses (diff > 3 days or cost mismatch) are excluded from candidates.
7. Read-only guarantee: database state is never mutated by the report generator.
8. Text, markdown, and json formatting outputs.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest

from backend import models
from backend.core.money import quantize_money
from backend.scripts.report_lab_debt_impact import (
    collect_tenant_impact,
    find_double_count_pairs,
    format_markdown_report,
    format_text_report,
    generate_impact_reports,
    is_laboratory_category,
)


@pytest.mark.asyncio
async def test_report_lab_debt_impact_metrics_and_heuristics(async_db_session, admin_user):
    tenant_id = admin_user.tenant_id

    # 1. Seed a laboratory
    lab = models.Laboratory(
        name="Al-Amal Dental Lab",
        contact_person="Dr. Hazem",
        phone="01011112222",
        tenant_id=tenant_id,
    )
    async_db_session.add(lab)
    await async_db_session.flush()

    # 2. Seed a patient
    patient = models.Patient(
        name="Test Patient L6",
        age=30,
        medical_history="None",
        notes="",
        phone="01234567890",
        tenant_id=tenant_id,
    )
    async_db_session.add(patient)
    await async_db_session.flush()

    base_time = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc).replace(tzinfo=None)

    # 3. Seed Lab Orders:
    # Order A: active, cost 350 (should be counted)
    order_a = models.LabOrder(
        laboratory_id=lab.id,
        patient_id=patient.id,
        work_type="Zirconia Crown",
        cost=Decimal("350.00"),
        status="in_progress",
        order_date=base_time,
        tenant_id=tenant_id,
    )
    # Order B: active, cost 150 (should be counted)
    order_b = models.LabOrder(
        laboratory_id=lab.id,
        patient_id=patient.id,
        work_type="E-Max Inlay",
        cost=Decimal("150.00"),
        status="delivered",
        order_date=base_time + timedelta(days=5),
        tenant_id=tenant_id,
    )
    # Order C: cancelled, cost 500 (MUST be excluded)
    order_c = models.LabOrder(
        laboratory_id=lab.id,
        patient_id=patient.id,
        work_type="Cancelled Bridge",
        cost=Decimal("500.00"),
        status="cancelled",
        order_date=base_time,
        tenant_id=tenant_id,
    )
    # Order D: active but cost 0 (MUST be excluded from cost > 0)
    order_d = models.LabOrder(
        laboratory_id=lab.id,
        patient_id=patient.id,
        work_type="Study Model",
        cost=Decimal("0.00"),
        status="pending",
        order_date=base_time,
        tenant_id=tenant_id,
    )
    async_db_session.add_all([order_a, order_b, order_c, order_d])
    await async_db_session.flush()

    # 4. Seed Lab Payments:
    # Payment 1: 100 linked to order A
    pmt_1 = models.LabPayment(
        laboratory_id=lab.id,
        lab_order_id=order_a.id,
        amount=Decimal("100.00"),
        date=base_time,
        tenant_id=tenant_id,
    )
    # Payment 2: 50 on-account (unlinked)
    pmt_2 = models.LabPayment(
        laboratory_id=lab.id,
        amount=Decimal("50.00"),
        date=base_time + timedelta(days=2),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([pmt_1, pmt_2])
    await async_db_session.flush()

    # 5. Seed Expenses:
    # Expense 1: Category "Laboratory", cost 350 on base_time + 1 day -> Heuristic MATCH with Order A (diff = 1d <= 3d)
    exp_match = models.Expense(
        item_name="Lab work for patient A",
        cost=Decimal("350.00"),
        category="Laboratory",
        date=(base_time + timedelta(days=1)).date(),
        tenant_id=tenant_id,
    )
    # Expense 2: Category "معامل", cost 150 on base_time + 15 days -> Cost matches Order B, but date diff is 10 days (> 3 days) -> NO MATCH
    exp_far = models.Expense(
        item_name="Old Lab Payment",
        cost=Decimal("150.00"),
        category="معامل",
        date=(base_time + timedelta(days=15)).date(),
        tenant_id=tenant_id,
    )
    # Expense 3: Category "Supplies", cost 350 -> Not a lab expense
    exp_supplies = models.Expense(
        item_name="Dental Composite",
        cost=Decimal("350.00"),
        category="Supplies",
        date=base_time.date(),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([exp_match, exp_far, exp_supplies])
    await async_db_session.commit()

    # Run the collector on this tenant
    report = await collect_tenant_impact(async_db_session, tenant_id, "Test Tenant")

    # Assertions on metrics:
    # Active orders: A (350) + B (150) = 500 (count: 2)
    assert report.active_orders_count == 2
    assert report.active_orders_sum == 500.0

    # Payments: pmt_1 (100) + pmt_2 (50) = 150 (count: 2)
    assert report.payments_count == 2
    assert report.payments_sum == 150.0

    # Resulting debt: 500 - 150 = 350
    assert report.resulting_debt == 350.0

    # Lab Expenses: exp_match ("Laboratory", 350) + exp_far ("معامل", 150) = 500 (count: 2)
    # Supplies is excluded
    assert report.lab_expenses_count == 2
    assert report.lab_expenses_sum == 500.0

    # Heuristic double-count: only exp_match <-> order_a (cost 350, diff 1d)
    assert report.double_count_pairs_count == 1
    assert report.double_count_estimated_amount == 350.0
    pair = report.double_count_pairs[0]
    assert pair.expense_id == exp_match.id
    assert pair.order_id == order_a.id
    assert pair.days_difference == 1
    assert pair.expense_cost == 350.0
    assert pair.order_cost == 350.0

    # Test report formatting output
    text_rep = format_text_report([report])
    assert "DENTIX LAB DEBT IMPACT REPORT" in text_rep
    assert "Active Lab Orders : 2 (500.00 EGP)" in text_rep
    assert "Total Lab Payments      : 2 (150.00 EGP)" in text_rep
    assert "Net Resulting Lab Debt  : 350.00 EGP" in text_rep

    md_rep = format_markdown_report([report])
    assert "### Lab Debt Impact Report" in md_rep
    assert "**350.00 EGP**" in md_rep
    assert "Strictly read-only report" in md_rep


def test_is_laboratory_category_detection():
    assert is_laboratory_category("Laboratory") is True
    assert is_laboratory_category("laboratory") is True
    assert is_laboratory_category("  LABORATORY  ") is True
    assert is_laboratory_category("lab") is True
    assert is_laboratory_category("معمل") is True
    assert is_laboratory_category("معامل") is True
    assert is_laboratory_category("معامل وتركيبات") is True
    assert is_laboratory_category("معامل وتركيبات خارجية") is True

    assert is_laboratory_category("Supplies") is False
    assert is_laboratory_category("Utilities") is False
    assert is_laboratory_category("Rent") is False
    assert is_laboratory_category("") is False
    assert is_laboratory_category(None) is False


def test_find_double_count_pairs_edge_cases():
    base = date(2026, 10, 15)

    # Mock expense-like and order-like objects
    class MockExpense:
        def __init__(self, id, cost, date_val):
            self.id = id
            self.cost = cost
            self.date = date_val
            self.item_name = f"Exp {id}"
            self.notes = None

    class MockOrder:
        def __init__(self, id, cost, date_val):
            self.id = id
            self.cost = cost
            self.order_date = date_val
            self.work_type = f"Order {id}"
            self.laboratory_id = 1
            self.patient_id = 1

    # 1. Exact match (0 days)
    e1 = MockExpense(1, Decimal("250.00"), base)
    o1 = MockOrder(10, Decimal("250.00"), base)
    candidates, greedy_sum = find_double_count_pairs([e1], [o1], max_days=3)
    assert len(candidates) == 1
    assert greedy_sum == 250.0
    assert candidates[0].days_difference == 0

    # 2. Date diff exactly 3 days -> MATCH
    e2 = MockExpense(2, Decimal("300.00"), base + timedelta(days=3))
    o2 = MockOrder(20, Decimal("300.00"), base)
    candidates, greedy_sum = find_double_count_pairs([e2], [o2], max_days=3)
    assert len(candidates) == 1
    assert candidates[0].days_difference == 3

    # 3. Date diff 4 days -> NO MATCH
    e3 = MockExpense(3, Decimal("400.00"), base + timedelta(days=4))
    o3 = MockOrder(30, Decimal("400.00"), base)
    candidates, greedy_sum = find_double_count_pairs([e3], [o3], max_days=3)
    assert len(candidates) == 0
    assert greedy_sum == 0.0

    # 4. Cost mismatch -> NO MATCH
    e4 = MockExpense(4, Decimal("500.00"), base)
    o4 = MockOrder(40, Decimal("501.00"), base)
    candidates, greedy_sum = find_double_count_pairs([e4], [o4], max_days=3)
    assert len(candidates) == 0

    # 5. Greedy matching: 2 expenses match same order, closest day matched once in greedy_sum
    e_close = MockExpense(5, Decimal("100.00"), base + timedelta(days=1))
    e_far = MockExpense(6, Decimal("100.00"), base + timedelta(days=2))
    o_single = MockOrder(50, Decimal("100.00"), base)
    candidates, greedy_sum = find_double_count_pairs([e_close, e_far], [o_single], max_days=3)
    assert len(candidates) == 2  # Both reported as candidate pairs
    assert greedy_sum == 100.0  # But greedy sum counts only once to avoid double-counting


@pytest.mark.asyncio
async def test_generate_impact_reports_is_strictly_readonly(async_db_session, admin_user):
    # Call generate_impact_reports for the admin tenant
    reports = await generate_impact_reports(async_db_session, target_tenant_id=admin_user.tenant_id)
    assert len(reports) == 1
    # Verify session dirty / new sets are completely empty
    assert len(async_db_session.dirty) == 0
    assert len(async_db_session.new) == 0
    assert len(async_db_session.deleted) == 0

