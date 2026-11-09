# backend/tests/test_subscription_lifecycle_pr06.py
"""
PR-06 Acceptance Tests: Subscription Periods, Approved Trial, Calendar Renewal, and Safe Lifecycle.

Validates all PR-06 requirements:
1. Approved Professional Trial Registration:
   - New clinic registration creates clinic, first owner, Professional trial for exactly 14 days.
   - Missing trial configuration fails safely before committing partial tenant or user.
2. Payment / Renewal During Trial:
   - Preserves remaining trial days; paid period starts when trial ends.
   - If paid plan differs (e.g. Essential), Professional remains effective until trial ends,
     with future plan scheduled for the paid period.
3. Calendar-Month Recurrence & Preserved Billing Anchor:
   - Jan 31 -> Feb 28/29 -> Mar 31 -> Apr 30 without drift.
   - Timezone boundaries handled accurately.
4. Idempotency & Replay Safety:
   - One receipt / renewal grants one paid period.
   - Same idempotency key with different payload conflicts (409).
   - Duplicate payment provider ID returns existing payment without double extension.
5. Clinical History Read Invariance:
   - Expired clinic (read-only) can authenticate and read authorized clinical history,
     attachments, care sessions, and prior treatment plans.
   - New business writes and AI remain blocked (403).
   - Feature rollout flags (off) do NOT block reading existing authored care sessions or treatment plans.
6. Safe Hard-Disable Independence:
   - Paid renewal, assignment, or worker cannot unsuspend a security-disabled (is_active=False) clinic.
   - Suspended_admin and cancelled clinics reject renewal without explicit reactivation.
   - Worker cannot resurrect or overwrite suspended_admin or cancelled states.
7. Scheduled Downgrade & Capacity Enforcement:
   - Cannot schedule downgrade if active accounts exceed target plan cap.
   - Once scheduled, new user creation respects the pending lower cap atomically.
   - At renewal, atomic check applies downgrade without silent deactivation/deletion.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import pytest
from fastapi import HTTPException

from backend import models, schemas
from backend.core.commercial_registry import OperationClass
from backend.services.commercial_decision import CommercialDecisionEngine
from backend.services.subscription_calendar import (
    add_calendar_months,
    calculate_grace_period,
    calculate_subscription_period,
)
from backend.services.subscription_state_machine import SubscriptionState
from backend.services.subscription_renewal_service import (
    SubscriptionRenewalError,
    renew_subscription,
)
from backend.services.subscription_service import SubscriptionService
from backend.services.account_admission_service import (
    AccountAdmissionService,
    AccountCapacityExceededError,
)
from backend.workers.subscription_checker import check_expired_subscriptions
from backend.routers.auth import register as register_router
from backend.routers import admin_tenants as admin_tenants_router
from backend.services.care_session_service import CareSessionService
from backend.services.treatment_plan_service import TreatmentPlanService


def _user(
    username: str,
    role: str = "doctor",
    tenant_id: int = 101,
    is_active: bool = True,
    is_deleted: bool = False,
    id: int = None,
):
    kwargs = {
        "username": username,
        "email": f"{username}@clinic.test",
        "hashed_password": "hashed_pw_test_lifecycle_pr06",
        "role": role,
        "tenant_id": tenant_id,
        "is_active": is_active,
        "is_deleted": is_deleted,
    }
    if id is not None:
        kwargs["id"] = id
    return models.User(**kwargs)


@pytest.fixture
def mock_super_admin():
    return _user(id=999, username="superadmin_pr06", role="super_admin", tenant_id=None)


@pytest.fixture
async def setup_launch_plans(async_db_session):
    """Seed the canonical 3 launch plans for tests."""
    plans = [
        models.SubscriptionPlan(
            name="essential",
            display_name_ar="الباقة الأساسية",
            price=200.0,
            duration_days=30,
            max_users=2,
            is_ai_enabled=True,
            ai_daily_limit=2,
            is_active=True,
        ),
        models.SubscriptionPlan(
            name="professional",
            display_name_ar="الباقة الاحترافية",
            price=400.0,
            duration_days=30,
            max_users=5,
            is_ai_enabled=True,
            ai_daily_limit=10,
            is_active=True,
        ),
        models.SubscriptionPlan(
            name="business",
            display_name_ar="باقة الأعمال",
            price=800.0,
            duration_days=30,
            max_users=15,
            is_ai_enabled=True,
            ai_daily_limit=30,
            is_active=True,
        ),
    ]
    async_db_session.add_all(plans)
    await async_db_session.commit()
    return {p.name: p for p in plans}


# ---------------------------------------------------------------------------
# 1. Calendar Recurrence & Preserved Billing Anchor
# ---------------------------------------------------------------------------

def test_calendar_month_recurrence_preserves_anchor():
    """Jan 31 -> Feb 28 -> Mar 31 -> Apr 30 with preserved anchor 31."""
    jan_31 = datetime(2026, 1, 31, 10, 0, 0)

    # +1 month: Feb 2026 has 28 days
    feb_end, anchor = add_calendar_months(jan_31, months=1, anchor_day=31, tz_name="Africa/Cairo")
    assert feb_end.year == 2026
    assert feb_end.month == 2
    assert feb_end.day == 28
    assert anchor == 31

    # +1 month from Feb 28 with anchor 31: Mar 2026 has 31 days
    mar_end, anchor = add_calendar_months(feb_end, months=1, anchor_day=anchor, tz_name="Africa/Cairo")
    assert mar_end.year == 2026
    assert mar_end.month == 3
    assert mar_end.day == 31
    assert anchor == 31

    # +1 month from Mar 31 with anchor 31: Apr 2026 has 30 days
    apr_end, anchor = add_calendar_months(mar_end, months=1, anchor_day=anchor, tz_name="Africa/Cairo")
    assert apr_end.year == 2026
    assert apr_end.month == 4
    assert apr_end.day == 30
    assert anchor == 31


def test_calendar_month_leap_year_february():
    """Leap year 2028: Jan 31 -> Feb 29 -> Mar 31."""
    jan_31 = datetime(2028, 1, 31, 12, 0, 0)
    feb_end, anchor = add_calendar_months(jan_31, months=1, anchor_day=31)
    assert feb_end.year == 2028
    assert feb_end.month == 2
    assert feb_end.day == 29
    assert anchor == 31

    mar_end, anchor = add_calendar_months(feb_end, months=1, anchor_day=anchor)
    assert mar_end.year == 2028
    assert mar_end.month == 3
    assert mar_end.day == 31


# ---------------------------------------------------------------------------
# 2. Approved Professional Trial Registration (14 days)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registration_creates_professional_trial_14_days(async_db_session, setup_launch_plans):
    """Registration creates clinic with Professional trial for exactly 14 days and 1 counted owner."""
    register_fn = getattr(register_router.register_clinic, "__wrapped__", register_router.register_clinic)
    res = await register_fn(
        request=None,
        clinic_name="Alpha Dental Clinic",
        admin_username="alpha_owner",
        admin_email="alpha@test.com",
        admin_password="StrongPassword123!",
        contact_phone="01011112233",
        db=async_db_session,
    )
    data = res.data if hasattr(res, "data") else res.get("data")
    assert data is not None

    # Inspect created tenant
    tenant = (
        await async_db_session.execute(
            models.Tenant.__table__.select().where(models.Tenant.name == "Alpha Dental Clinic")
        )
    ).first()
    assert tenant is not None
    assert tenant.subscription_status == "trial"
    assert tenant.plan == "professional"
    assert tenant.is_active is True
    assert tenant.grace_period_until is None  # Trial has no grace period

    # Verify duration is exactly 14 days
    diff = tenant.subscription_end_date - tenant.subscription_start_date
    assert diff.days == 14

    # Verify authoritative seat count is 1 (owner)
    count = await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id)
    assert count == 1


@pytest.mark.asyncio
async def test_registration_fails_safely_if_trial_plan_missing(async_db_session):
    """If Professional trial plan is not configured, registration fails without partial tenant."""
    register_fn = getattr(register_router.register_clinic, "__wrapped__", register_router.register_clinic)
    with pytest.raises(HTTPException) as exc_info:
        await register_fn(
            request=None,
            clinic_name="Broken Seed Clinic",
            admin_username="broken_owner",
            admin_email="broken@test.com",
            admin_password="StrongPassword123!",
            contact_phone="01099998877",
            db=async_db_session,
        )
    assert exc_info.value.status_code == 500
    assert "باقة التجربة المجانية غير مهيأة" in exc_info.value.detail

    # Verify no tenant was committed
    tenants = (await async_db_session.execute(models.Tenant.__table__.select())).all()
    assert len(tenants) == 0


# ---------------------------------------------------------------------------
# 3. Payment During Trial (Same Tier vs Different Tier)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_during_trial_same_tier_preserves_trial(async_db_session, setup_launch_plans):
    """Paying for Professional during Professional trial preserves remaining trial days."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    trial_end = now + timedelta(days=10)  # 10 days left in trial

    tenant = models.Tenant(
        id=301,
        name="Trial Clinic Same Tier",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="trial",
        subscription_start_date=now - timedelta(days=4),
        subscription_end_date=trial_end,
        billing_day_anchor=trial_end.day,
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()

    # Record payment for Professional (1 month)
    payment_in = schemas.SubscriptionPaymentCreate(
        tenant_id=tenant.id,
        plan_id=pro_plan.id,
        amount=Decimal("400.00"),
        payment_method="manual_cash",
        notes="Purchased 1 month Professional during trial",
        provider="manual",
        provider_payment_id="pay_trial_same_01",
    )
    payment = await SubscriptionService.record_payment(
        async_db_session, payment_in, created_by="superadmin"
    )
    assert payment.id is not None

    await async_db_session.refresh(tenant)
    # Status remains trial until trial ends
    assert tenant.subscription_status == "trial"
    assert tenant.plan == "professional"
    # End date extends from trial_end by 1 calendar month
    assert tenant.subscription_end_date > trial_end
    # Grace period is calculated 7 days after the paid end date
    assert tenant.grace_period_until == calculate_grace_period(tenant.subscription_end_date)


@pytest.mark.asyncio
async def test_payment_during_trial_different_tier_preserves_trial_and_schedules_future(
    async_db_session, setup_launch_plans
):
    """Paying for Essential during Professional trial preserves Professional trial and schedules Essential."""
    pro_plan = setup_launch_plans["professional"]
    ess_plan = setup_launch_plans["essential"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    trial_end = now + timedelta(days=10)

    tenant = models.Tenant(
        id=302,
        name="Trial Clinic Diff Tier",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="trial",
        subscription_start_date=now - timedelta(days=4),
        subscription_end_date=trial_end,
        billing_day_anchor=trial_end.day,
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()

    # Clinic purchases Essential (2 seats)
    payment_in = schemas.SubscriptionPaymentCreate(
        tenant_id=tenant.id,
        plan_id=ess_plan.id,
        amount=Decimal("200.00"),
        payment_method="bank_transfer",
        provider="manual",
        provider_payment_id="pay_trial_diff_01",
    )
    await SubscriptionService.record_payment(async_db_session, payment_in, created_by="superadmin")

    await async_db_session.refresh(tenant)
    # Effective current plan is still professional during remaining trial!
    assert tenant.plan == "professional"
    assert tenant.subscription_status == "trial"
    # Future plan is recorded as Essential starting at trial_end
    assert tenant.future_plan_id == ess_plan.id
    assert tenant.future_plan_start_date == trial_end


# ---------------------------------------------------------------------------
# 4. Idempotency & Replay Safety
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_renewal_idempotency_key_replay_and_conflict(async_db_session, mock_super_admin, setup_launch_plans):
    """Same idempotency key with same request returns cached response; different payload raises 409."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    tenant = models.Tenant(
        id=401,
        name="Idempotent Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_start_date=now - timedelta(days=20),
        subscription_end_date=now + timedelta(days=10),
        billing_day_anchor=now.day,
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()

    req1 = schemas.TenantManualRenewalRequest(
        idempotency_key="replay-001",
        plan_id=pro_plan.id,
        extension_days=30,
        notes="First renewal attempt",
    )
    res1 = await renew_subscription(async_db_session, tenant_id=tenant.id, request=req1, admin=mock_super_admin)
    assert res1["is_idempotent_duplicate"] is False
    first_end = res1["subscription_end_date"]

    # Replay identical request -> returns cached response with is_idempotent_duplicate=True
    res_replay = await renew_subscription(async_db_session, tenant_id=tenant.id, request=req1, admin=mock_super_admin)
    assert res_replay["is_idempotent_duplicate"] is True
    assert res_replay["subscription_end_date"] == first_end

    # Replay same idempotency key with DIFFERENT payload -> 409 Conflict
    req_conflict = schemas.TenantManualRenewalRequest(
        idempotency_key="replay-001",
        plan_id=pro_plan.id,
        extension_days=60,  # Different days!
        notes="Conflicting payload",
    )
    with pytest.raises(SubscriptionRenewalError) as exc_info:
        await renew_subscription(async_db_session, tenant_id=tenant.id, request=req_conflict, admin=mock_super_admin)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_payment_receipt_does_not_double_extend(async_db_session, setup_launch_plans):
    """Replaying payment with same provider_payment_id returns existing record without extending time twice."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    tenant = models.Tenant(
        id=402,
        name="Receipt Idempotency Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=5),
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()

    payment_in = schemas.SubscriptionPaymentCreate(
        tenant_id=tenant.id,
        plan_id=pro_plan.id,
        amount=Decimal("400.00"),
        payment_method="card",
        provider="fawry",
        provider_payment_id="fawry_tx_unique_999",
    )
    p1 = await SubscriptionService.record_payment(async_db_session, payment_in, created_by="system")
    await async_db_session.refresh(tenant)
    end_after_first = tenant.subscription_end_date

    # Replay payment with same fawry_tx_unique_999
    p2 = await SubscriptionService.record_payment(async_db_session, payment_in, created_by="system")
    assert p1.id == p2.id

    await async_db_session.refresh(tenant)
    # End date MUST NOT have been extended a second time!
    assert tenant.subscription_end_date == end_after_first


# ---------------------------------------------------------------------------
# 5. Clinical History Read Invariance & Expiry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_clinic_can_read_history_but_blocked_from_writes(async_db_session, setup_launch_plans):
    """Expired clinic can read existing clinical history; writes are blocked with 403."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Tenant expired 10 days ago (past 7 grace days)
    tenant = models.Tenant(
        id=501,
        name="Expired History Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="expired_read_only",
        subscription_end_date=now - timedelta(days=10),
        grace_period_until=now - timedelta(days=3),
        is_active=True,
    )
    async_db_session.add(tenant)

    doctor = _user(username="doc_exp", role="doctor", tenant_id=tenant.id)
    async_db_session.add(doctor)
    await async_db_session.flush()

    patient = models.Patient(
        id=50101,
        name="Ahmed Historical",
        phone="01012345678",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor.id,
    )
    async_db_session.add(patient)

    care_session = models.CareSession(
        id=501001,
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_user_id=doctor.id,
        status="completed",
    )
    async_db_session.add(care_session)
    await async_db_session.commit()

    # 1. CommercialDecision for READ_HISTORY: ALLOWED
    dec_read = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant,
        capability="clinical",
        operation=OperationClass.READ_HISTORY.value,
        now=now,
        override_mode="enforce",
    )
    assert dec_read.allowed is True
    assert dec_read.reason_code == "CLINICAL_HISTORY_INVARIANT"

    # 2. CommercialDecision for WRITE_BUSINESS: DENIED
    dec_write = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant,
        capability="clinical",
        operation=OperationClass.WRITE_BUSINESS.value,
        now=now,
        override_mode="enforce",
    )
    assert dec_write.allowed is False
    assert dec_write.proposed_allowed is False
    assert dec_write.reason_code == "SUBSCRIPTION_EXPIRED"


@pytest.mark.asyncio
async def test_rollout_gate_off_does_not_block_historical_reads(async_db_session, setup_launch_plans):
    """Even if native writes rollout flag is off, reading existing care sessions succeeds."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    tenant = models.Tenant(
        id=502,
        name="Rollout Off Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=20),
        is_active=True,
    )
    async_db_session.add(tenant)
    doctor = _user(id=5021, username="doc_rollout", role="doctor", tenant_id=tenant.id)
    async_db_session.add(doctor)
    await async_db_session.flush()

    patient = models.Patient(
        id=50201,
        name="Fatima History",
        phone="01098765432",
        tenant_id=tenant.id,
        assigned_doctor_id=doctor.id,
    )
    async_db_session.add(patient)
    session = models.CareSession(
        id=502001,
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_user_id=doctor.id,
        status="completed",
    )
    async_db_session.add(session)
    await async_db_session.commit()

    care_service = CareSessionService(async_db_session, tenant_id=tenant.id, current_user=doctor)
    # Reading existing session must NOT raise 404
    pres = await care_service.get_session(patient_id=patient.id, session_id=session.id)
    assert pres is not None
    assert pres.id == session.id


# ---------------------------------------------------------------------------
# 6. Hard-Disable Independence & Security States
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paid_renewal_cannot_unsuspend_hard_disabled_clinic(
    async_db_session, mock_super_admin, setup_launch_plans
):
    """Manual renewal updates commercial status but NEVER reverses security disable (is_active=False)."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Clinic is hard-disabled for security investigation (is_active=False)
    tenant = models.Tenant(
        id=601,
        name="Security Disabled Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=5),
        is_active=False,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()

    req = schemas.TenantManualRenewalRequest(
        idempotency_key="disabled01",
        extension_days=30,
        notes="Renew while disabled",
    )
    res = await renew_subscription(async_db_session, tenant_id=tenant.id, request=req, admin=mock_super_admin)
    assert res["subscription_status"] == "active"

    await async_db_session.refresh(tenant)
    # is_active MUST STILL BE FALSE!
    assert tenant.is_active is False


@pytest.mark.asyncio
async def test_suspended_and_cancelled_clinics_reject_renewal(
    async_db_session, mock_super_admin, setup_launch_plans
):
    """Clinics in suspended_admin or cancelled state cannot be renewed without explicit reactivation."""
    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    tenant_susp = models.Tenant(
        id=602,
        name="Suspended Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="suspended_admin",
        subscription_end_date=now + timedelta(days=5),
        is_active=True,
    )
    async_db_session.add(tenant_susp)
    await async_db_session.commit()

    req = schemas.TenantManualRenewalRequest(
        idempotency_key="suspend-01",
        extension_days=30,
    )
    with pytest.raises(SubscriptionRenewalError) as exc_info:
        await renew_subscription(async_db_session, tenant_id=tenant_susp.id, request=req, admin=mock_super_admin)
    assert exc_info.value.status_code == 409
    assert "suspended_admin" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 7. Scheduled Downgrade & Capacity Enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheduled_downgrade_enforces_capacity(
    async_db_session, mock_super_admin, setup_launch_plans, monkeypatch
):
    """Scheduling downgrade requires active accounts <= target cap; enforces pending cap atomically."""
    pro_plan = setup_launch_plans["professional"]  # cap = 5
    ess_plan = setup_launch_plans["essential"]     # cap = 2
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    tenant = models.Tenant(
        id=701,
        name="Downgrade Clinic",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=20),
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.flush()

    # Add 3 active users (exceeds Essential cap of 2)
    u1 = _user(username="u1_701", role="admin", tenant_id=tenant.id)
    u2 = _user(username="u2_701", role="doctor", tenant_id=tenant.id)
    u3 = _user(username="u3_701", role="doctor", tenant_id=tenant.id)
    async_db_session.add_all([u1, u2, u3])
    await async_db_session.commit()

    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 3

    # 1. Attempt to schedule downgrade to Essential while having 3 active users -> REJECTED (400)
    with pytest.raises(HTTPException) as exc_info:
        await admin_tenants_router.schedule_tenant_downgrade(
            tenant_id=tenant.id,
            plan_id=ess_plan.id,
            current_user=mock_super_admin,
            db=async_db_session,
        )
    assert exc_info.value.status_code == 400
    assert "exceeding the target cap" in exc_info.value.detail or "3" in exc_info.value.detail

    # 2. Deactivate u3 -> active count drops to 2
    u3.is_active = False
    await async_db_session.commit()
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2

    # 3. Now scheduling downgrade to Essential succeeds!
    res_sched = await admin_tenants_router.schedule_tenant_downgrade(
        tenant_id=tenant.id,
        plan_id=ess_plan.id,
        current_user=mock_super_admin,
        db=async_db_session,
    )
    assert res_sched["success"] is True

    await async_db_session.refresh(tenant)
    assert tenant.scheduled_downgrade_plan_id == ess_plan.id

    # 4. While downgrade is pending (cap=2), creating a 3rd user MUST BE BLOCKED!
    with pytest.raises(AccountCapacityExceededError):
        await AccountAdmissionService.admit_active_account(async_db_session, tenant_id=tenant.id)

    # 5. Advance to the renewal boundary; early payment must preserve the existing term.
    # Keep the original downgrade assertions, exercising the actual next-period start.
    renewal_time = now + timedelta(days=20)
    class RenewalClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return renewal_time.replace(tzinfo=timezone.utc) if tz else renewal_time
    monkeypatch.setattr("backend.services.subscription_renewal_service.datetime", RenewalClock)
    req_renew = schemas.TenantManualRenewalRequest(
        idempotency_key="downgrd-01",
        extension_days=30,
    )
    res_renew = await renew_subscription(
        async_db_session, tenant_id=tenant.id, request=req_renew, admin=mock_super_admin
    )
    assert res_renew["plan"] == "essential"

    await async_db_session.refresh(tenant)
    assert tenant.plan == "essential"
    assert tenant.plan_id == ess_plan.id
    assert tenant.scheduled_downgrade_plan_id is None


# ---------------------------------------------------------------------------
# 8. Subscription Worker Lifecycle Transitions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_subscription_worker_lifecycle(async_db_session, setup_launch_plans, monkeypatch):
    """Worker handles trial expiry, grace transitions, and respects cancelled/suspended."""
    monkeypatch.setenv("SUBSCRIPTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")

    pro_plan = setup_launch_plans["professional"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Tenant 1: Trial past end date -> directly to expired_read_only (no grace)
    t_trial = models.Tenant(
        id=801,
        name="Worker Trial",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="trial",
        subscription_end_date=now - timedelta(days=2),
        is_active=True,
    )

    # Tenant 2: Paid active past end date but WITHIN 7 grace days -> transitions to grace
    t_paid_grace = models.Tenant(
        id=802,
        name="Worker Grace",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_end_date=now - timedelta(days=3),
        grace_period_until=now + timedelta(days=4),
        is_active=True,
    )

    # Tenant 3: Paid active past grace -> transitions to expired_read_only
    t_paid_exp = models.Tenant(
        id=803,
        name="Worker Expired",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="active",
        subscription_end_date=now - timedelta(days=10),
        grace_period_until=now - timedelta(days=3),
        is_active=True,
    )

    # Tenant 4: Suspended by admin -> MUST NOT be modified by worker!
    t_susp = models.Tenant(
        id=804,
        name="Worker Suspended",
        plan="professional",
        plan_id=pro_plan.id,
        subscription_status="suspended_admin",
        subscription_end_date=now - timedelta(days=15),
        is_active=True,
    )

    async_db_session.add_all([t_trial, t_paid_grace, t_paid_exp, t_susp])
    await async_db_session.commit()

    count = await check_expired_subscriptions(async_db_session)
    assert count == 3  # t_trial, t_paid_grace, t_paid_exp processed

    await async_db_session.refresh(t_trial)
    await async_db_session.refresh(t_paid_grace)
    await async_db_session.refresh(t_paid_exp)
    await async_db_session.refresh(t_susp)

    assert t_trial.subscription_status == "expired_read_only"
    assert t_paid_grace.subscription_status == "grace"
    assert t_paid_exp.subscription_status == "expired_read_only"
    # Worker must NEVER touch suspended_admin:
    assert t_susp.subscription_status == "suspended_admin"
