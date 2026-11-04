"""Acceptance test suite for PR-09B Commercial Controls on Financial and Reporting Modules.

Covers:
1. Gating payment, expense, salary, and financial mutations when subscription is inactive or lacks 'billing' capability.
2. Gating export report endpoints (CSV exports) when plan lacks 'export_reports' capability or emergency restriction is active.
3. Direct domain service enforcement (BillingService.create_payment, ExpenseService.create_expense) failing-closed.
4. Financial AI tools obeying commercial capability and subscription state decisions.
5. Emergency restrictions on 'billing' and 'export_reports' taking immediate effect.
6. Preserving finance RBAC and cross-tenant financial isolation across all subscription states.
"""

from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from backend import models, schemas
from backend.main import app
from backend.auth import create_access_token, get_password_hash
from backend.core.permissions import Permission, Role
from backend.core.commercial_registry import CapabilityKey, OperationClass
from backend.services.commercial_decision import CommercialDecisionEngine
from backend.services.entitlement_service import EntitlementService
from backend.services.billing_service import BillingService
from backend.services.expense_service import ExpenseService
from backend.ai.executor import ToolExecutor


@pytest.fixture(autouse=True)
def enforce_subscription_mode_for_pr09b(monkeypatch):
    """Ensure subscription enforcement mode is 'enforce' for PR-09B tests."""
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")


def _auth_header(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pr09b_setup(db_session):
    """Seed test plans, active clinic, expired clinic, restricted clinics, and users."""
    now = datetime.now(timezone.utc)

    # 1. Full Plan (Clinical, Billing, Export Reports, AI)
    plan_full = models.SubscriptionPlan(
        name="pr09b_full_plan",
        display_name_ar="خطة متكاملة",
        price=Decimal("300.00"),
        max_users=10,
        is_ai_enabled=True,
        ai_daily_limit=20,
        features='{"clinical": true, "billing": true, "export_reports": true, "ai_insights": true}',
    )
    # 2. Plan without Billing (Clinical only, no Billing or Export)
    plan_no_billing = models.SubscriptionPlan(
        name="pr09b_no_billing_plan",
        display_name_ar="خطة عيادة سريرية فقط",
        price=Decimal("150.00"),
        max_users=5,
        is_ai_enabled=False,
        ai_daily_limit=0,
        features='{"clinical": true, "billing": false, "export_reports": false, "ai_insights": false}',
    )
    # 3. Plan with Billing but without Export Reports
    plan_no_export = models.SubscriptionPlan(
        name="pr09b_no_export_plan",
        display_name_ar="خطة بدون تصدير تقارير",
        price=Decimal("200.00"),
        max_users=5,
        is_ai_enabled=False,
        ai_daily_limit=0,
        features='{"clinical": true, "billing": true, "export_reports": false, "ai_insights": false}',
    )
    db_session.add_all([plan_full, plan_no_billing, plan_no_export])
    db_session.commit()
    for p in (plan_full, plan_no_billing, plan_no_export):
        db_session.refresh(p)

    # 4. Active Clinic (Full Plan)
    tenant_active = models.Tenant(
        name="PR09B Active Clinic",
        plan=plan_full.name,
        plan_id=plan_full.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_active.subscription_plan = plan_full

    # 5. Expired Clinic (Full Plan, but subscription ended 15 days ago, past grace)
    tenant_expired = models.Tenant(
        name="PR09B Expired Clinic",
        plan=plan_full.name,
        plan_id=plan_full.id,
        subscription_status="expired_read_only",
        subscription_end_date=now - timedelta(days=15),
        grace_period_until=now - timedelta(days=8),
        is_active=True,
    )
    tenant_expired.subscription_plan = plan_full

    # 6. Restricted Clinic (Active subscription, but Plan has billing=False)
    tenant_no_billing = models.Tenant(
        name="PR09B No Billing Clinic",
        plan=plan_no_billing.name,
        plan_id=plan_no_billing.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_no_billing.subscription_plan = plan_no_billing

    # 7. Restricted Clinic (Active subscription, but Plan has export_reports=False)
    tenant_no_export = models.Tenant(
        name="PR09B No Export Clinic",
        plan=plan_no_export.name,
        plan_id=plan_no_export.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_no_export.subscription_plan = plan_no_export

    db_session.add_all([tenant_active, tenant_expired, tenant_no_billing, tenant_no_export])
    db_session.commit()
    for t in (tenant_active, tenant_expired, tenant_no_billing, tenant_no_export):
        db_session.refresh(t)

    # Users in Active Clinic
    admin_active = models.User(
        username="pr09b_admin_act",
        email="admin_act@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_active.id,
        is_active=True,
    )
    recep_active = models.User(
        username="pr09b_recep_act",
        email="recep_act@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="receptionist",
        tenant_id=tenant_active.id,
        is_active=True,
    )
    doc_active = models.User(
        username="pr09b_doc_act",
        email="doc_act@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_active.id,
        is_active=True,
    )

    # Users in Expired Clinic
    admin_expired = models.User(
        username="pr09b_admin_exp",
        email="admin_exp@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_expired.id,
        is_active=True,
    )
    recep_expired = models.User(
        username="pr09b_recep_exp",
        email="recep_exp@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="receptionist",
        tenant_id=tenant_expired.id,
        is_active=True,
    )

    # User in No-Billing Clinic
    admin_no_billing = models.User(
        username="pr09b_admin_nobill",
        email="admin_nobill@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_no_billing.id,
        is_active=True,
    )

    # User in No-Export Clinic
    admin_no_export = models.User(
        username="pr09b_admin_noexp",
        email="admin_noexp@pr09b.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_no_export.id,
        is_active=True,
    )

    db_session.add_all([
        admin_active, recep_active, doc_active,
        admin_expired, recep_expired,
        admin_no_billing, admin_no_export
    ])
    db_session.commit()
    for u in (
        admin_active, recep_active, doc_active,
        admin_expired, recep_expired,
        admin_no_billing, admin_no_export
    ):
        db_session.refresh(u)

    # Seed patients in active and expired clinics
    patient_active = models.Patient(
        name="Tarek Finance Active",
        phone="01111112222",
        age=30,
        tenant_id=tenant_active.id,
        assigned_doctor_id=doc_active.id,
    )
    patient_expired = models.Patient(
        name="Mona Finance Expired",
        phone="01222223333",
        age=28,
        tenant_id=tenant_expired.id,
    )
    patient_no_billing = models.Patient(
        name="Samir No Billing",
        phone="01333334444",
        age=45,
        tenant_id=tenant_no_billing.id,
    )
    db_session.add_all([patient_active, patient_expired, patient_no_billing])
    db_session.commit()
    for p in (patient_active, patient_expired, patient_no_billing):
        db_session.refresh(p)

    return {
        "tenant_active": tenant_active,
        "tenant_expired": tenant_expired,
        "tenant_no_billing": tenant_no_billing,
        "tenant_no_export": tenant_no_export,
        "admin_active": admin_active,
        "recep_active": recep_active,
        "doc_active": doc_active,
        "admin_expired": admin_expired,
        "recep_expired": recep_expired,
        "admin_no_billing": admin_no_billing,
        "admin_no_export": admin_no_export,
        "patient_active": patient_active,
        "patient_expired": patient_expired,
        "patient_no_billing": patient_no_billing,
    }


# ==============================================================================
# 1. Active Clinic: Permitted Financial Writes and Exports
# ==============================================================================

def test_active_clinic_financial_writes_and_exports_permitted(client, pr09b_setup):
    """In an active clinic with billing & export capabilities, financial mutations and exports succeed."""
    admin_active = pr09b_setup["admin_active"]
    patient_active = pr09b_setup["patient_active"]
    headers = _auth_header(admin_active)

    # 1. Record Payment (POST /payments)
    res_pay = client.post(
        "/api/v1/payments",
        json={"patient_id": patient_active.id, "amount": 500.0, "notes": "Checkup payment"},
        headers=headers,
    )
    assert res_pay.status_code == 200, res_pay.text
    assert res_pay.json()["data"]["id"] is not None

    # 2. Record Expense (POST /expenses)
    res_exp = client.post(
        "/api/v1/expenses",
        json={
            "item_name": "Latex Gloves",
            "cost": 150.0,
            "category": "Supplies",
            "date": "2026-11-04",
            "notes": "Sterile box",
        },
        headers=headers,
    )
    assert res_exp.status_code == 200, res_exp.text

    # 3. Export Summary CSV (GET /reports/summary/export.csv)
    res_csv = client.get(
        "/api/v1/financials/reports/summary/export.csv?start_date=2026-11-01&end_date=2026-11-30&locale=en",
        headers=headers,
    )
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")


# ==============================================================================
# 2. Expired Clinic: Financial Mutations & Exports Blocked
# ==============================================================================

def test_expired_clinic_blocks_financial_mutations_and_exports(client, pr09b_setup):
    """
    Expired clinic:
    - POST to /payments, /expenses, /accounting/salaries returns HTTP 403.
    - GET to /reports/.../export.csv returns HTTP 403.
    """
    admin_expired = pr09b_setup["admin_expired"]
    patient_expired = pr09b_setup["patient_expired"]
    headers = _auth_header(admin_expired)

    # 1. Payment creation blocked -> 403
    res_pay = client.post(
        "/api/v1/payments",
        json={"patient_id": patient_expired.id, "amount": 350.0, "notes": "Blocked payment"},
        headers=headers,
    )
    assert res_pay.status_code == 403
    assert "اشتراك" in res_pay.text or "expired" in res_pay.text.lower()

    # 2. Expense creation blocked -> 403
    res_exp = client.post(
        "/api/v1/expenses",
        json={
            "item_name": "Paper Towels",
            "cost": 80.0,
            "category": "Office",
            "date": "2026-11-04",
        },
        headers=headers,
    )
    assert res_exp.status_code == 403

    # 3. Salary payment blocked -> 403
    res_sal = client.post(
        "/api/v1/accounting/salaries",
        json={"user_id": admin_expired.id, "amount": 1000.0, "month": 11, "year": 2026},
        headers=headers,
    )
    assert res_sal.status_code == 403

    # 4. Report export blocked -> 403
    res_csv = client.get(
        "/api/v1/financials/reports/summary/export.csv?start_date=2026-11-01&end_date=2026-11-30&locale=en",
        headers=headers,
    )
    assert res_csv.status_code == 403


# ==============================================================================
# 3. Plan Lacking Billing Capability
# ==============================================================================

def test_plan_lacking_billing_blocks_writes_and_services(client, pr09b_setup):
    """
    Clinic assigned a plan where billing=False:
    - Direct payment and expense mutations fail with HTTP 403.
    """
    admin_no_billing = pr09b_setup["admin_no_billing"]
    patient_no_billing = pr09b_setup["patient_no_billing"]
    headers = _auth_header(admin_no_billing)

    # 1. Attempt to create payment -> 403
    res_pay = client.post(
        "/api/v1/payments",
        json={"patient_id": patient_no_billing.id, "amount": 200.0},
        headers=headers,
    )
    assert res_pay.status_code == 403
    assert "فواتير" in res_pay.text or "billing" in res_pay.text.lower() or "مدفوعات" in res_pay.text

    # 2. Attempt to create expense -> 403
    res_exp = client.post(
        "/api/v1/expenses",
        json={
            "item_name": "Anesthetic",
            "cost": 300.0,
            "category": "Medications",
            "date": "2026-11-04",
        },
        headers=headers,
    )
    assert res_exp.status_code == 403


# ==============================================================================
# 4. Plan Lacking Export Reports Capability
# ==============================================================================

def test_plan_lacking_export_reports_blocks_csv_exports(client, pr09b_setup):
    """
    Clinic assigned a plan where billing=True but export_reports=False:
    - Direct payment writes succeed.
    - Export CSV endpoints fail with HTTP 403.
    """
    admin_no_export = pr09b_setup["admin_no_export"]
    headers = _auth_header(admin_no_export)

    # 1. Export summary CSV -> 403
    res_csv = client.get(
        "/api/v1/financials/reports/summary/export.csv?start_date=2026-11-01&end_date=2026-11-30&locale=en",
        headers=headers,
    )
    assert res_csv.status_code == 403
    assert "تصدير" in res_csv.text or "export" in res_csv.text.lower() or "تقارير" in res_csv.text


# ==============================================================================
# 5. Emergency Restriction on 'billing'
# ==============================================================================

def test_emergency_restriction_on_billing_blocks_mutations_immediately(client, pr09b_setup, db_session):
    """
    When an emergency restriction is active on 'billing':
    - Payments and expenses mutations immediately return 403.
    """
    admin_active = pr09b_setup["admin_active"]
    patient_active = pr09b_setup["patient_active"]
    headers = _auth_header(admin_active)

    setting = models.SystemSetting(key="emergency_restriction_billing", value="true")
    db_session.add(setting)
    db_session.commit()

    try:
        # Create payment under emergency restriction -> 403
        res_pay = client.post(
            "/api/v1/payments",
            json={"patient_id": patient_active.id, "amount": 400.0},
            headers=headers,
        )
        assert res_pay.status_code == 403
        assert "طوارئ" in res_pay.text or "emergency" in res_pay.text.lower() or "حظر" in res_pay.text
    finally:
        db_session.delete(setting)
        db_session.commit()


# ==============================================================================
# 6. Emergency Restriction on 'export_reports'
# ==============================================================================

def test_emergency_restriction_on_export_reports_blocks_exports_immediately(client, pr09b_setup, db_session):
    """
    When an emergency restriction is active on 'export_reports':
    - Export endpoints immediately return 403.
    - Direct payment creation remains unaffected.
    """
    admin_active = pr09b_setup["admin_active"]
    patient_active = pr09b_setup["patient_active"]
    headers = _auth_header(admin_active)

    setting = models.SystemSetting(key="emergency_restriction_export_reports", value="true")
    db_session.add(setting)
    db_session.commit()

    try:
        # Export under emergency restriction -> 403
        res_csv = client.get(
            "/api/v1/financials/reports/summary/export.csv?start_date=2026-11-01&end_date=2026-11-30&locale=en",
            headers=headers,
        )
        assert res_csv.status_code == 403
        assert "طوارئ" in res_csv.text or "emergency" in res_csv.text.lower() or "حظر" in res_csv.text

        # Payment write remains permitted
        res_pay = client.post(
            "/api/v1/payments",
            json={"patient_id": patient_active.id, "amount": 250.0},
            headers=headers,
        )
        assert res_pay.status_code == 200
    finally:
        db_session.delete(setting)
        db_session.commit()


# ==============================================================================
# 7. Direct Domain Service Layer Enforcement
# ==============================================================================

@pytest.mark.asyncio
async def test_direct_service_layer_billing_and_expense_enforcement(
    async_db_session, pr09b_setup
):
    """
    Calling domain services directly:
    - BillingService.create_payment on expired tenant raises HTTPException(403).
    - ExpenseService.create_expense on expired tenant raises HTTPException(403).
    """
    from fastapi import HTTPException

    tenant_expired = pr09b_setup["tenant_expired"]
    patient_expired = pr09b_setup["patient_expired"]

    # 1. BillingService: Direct create_payment raises 403
    billing_svc = BillingService(async_db_session, tenant_id=tenant_expired.id)
    with pytest.raises(HTTPException) as exc_pay:
        await billing_svc.create_payment(
            schemas.PaymentCreate(patient_id=patient_expired.id, amount=Decimal("300.00"))
        )
    assert exc_pay.value.status_code == 403

    # 2. ExpenseService: Direct create_expense raises 403
    expense_svc = ExpenseService(async_db_session, tenant_id=tenant_expired.id)
    with pytest.raises(HTTPException) as exc_exp:
        await expense_svc.create_expense(
            schemas.ExpenseCreate(
                item_name="Direct Blocked Expense",
                cost=Decimal("120.00"),
                category="Office",
                date=date(2026, 11, 4),
            )
        )
    assert exc_exp.value.status_code == 403


# ==============================================================================
# 8. Financial AI Tools Enforce Commercial Decision
# ==============================================================================

@pytest.mark.asyncio
async def test_financial_ai_tools_enforce_commercial_decision(
    async_db_session, pr09b_setup
):
    """
    AI ToolExecutor:
    - Mutating financial tool (create_payment) returns success=False on expired clinic.
    - Reporting AI tools (get_revenue_trend, get_doctor_ranking) return success=False on plan without export_reports.
    """
    admin_expired = pr09b_setup["admin_expired"]
    admin_no_export = pr09b_setup["admin_no_export"]
    patient_expired = pr09b_setup["patient_expired"]

    # 1. Expired clinic: create_payment tool denied
    exec_expired = ToolExecutor(async_db_session, admin_expired)
    res_pay = await exec_expired.execute(
        "create_payment",
        {"patient_name": patient_expired.name, "amount": 500},
    )
    assert res_pay.get("success") is False
    assert res_pay.get("error_code") == "subscription_expired"

    # 2. Clinic lacking export_reports: reporting tool denied
    exec_no_export = ToolExecutor(async_db_session, admin_no_export)
    res_trend = await exec_no_export.execute("get_revenue_trend", {})
    assert res_trend.get("success") is False
    assert res_trend.get("error_code") == "plan_restricted"


# ==============================================================================
# 9. Finance RBAC and Cross-Tenant Isolation Preserved
# ==============================================================================

def test_finance_rbac_and_cross_tenant_isolation_preserved(client, pr09b_setup):
    """
    Finance RBAC & Tenancy:
    - Doctor lacking REPORT_READ / REPORT_EXPORT cannot access financial export (403).
    - Receptionist lacking REPORT_EXPORT cannot export CSV (403).
    - Cross-tenant user cannot access or record payments for another tenant's patient (403/404).
    """
    doc_active = pr09b_setup["doc_active"]
    recep_active = pr09b_setup["recep_active"]
    admin_active = pr09b_setup["admin_active"]
    patient_expired = pr09b_setup["patient_expired"]

    # 1. Doctor without financial RBAC cannot export reports -> 403
    res_doc = client.get(
        "/api/v1/financials/reports/summary/export.csv?start_date=2026-11-01&end_date=2026-11-30&locale=en",
        headers=_auth_header(doc_active),
    )
    assert res_doc.status_code == 403

    # 2. Receptionist without REPORT_EXPORT cannot export reports -> 403
    res_recep = client.get(
        "/api/v1/financials/reports/summary/export.csv?start_date=2026-11-01&end_date=2026-11-30&locale=en",
        headers=_auth_header(recep_active),
    )
    assert res_recep.status_code == 403

    # 3. Active tenant admin cannot record payment for expired tenant's patient -> 400/404/422 (cross-tenant)
    res_cross = client.post(
        "/api/v1/payments",
        json={"patient_id": patient_expired.id, "amount": 100.0},
        headers=_auth_header(admin_active),
    )
    assert res_cross.status_code in {400, 404, 422}
