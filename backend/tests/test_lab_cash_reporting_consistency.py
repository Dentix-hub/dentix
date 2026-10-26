"""Tests for PR-3: Cash-basis lab reporting consistency across all financial surfaces.

Verifies:
1. For the same period and data, Finance Summary `lab_costs` (cash basis)
   equals the lab expense reported by every modified endpoint/surface:
   - routers/metrics_decimal.py (`get_profitability`)
   - routers/metrics_legacy.py (`get_profitability`)
   - crud/reporting.py (`get_financial_stats`)
   - crud/reporting_legacy.py (`get_financial_stats`)
   - crud/billing.py (`get_financial_stats`)
2. Per-doctor lab cost queries remain accrual-based (LabOrder.cost scoped to doctor).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest

from backend import models
from backend.crud import billing as crud_billing
from backend.crud import reporting as crud_reporting
from backend.crud import reporting_legacy as crud_reporting_legacy
from backend.routers import metrics_decimal, metrics_legacy
from backend.services.finance_summary_service import FinanceSummaryService


@pytest.mark.asyncio
async def test_lab_cash_reporting_consistency_across_surfaces(async_db_session, admin_user):
    tenant_id = admin_user.tenant_id
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()

    # 1. Create a Laboratory
    lab = models.Laboratory(
        name="Consistency Test Lab",
        contact_person="Lab Tech",
        phone="0123456789",
        tenant_id=tenant_id,
    )
    async_db_session.add(lab)
    await async_db_session.flush()

    # 2. Create a Doctor and Patient
    doctor = models.User(
        username=f"doc_{tenant_id}",
        email=f"doc_{tenant_id}@example.com",
        hashed_password="hash",
        role="doctor",
        tenant_id=tenant_id,
        is_active=True,
    )
    async_db_session.add(doctor)
    await async_db_session.flush()

    patient = models.Patient(
        name="Consistency Patient",
        age=30,
        phone="01011112222",
        medical_history="",
        notes="",
        assigned_doctor_id=doctor.id,
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add(patient)
    await async_db_session.flush()

    # 3. Create Lab Orders (accrual cost = 1200 total)
    order1 = models.LabOrder(
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Zirconia Crown",
        cost=Decimal("700.00"),
        price_to_patient=Decimal("1500.00"),
        status="completed",
        order_date=now,
        tenant_id=tenant_id,
    )
    order2 = models.LabOrder(
        patient_id=patient.id,
        doctor_id=doctor.id,
        laboratory_id=lab.id,
        work_type="Emax Veneer",
        cost=Decimal("500.00"),
        price_to_patient=Decimal("1200.00"),
        status="in_progress",
        order_date=now,
        tenant_id=tenant_id,
    )
    async_db_session.add_all([order1, order2])
    await async_db_session.flush()

    # 4. Create Lab Payments (cash payments = 450 total today, order cost = 1200)
    # Payment 1: allocated to order1 (300.00)
    payment1 = models.LabPayment(
        laboratory_id=lab.id,
        lab_order_id=order1.id,
        amount=Decimal("300.00"),
        date=now,
        tenant_id=tenant_id,
    )
    # Payment 2: unallocated payment (150.00)
    payment2 = models.LabPayment(
        laboratory_id=lab.id,
        lab_order_id=None,
        amount=Decimal("150.00"),
        date=now,
        tenant_id=tenant_id,
    )
    async_db_session.add_all([payment1, payment2])
    await async_db_session.commit()

    expected_cash_lab_total = 450.0  # 300 + 150
    accrual_orders_cost = 1200.0     # 700 + 500

    # -------------------------------------------------------------------------
    # Surface 1: Finance Summary Service (cash basis)
    # -------------------------------------------------------------------------
    start_str = (today - timedelta(days=1)).isoformat()
    end_str = (today + timedelta(days=1)).isoformat()
    summary_service = FinanceSummaryService(async_db_session, tenant_id)
    summary = await summary_service.get_summary(start_date=start_str, end_date=end_str)
    finance_lab_costs = summary["deductions"]["lab_costs"]
    assert finance_lab_costs == pytest.approx(expected_cash_lab_total), (
        f"FinanceSummary deductions.lab_costs ({finance_lab_costs}) must match cash payments ({expected_cash_lab_total})"
    )

    # -------------------------------------------------------------------------
    # Surface 2: Metrics Decimal (get_profitability)
    # -------------------------------------------------------------------------
    metrics_dec_res = await metrics_decimal.get_profitability(
        period="24h",
        db=async_db_session,
        current_user=admin_user,
    )
    dec_lab_costs = metrics_dec_res["data"]["breakdown"]["lab_costs"]
    assert dec_lab_costs == pytest.approx(finance_lab_costs), (
        f"metrics_decimal lab_costs ({dec_lab_costs}) must match FinanceSummary ({finance_lab_costs})"
    )

    # -------------------------------------------------------------------------
    # Surface 3: Metrics Legacy (get_profitability)
    # -------------------------------------------------------------------------
    metrics_leg_res = await metrics_legacy.get_profitability(
        period="24h",
        db=async_db_session,
        current_user=admin_user,
    )
    leg_lab_costs = metrics_leg_res["data"]["breakdown"]["lab_costs"]
    assert leg_lab_costs == pytest.approx(finance_lab_costs), (
        f"metrics_legacy lab_costs ({leg_lab_costs}) must match FinanceSummary ({finance_lab_costs})"
    )

    # -------------------------------------------------------------------------
    # Surface 4: CRUD Reporting (get_financial_stats without doctor scope)
    # -------------------------------------------------------------------------
    rep_stats = await crud_reporting.get_financial_stats(
        async_db_session,
        tenant_id,
        timezone_name="UTC",
        business_date=today,
        doctor_patient_scope_id=None,
    )
    # With 0 manual expenses, today_expenses and total_expenses reflect lab costs
    assert rep_stats["today_expenses"] == pytest.approx(finance_lab_costs), (
        f"reporting.today_expenses ({rep_stats['today_expenses']}) must match FinanceSummary ({finance_lab_costs})"
    )
    assert rep_stats["total_expenses"] == pytest.approx(expected_cash_lab_total), (
        f"reporting.total_expenses ({rep_stats['total_expenses']}) must match total cash payments"
    )

    # -------------------------------------------------------------------------
    # Surface 5: CRUD Reporting Legacy (get_financial_stats without doctor scope)
    # -------------------------------------------------------------------------
    rep_leg_stats = await crud_reporting_legacy.get_financial_stats(
        async_db_session,
        tenant_id,
        timezone_name="UTC",
        business_date=today,
        doctor_patient_scope_id=None,
    )
    assert rep_leg_stats["today_expenses"] == pytest.approx(finance_lab_costs), (
        f"reporting_legacy.today_expenses ({rep_leg_stats['today_expenses']}) must match FinanceSummary ({finance_lab_costs})"
    )
    assert rep_leg_stats["total_expenses"] == pytest.approx(expected_cash_lab_total), (
        f"reporting_legacy.total_expenses ({rep_leg_stats['total_expenses']}) must match total cash payments"
    )

    # -------------------------------------------------------------------------
    # Surface 6: CRUD Billing (get_financial_stats without doctor scope)
    # -------------------------------------------------------------------------
    bill_stats = await crud_billing.get_financial_stats(
        async_db_session,
        tenant_id,
        doctor_id=None,
    )
    assert bill_stats["today_expenses"] == pytest.approx(finance_lab_costs), (
        f"billing.today_expenses ({bill_stats['today_expenses']}) must match FinanceSummary ({finance_lab_costs})"
    )
    assert bill_stats["total_expenses"] == pytest.approx(expected_cash_lab_total), (
        f"billing.total_expenses ({bill_stats['total_expenses']}) must match total cash payments"
    )

    # -------------------------------------------------------------------------
    # Untouched Invariant: Per-doctor lab cost queries remain accrual-based
    # -------------------------------------------------------------------------
    doctor_bill_stats = await crud_billing.get_financial_stats(
        async_db_session,
        tenant_id,
        doctor_id=doctor.id,
    )
    assert doctor_bill_stats["total_expenses"] == pytest.approx(accrual_orders_cost), (
        f"doctor-scoped billing lab expenses ({doctor_bill_stats['total_expenses']}) must stay accrual ({accrual_orders_cost})"
    )

    doctor_rep_stats = await crud_reporting.get_financial_stats(
        async_db_session,
        tenant_id,
        timezone_name="UTC",
        business_date=today,
        doctor_patient_scope_id=doctor.id,
        is_doctor=True,
    )
    assert doctor_rep_stats["total_expenses"] == pytest.approx(accrual_orders_cost), (
        f"doctor-scoped reporting lab expenses ({doctor_rep_stats['total_expenses']}) must stay accrual ({accrual_orders_cost})"
    )
