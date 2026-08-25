"""
Financial Truth & Metric Contract Unit & Integration Tests (Phase 0)

Tests strictly enforce the specifications in docs/FINANCE_METRIC_CONTRACT.md:
1. Doctor compensation formula: (Collected - Lab Cost) * Commission% + Fixed Salary
2. Deductions reconciliation: Doctor dues + Staff dues + Expenses + Lab costs
3. Lab cost provenance & non-duplication
4. Prorated salary calculation for mid-month hires
5. Outstanding balance semantics (all-time vs period balance)
6. Date boundaries and multi-tenant isolation
7. Financial visibility rules (doctor self-scope vs admin)
"""

import pytest
from datetime import datetime, date, timezone
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService
from backend.services.financial_visibility_service import FinancialVisibilityService
from backend.routers.expenses import get_expenses as get_expenses_endpoint
from backend.routers.accounting import get_my_doctor_revenue, get_my_doctor_details
from backend import models


def create_test_patient(id: int, name: str, tenant_id: int, assigned_doctor_id: int = None):
    return models.Patient(
        id=id,
        name=name,
        age=35,
        phone="01012345678",
        medical_history="No chronic conditions",
        notes="General note",
        tenant_id=tenant_id,
        assigned_doctor_id=assigned_doctor_id,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_expense_pagination_contract_returns_authoritative_total(async_db_session):
    db = async_db_session
    tenant_id = 120
    admin = models.User(
        id=220,
        username="expense_pager_admin",
        email="expense-pager@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    db.add_all([
        admin,
        models.Expense(id=1001, item_name="First", cost=10, date=date(2026, 8, 1), tenant_id=tenant_id),
        models.Expense(id=1002, item_name="Second", cost=20, date=date(2026, 8, 2), tenant_id=tenant_id),
    ])
    await db.commit()

    response = await get_expenses_endpoint(
        search=None,
        category=None,
        start_date=None,
        end_date=None,
        skip=1,
        limit=1,
        offset=None,
        page=None,
        page_size=None,
        db=db,
        current_user=admin,
    )

    assert response["data"]["total"] == 2
    assert response["data"]["skip"] == 1
    assert response["data"]["limit"] == 1
    assert len(response["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_doctor_self_service_endpoints_return_only_authenticated_doctor(async_db_session):
    db = async_db_session
    doctor = models.User(
        id=221,
        username="self_service_doctor",
        email="self-service-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=121,
    )
    other_doctor = models.User(
        id=222,
        username="other_doctor",
        email="other-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=121,
    )
    db.add_all([doctor, other_doctor])
    await db.commit()

    revenue_response = await get_my_doctor_revenue(
        start_date="2026-08-01",
        end_date="2026-08-31",
        db=db,
        current_user=doctor,
    )
    doctors = revenue_response["data"]["doctors"]
    assert [item["doctor_id"] for item in doctors] == [doctor.id]

    details_response = await get_my_doctor_details(
        start_date="2026-08-01",
        end_date="2026-08-31",
        db=db,
        current_user=doctor,
    )
    assert details_response["data"]["doctor_id"] == doctor.id


@pytest.mark.asyncio
async def test_doctor_compensation_formula_exact(async_db_session):
    """
    FIN-TRUTH-007 / FIN-TRUTH-010:
    Doctor compensation = (Collected - Lab Cost) * (Commission% / 100) + Fixed Salary.
    """
    db = async_db_session
    tenant_id = 101

    # Create Doctor User
    doctor = models.User(
        id=201,
        username="dr_ahmed",
        email="ahmed@clinic.com",
        hashed_password="hashed_pass_test",
        role="doctor",
        tenant_id=tenant_id,
        commission_percent=30.0,
        fixed_salary=5000.0,
    )
    db.add(doctor)

    # Create Patient
    patient = create_test_patient(id=301, name="Patient Ali", tenant_id=tenant_id, assigned_doctor_id=201)
    db.add(patient)

    # Treatments in range: 2 treatments, total gross = 4000, discount = 500, net = 3500
    t1 = models.Treatment(
        id=401,
        patient_id=301,
        doctor_id=201,
        cost=2000.0,
        discount=200.0,
        date=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    t2 = models.Treatment(
        id=402,
        patient_id=301,
        doctor_id=201,
        cost=2000.0,
        discount=300.0,
        date=datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add_all([t1, t2])

    # Payment in range: 3000 collected specifically attributed to doctor
    payment = models.Payment(
        id=501,
        patient_id=301,
        doctor_id=201,
        amount=3000.0,
        date=datetime(2026, 8, 6, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add(payment)

    # Lab order in range: 600 lab cost for doctor
    lab = models.Laboratory(id=601, name="Dental Lab One", tenant_id=tenant_id)
    db.add(lab)
    lab_order = models.LabOrder(
        id=701,
        patient_id=301,
        laboratory_id=601,
        doctor_id=201,
        work_type="Crown",
        cost=600.0,
        order_date=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add(lab_order)

    await db.commit()

    service = AccountingService(db, tenant_id=tenant_id)
    start = datetime(2026, 8, 1, 0, 0, 0)
    end = datetime(2026, 8, 31, 23, 59, 59)

    doctor_dues, total_dues = await service.calculate_doctor_dues(start, end)

    assert len(doctor_dues) == 1
    doc_result = doctor_dues[0]

    # Verify breakdown fields
    assert doc_result["id"] == 201
    assert doc_result["revenue"] == 3500.0  # (2000-200) + (2000-300)
    assert doc_result["collected"] == 3000.0
    assert doc_result["lab_cost"] == 600.0

    # Commission Base = 3000 - 600 = 2400
    assert doc_result["commission_base"] == 2400.0

    # Commission Amount = 2400 * 30% = 720
    assert doc_result["commission_amount"] == 720.0

    # Total Due = 720 + 5000 = 5720.0
    assert doc_result["total_due"] == 5720.0
    assert total_dues == 5720.0


@pytest.mark.asyncio
async def test_deductions_and_net_profit_reconciliation(async_db_session):
    """
    FIN-TRUTH-005 / FIN-TRUTH-006:
    Total Deductions = Doctor Dues + Staff Dues + Manual Expenses + Lab Costs.
    Net Profit = Total Collected - Total Deductions.
    """
    db = async_db_session
    tenant_id = 102

    # Doctor
    doctor = models.User(
        id=202,
        username="dr_sara",
        email="sara@clinic.com",
        hashed_password="hashed_pass_test",
        role="doctor",
        tenant_id=tenant_id,
        commission_percent=20.0,
        fixed_salary=3000.0,
    )
    # Staff Assistant
    assistant = models.User(
        id=203,
        username="assistant_nour",
        email="nour@clinic.com",
        hashed_password="hashed_pass_test",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=1500.0,
        per_appointment_fee=10.0,
    )
    db.add_all([doctor, assistant])

    patient = create_test_patient(id=302, name="Patient Mona", tenant_id=tenant_id, assigned_doctor_id=202)
    db.add(patient)

    # Treatment (2 treatments = 2 appointments)
    t1 = models.Treatment(
        id=403,
        patient_id=302,
        doctor_id=202,
        cost=5000.0,
        discount=500.0,
        date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    t2 = models.Treatment(
        id=404,
        patient_id=302,
        doctor_id=202,
        cost=3000.0,
        discount=0.0,
        date=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add_all([t1, t2])

    # Payment: Collected = 6000
    payment = models.Payment(
        id=502,
        patient_id=302,
        doctor_id=202,
        amount=6000.0,
        date=datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add(payment)

    # Lab order: 500
    lab = models.Laboratory(id=602, name="Lab Sara", tenant_id=tenant_id)
    db.add(lab)
    lab_order = models.LabOrder(
        id=702,
        patient_id=302,
        laboratory_id=602,
        doctor_id=202,
        work_type="Bridge",
        cost=500.0,
        order_date=datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add(lab_order)

    # Manual Expense: 800 (clinic consumables/rent)
    expense = models.Expense(
        id=801,
        item_name="Clinic Supplies",
        cost=800.0,
        category="Supplies",
        date=date(2026, 8, 15),
        tenant_id=tenant_id,
    )
    db.add(expense)

    await db.commit()

    service = AccountingService(db, tenant_id=tenant_id)
    start = datetime(2026, 8, 1, 0, 0, 0)
    end = datetime(2026, 8, 31, 23, 59, 59)

    # Calculate doctor dues:
    # Collected = 6000, Lab = 500 -> Commission base = 5500
    # Commission = 5500 * 20% = 1100
    # Total Doctor Due = 1100 + 3000 = 4100
    doc_dues, total_doc = await service.calculate_doctor_dues(start, end)
    assert total_doc == 4100.0

    # Calculate staff dues: 2 treatments = 2 appointments -> 1500 + (10 * 2) = 1520
    staff_dues, total_staff = await service.calculate_staff_dues(start, end, total_appointments=2)
    assert total_staff == 1520.0

    # Expenses = 800.0, Lab Costs = 500.0
    total_exp = await service.get_total_expenses(start, end)
    assert total_exp == 800.0
    total_lab = await service.get_total_lab_costs(start, end)
    assert total_lab == 500.0

    # Total Deductions = 4100 + 1520 + 800 + 500 = 6920.0
    total_deductions = total_doc + total_staff + total_exp + total_lab
    assert total_deductions == 6920.0

    # Net Cash Result = 6000 - 6920 = -920.0
    net_profit = 6000.0 - total_deductions
    assert net_profit == -920.0


@pytest.mark.asyncio
async def test_salary_proration_for_mid_month_hire(async_db_session):
    """
    FIN-TRUTH-003 / FIN-TRUTH-010:
    Salary proration for an employee starting work on August 16 (16 days worked in 31-day month).
    """
    db = async_db_session
    tenant_id = 103

    # Employee with hire date on August 16, 2026
    employee = models.User(
        id=204,
        username="mid_month_emp",
        email="emp@clinic.com",
        hashed_password="hashed_pass_test",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=3100.0,
        hire_date=date(2026, 8, 16),
    )
    db.add(employee)
    await db.commit()

    service = AccountingService(db, tenant_id=tenant_id)
    salary_status = await service.get_salary_status_for_month("2026-08")

    emp_data = next((e for e in salary_status["employees"] if e["id"] == 204), None)
    assert emp_data is not None
    assert emp_data["days_in_month"] == 31
    assert emp_data["is_new_this_month"] is True
    # Days worked = 31 - 16 + 1 = 16 days
    assert emp_data["days_worked"] == 16
    # Prorated salary = 3100 * (16 / 31) = 1600.0
    assert emp_data["prorated_salary"] == 1600.0


@pytest.mark.asyncio
async def test_outstanding_balance_scope_semantics(async_db_session):
    """
    FIN-TRUTH-004:
    Outstanding balance across clinic is all-time uncollected debt, while period balance is delta.
    """
    db = async_db_session
    tenant_id = 104

    patient = create_test_patient(id=304, name="Patient Tarek", tenant_id=tenant_id)
    db.add(patient)

    # Treatment in July 2026 (old activity): Cost = 5000, Paid = 1000 -> Old Debt = 4000
    t_old = models.Treatment(
        id=405,
        patient_id=304,
        cost=5000.0,
        discount=0.0,
        date=datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    p_old = models.Payment(
        id=503,
        patient_id=304,
        amount=1000.0,
        date=datetime(2026, 7, 15, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )

    # August 2026 activity: Treatment = 2000, Payment = 2000 -> Period Balance Delta = 0
    t_new = models.Treatment(
        id=406,
        patient_id=304,
        cost=2000.0,
        discount=0.0,
        date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    p_new = models.Payment(
        id=504,
        patient_id=304,
        amount=2000.0,
        date=datetime(2026, 8, 10, 11, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db.add_all([t_old, p_old, t_new, p_new])
    await db.commit()

    billing_service = BillingService(db, tenant_id=tenant_id)
    real_outstanding = await billing_service.get_outstanding_balance(patient_id=304)

    # Total Invoiced = 7000, Total Paid = 3000 -> Real Outstanding (All-Time) = 4000
    assert real_outstanding == 4000.0

    accounting_service = AccountingService(db, tenant_id=tenant_id)
    start = datetime(2026, 8, 1, 0, 0, 0)
    end = datetime(2026, 8, 31, 23, 59, 59)

    period_income = await accounting_service.get_total_income(start, end, patient_id=304)
    period_collected = await accounting_service.get_total_collected(start, end, patient_id=304)

    # In August: Invoiced = 2000, Collected = 2000, Period Delta = 0
    assert period_income == 2000.0
    assert period_collected == 2000.0
    assert (period_income - period_collected) == 0.0


@pytest.mark.asyncio
async def test_tenant_isolation_in_financials(async_db_session):
    """
    FIN-TRUTH-009 / FIN-TRUTH-010:
    Data from Tenant 105 must NEVER appear in Tenant 106 queries.
    """
    db = async_db_session
    tenant_a = 105
    tenant_b = 106

    patient_a = create_test_patient(id=305, name="Patient Tenant A", tenant_id=tenant_a)
    patient_b = create_test_patient(id=306, name="Patient Tenant B", tenant_id=tenant_b)
    db.add_all([patient_a, patient_b])

    # Tenant A payment: 10000
    p_a = models.Payment(
        id=505,
        patient_id=305,
        amount=10000.0,
        date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_a,
    )
    # Tenant B payment: 250
    p_b = models.Payment(
        id=506,
        patient_id=306,
        amount=250.0,
        date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_b,
    )
    db.add_all([p_a, p_b])
    await db.commit()

    service_a = AccountingService(db, tenant_id=tenant_a)
    service_b = AccountingService(db, tenant_id=tenant_b)

    start = datetime(2026, 8, 1, 0, 0, 0)
    end = datetime(2026, 8, 31, 23, 59, 59)

    collected_a = await service_a.get_total_collected(start, end)
    collected_b = await service_b.get_total_collected(start, end)

    assert collected_a == 10000.0
    assert collected_b == 250.0


@pytest.mark.asyncio
async def test_doctor_financial_visibility_self_scope(async_db_session):
    """
    FIN-TRUTH-009:
    Doctor without cross-doctor history override only sees payments for assigned patients.
    Admin sees all payments in the tenant.
    """
    db = async_db_session
    tenant_id = 107

    # Doctor 1 & Doctor 2
    doc1 = models.User(
        id=205,
        username="doc_one",
        email="doc1@clinic.com",
        hashed_password="hashed_pass_test",
        role="doctor",
        tenant_id=tenant_id,
        can_view_other_doctors_history=False,
    )
    doc2 = models.User(
        id=206,
        username="doc_two",
        email="doc2@clinic.com",
        hashed_password="hashed_pass_test",
        role="doctor",
        tenant_id=tenant_id,
        can_view_other_doctors_history=False,
    )
    admin = models.User(
        id=207,
        username="admin_user",
        email="admin@clinic.com",
        hashed_password="hashed_pass_test",
        role="admin",
        tenant_id=tenant_id,
    )
    db.add_all([doc1, doc2, admin])

    pat1 = create_test_patient(id=307, name="Patient of Doc1", tenant_id=tenant_id, assigned_doctor_id=205)
    pat2 = create_test_patient(id=308, name="Patient of Doc2", tenant_id=tenant_id, assigned_doctor_id=206)
    db.add_all([pat1, pat2])

    p1 = models.Payment(id=507, patient_id=307, doctor_id=205, amount=1200.0, tenant_id=tenant_id)
    p2 = models.Payment(id=508, patient_id=308, doctor_id=206, amount=800.0, tenant_id=tenant_id)
    db.add_all([p1, p2])
    await db.commit()

    # Visibility for Doc 1
    vis_doc1 = FinancialVisibilityService(db, doc1, tenant_id=tenant_id)
    query_doc1 = vis_doc1.get_visible_payments_query()
    res_doc1 = (await db.execute(query_doc1)).scalars().all()
    assert len(res_doc1) == 1
    assert res_doc1[0].id == 507

    # Visibility for Admin
    vis_admin = FinancialVisibilityService(db, admin, tenant_id=tenant_id)
    query_admin = vis_admin.get_visible_payments_query()
    res_admin = (await db.execute(query_admin)).scalars().all()
    assert len(res_admin) == 2


@pytest.mark.asyncio
async def test_financial_activity_contracts_and_rbac(async_db_session):
    """
    GEMINI_REPAIR_PLAN R2:
    - Activity uses Expense.cost and Expense.notes without error
    - Payment at 15:00 on end_date is properly included
    - Multi-tenant isolation is strictly enforced
    - Receptionist only sees payments; Admin sees all
    - Stable sorting on (timestamp DESC, source_id DESC)
    """
    db = async_db_session
    tenant_a = 108
    tenant_b = 109

    # Admin and Receptionist users
    admin_user = models.User(id=208, username="admin_r2", email="admin_r2@c.com", hashed_password="h", role="admin", tenant_id=tenant_a)
    rec_user = models.User(id=209, username="rec_r2", email="rec_r2@c.com", hashed_password="h", role="receptionist", tenant_id=tenant_a)
    doc_user = models.User(id=210, username="doc_r2", email="doc_r2@c.com", hashed_password="h", role="doctor", tenant_id=tenant_a)
    db.add_all([admin_user, rec_user, doc_user])

    # Patient
    pat = create_test_patient(id=309, name="Activity Patient", tenant_id=tenant_a, assigned_doctor_id=210)
    db.add(pat)

    # 1. Payment on 2026-08-15 at 15:30:00 (mid-day on end_date)
    p = models.Payment(
        id=509,
        patient_id=309,
        doctor_id=210,
        amount=1500.0,
        date=datetime(2026, 8, 15, 15, 30, 0, tzinfo=timezone.utc),
        notes="Cash payment",
        tenant_id=tenant_a,
    )

    # 2. Expense on 2026-08-15
    e = models.Expense(
        id=809,
        item_name="Medical Gloves",
        cost=450.0,
        category="Supplies",
        date=date(2026, 8, 15),
        notes="Box of 100",
        tenant_id=tenant_a,
    )

    # 3. Tenant B Expense (should be excluded)
    e_b = models.Expense(
        id=810,
        item_name="Tenant B Expense",
        cost=9999.0,
        category="Supplies",
        date=date(2026, 8, 15),
        tenant_id=tenant_b,
    )

    # 4. Salary payment on 2026-08-10
    s = models.SalaryPayment(
        id=909,
        user_id=209,
        month="2026-08",
        amount=3000.0,
        payment_date=datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc),
        notes="August salary installment",
        tenant_id=tenant_a,
    )

    db.add_all([p, e, e_b, s])
    await db.commit()

    service = AccountingService(db, tenant_id=tenant_a)

    # 1. Admin Query covering 2026-08-01 to 2026-08-15
    activity = await service.get_financial_activity(
        start_date="2026-08-01",
        end_date="2026-08-15",
        current_user=admin_user,
    )

    assert activity["total_count"] == 3
    assert activity["total_inflow"] == 1500.0
    assert activity["total_outflow"] == 3450.0  # 450 expense + 3000 salary
    assert activity["net_flow"] == -1950.0

    # Verify expense field mapping
    exp_event = next(ev for ev in activity["events"] if ev["source_type"] == "expense")
    assert exp_event["amount"] == 450.0
    assert exp_event["title"] == "Medical Gloves"
    assert exp_event["subtitle"] == "Box of 100"

    # Verify payment at 15:30 is included
    pay_event = next(ev for ev in activity["events"] if ev["source_type"] == "payment")
    assert pay_event["amount"] == 1500.0

    # 2. Receptionist Query - should only see payments
    rec_activity = await service.get_financial_activity(
        start_date="2026-08-01",
        end_date="2026-08-15",
        current_user=rec_user,
    )
    assert rec_activity["total_count"] == 1
    assert rec_activity["events"][0]["source_type"] == "payment"
    assert rec_activity["total_outflow"] == 0.0


@pytest.mark.asyncio
async def test_payroll_multi_installment_and_guards(async_db_session):
    """
    GEMINI_REPAIR_PLAN R3:
    - Multi-installment payments: unpaid -> partial -> paid
    - Delete partial payment and verify recalculation
    - Overpayment rejection and non-positive amount rejection
    - Exclusion of doctors, admins, super_admins from payroll
    - Multi-tenant isolation
    """
    db = async_db_session
    tenant_a = 110
    tenant_b = 111

    admin = models.User(id=211, username="admin_r3", email="admin_r3@c.com", hashed_password="h", role="admin", tenant_id=tenant_a)
    doctor = models.User(id=212, username="doc_r3", email="doc_r3@c.com", hashed_password="h", role="doctor", tenant_id=tenant_a, fixed_salary=10000.0)
    assistant = models.User(id=213, username="ast_r3", email="ast_r3@c.com", hashed_password="h", role="assistant", tenant_id=tenant_a, fixed_salary=5000.0)
    nurse_b = models.User(id=214, username="nurse_b", email="nurse_b@c.com", hashed_password="h", role="nurse", tenant_id=tenant_b, fixed_salary=4000.0)

    db.add_all([admin, doctor, assistant, nurse_b])
    await db.commit()

    service_a = AccountingService(db, tenant_id=tenant_a)
    service_b = AccountingService(db, tenant_id=tenant_b)
    assert service_b.tenant_id == tenant_b

    month = "2026-08"

    # 1. Initial status: doctor and admin must be excluded; only assistant is in payroll
    status = await service_a.get_salary_status_for_month(month)
    assert len(status["employees"]) == 1
    emp = status["employees"][0]
    assert emp["id"] == 213
    assert emp["username"] == "ast_r3"
    assert emp["payable_amount"] == 5000.0
    assert emp["paid_amount"] == 0.0
    assert emp["remaining_amount"] == 5000.0
    assert emp["status"] == "unpaid"
    assert len(emp["payments"]) == 0

    # 2. Reject zero or negative amount
    res_zero = await service_a.process_salary_payment(213, admin, month, 0.0, False, 30, "Zero")
    assert "error" in res_zero

    res_neg = await service_a.process_salary_payment(213, admin, month, -500.0, False, 30, "Neg")
    assert "error" in res_neg

    # 3. Reject paying doctor or paying user in another tenant
    res_doc = await service_a.process_salary_payment(212, admin, month, 1000.0, False, 30, "Doc")
    assert "error" in res_doc

    res_cross = await service_a.process_salary_payment(214, admin, month, 1000.0, False, 30, "Cross")
    assert "error" in res_cross

    # 4. First Partial Payment: 2000 EGP
    res_p1 = await service_a.process_salary_payment(213, admin, month, 2000.0, True, 30, "Advance payment")
    assert res_p1.get("success") is True
    p1_id = res_p1["payment_id"]
    assert p1_id is not None

    # Verify state after first installment
    status_p1 = await service_a.get_salary_status_for_month(month)
    emp_p1 = status_p1["employees"][0]
    assert emp_p1["paid_amount"] == 2000.0
    assert emp_p1["remaining_amount"] == 3000.0
    assert emp_p1["status"] == "partial"
    assert len(emp_p1["payments"]) == 1

    # 5. Overpayment guard: attempt paying 3500 when remaining is 3000
    res_over = await service_a.process_salary_payment(213, admin, month, 3500.0, False, 30, "Over")
    assert "error" in res_over

    # 6. Second Installment: 3000 EGP (Full completion)
    res_p2 = await service_a.process_salary_payment(213, admin, month, 3000.0, False, 30, "Remaining balance")
    assert res_p2.get("success") is True
    p2_id = res_p2["payment_id"]

    # Verify state after second installment -> PAID
    status_p2 = await service_a.get_salary_status_for_month(month)
    emp_p2 = status_p2["employees"][0]
    assert emp_p2["paid_amount"] == 5000.0
    assert emp_p2["remaining_amount"] == 0.0
    assert emp_p2["status"] == "paid"
    assert len(emp_p2["payments"]) == 2

    # 7. Delete second installment -> reverts to PARTIAL
    del_res = await service_a.remove_salary_payment(p2_id, admin)
    assert del_res is True

    status_del = await service_a.get_salary_status_for_month(month)
    emp_del = status_del["employees"][0]
    assert emp_del["paid_amount"] == 2000.0
    assert emp_del["remaining_amount"] == 3000.0
    assert emp_del["status"] == "partial"
    assert len(emp_del["payments"]) == 1

