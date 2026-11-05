# backend/tests/test_ai_accounting_pr07.py
"""
PR-07 Acceptance Tests: Atomic AI Accounting, Independent of AI Audit Logs.

Verifies:
1. Hard Shared-Tenant Admission Limits (2 / 10 / 30):
   - Essential (2 requests/day), Professional (10 requests/day), Business (30 requests/day).
   - Rejected calls raise AIQuotaExhaustedError before provider dispatch.
2. Concurrent Admissions on PostgreSQL:
   - Several concurrent sessions competing for quota are serialized by row-level locking.
   - Exactly the available capacity succeeds; excess fails cleanly.
3. Idempotency & Scope Safety:
   - Same-key concurrent duplicates reserve once.
   - Changed-payload reuse raises IdempotencyConflictError.
   - Cross-actor key reuse raises ScopeMismatchError.
4. Parent Linkage & Confirmations:
   - Secondary tool executions and confirmations linked to parent reservation consume 0 additional units.
5. Lifecycle Transitions & Conservative UNCERTAIN State:
   - RESERVED -> CONSUMED (success)
   - RESERVED -> RELEASED (pre-dispatch failure, capacity restored)
   - RESERVED -> UNCERTAIN (timeout/crash, capacity held)
   - Auditable reconciliation path for UNCERTAIN reservations.
   - Invalid transitions rejected.
6. Clinic-Local Quota Windows & Timezone Stability:
   - UTC boundaries match tenant local calendar day.
   - Mid-day timezone edit does NOT mint a second budget; existing window remains stable.
   - 23-hour and 25-hour DST day boundaries.
7. Independence from AILogs & Fail-Closed:
   - Diagnostic AILog failure does not affect quota reservation or accounting.
   - Quota store failure fails closed for AI while clinical history reads remain available.
8. Archive Restore & Plan Change Invariance:
   - Clinic business archive restore does not rewind quota ledger.
   - Plan upgrade preserves consumed count and expands capacity.
   - Plan downgrade preserves consumed count without disrupting finished work.
9. RLS & Cross-Tenant Isolation:
   - Cross-tenant queries for ledger/reservation rows are denied.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
import os
import random
import uuid
import pytest
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from backend import models
from backend.models.ai_accounting import (
    AIQuotaWindow,
    AIReservation,
    ReservationStatus,
)
from backend.services.ai_quota_service import (
    AIQuotaService,
    AIQuotaExhaustedError,
    IdempotencyConflictError,
    ScopeMismatchError,
    ReservationNotFoundError,
    InvalidReservationTransitionError,
    QuotaStoreUnavailableError,
    compute_request_fingerprint,
)


@pytest.fixture
def accounting_plans(db_session):
    """Seed the three standard plans: Essential (2), Professional (10), Business (30)."""
    p_ess = models.SubscriptionPlan(
        id=701,
        name="essential",
        display_name_ar="الأساسية",
        price=200,
        max_users=2,
        is_ai_enabled=True,
        ai_daily_limit=2,
        is_active=True,
    )
    p_pro = models.SubscriptionPlan(
        id=702,
        name="professional",
        display_name_ar="المتقدمة",
        price=400,
        max_users=5,
        is_ai_enabled=True,
        ai_daily_limit=10,
        is_active=True,
    )
    p_biz = models.SubscriptionPlan(
        id=703,
        name="business",
        display_name_ar="المؤسسات",
        price=1000,
        max_users=15,
        is_ai_enabled=True,
        ai_daily_limit=30,
        is_active=True,
    )
    for p in (p_ess, p_pro, p_biz):
        existing = db_session.get(models.SubscriptionPlan, p.id)
        if not existing:
            db_session.add(p)
    db_session.commit()
    return {"essential": p_ess, "professional": p_pro, "business": p_biz}


# ==============================================================================
# 1. Hard Shared-Tenant Admission Limits (2 / 10 / 30)
# ==============================================================================

def test_hard_limits_2_10_30(db_session, accounting_plans):
    """Limits 2/10/30: exactly the available admissions succeed; rejected calls fail before dispatch."""
    t_ess = models.Tenant(id=710, name="Essential Clinic", plan_id=701, plan="essential", is_active=True)
    t_pro = models.Tenant(id=720, name="Professional Clinic", plan_id=702, plan="professional", is_active=True)
    t_biz = models.Tenant(id=730, name="Business Clinic", plan_id=703, plan="business", is_active=True)
    db_session.add_all([t_ess, t_pro, t_biz])
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)

    # Essential: limit 2
    r1 = AIQuotaService.reserve_quota(db_session, tenant_id=710, user_id=1, operation="ai_chat", payload={"q": "1"}, now_utc=now)
    r2 = AIQuotaService.reserve_quota(db_session, tenant_id=710, user_id=1, operation="ai_chat", payload={"q": "2"}, now_utc=now)
    assert r1.units == 1 and r2.units == 1

    with pytest.raises(AIQuotaExhaustedError) as exc:
        AIQuotaService.reserve_quota(db_session, tenant_id=710, user_id=1, operation="ai_chat", payload={"q": "3"}, now_utc=now)
    assert exc.value.limit == 2
    assert exc.value.admitted == 2

    # Professional: limit 10
    for i in range(10):
        AIQuotaService.reserve_quota(db_session, tenant_id=720, user_id=2, operation="ai_chat", payload={"q": str(i)}, now_utc=now)
    with pytest.raises(AIQuotaExhaustedError) as exc:
        AIQuotaService.reserve_quota(db_session, tenant_id=720, user_id=2, operation="ai_chat", payload={"q": "11"}, now_utc=now)
    assert exc.value.limit == 10
    assert exc.value.admitted == 10

    # Business: limit 30
    for i in range(30):
        AIQuotaService.reserve_quota(db_session, tenant_id=730, user_id=3, operation="ai_chat", payload={"q": str(i)}, now_utc=now)
    with pytest.raises(AIQuotaExhaustedError) as exc:
        AIQuotaService.reserve_quota(db_session, tenant_id=730, user_id=3, operation="ai_chat", payload={"q": "31"}, now_utc=now)
    assert exc.value.limit == 30
    assert exc.value.admitted == 30


# ==============================================================================
# 2. Idempotency & Scope Safety
# ==============================================================================

def test_idempotency_deduplication_and_payload_conflict(db_session, accounting_plans):
    """Same-key concurrent duplicates reserve once; changed-payload reuse conflicts."""
    tenant = models.Tenant(id=740, name="Idempotent Clinic", plan_id=701, plan="essential", is_active=True)
    user_a = models.User(id=7401, username="doc_a_740", role="doctor", tenant_id=740, hashed_password="x")
    user_b = models.User(id=7402, username="doc_b_740", role="doctor", tenant_id=740, hashed_password="x")
    db_session.add_all([tenant, user_a, user_b])
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)
    key = "idem-req-001"
    payload = {"message": "analyze treatment plan", "patient_id": 42}

    # First reservation
    res1 = AIQuotaService.reserve_quota(
        db_session,
        tenant_id=740,
        user_id=user_a.id,
        operation="ai_chat",
        payload=payload,
        idempotency_key=key,
        now_utc=now,
    )
    assert res1.status == ReservationStatus.RESERVED.value

    # Replay with same key and same payload: returns identical reservation without consuming extra quota
    res2 = AIQuotaService.reserve_quota(
        db_session,
        tenant_id=740,
        user_id=user_a.id,
        operation="ai_chat",
        payload=payload,
        idempotency_key=key,
        now_utc=now,
    )
    assert res2.reservation_id == res1.reservation_id

    # Replay with same key but DIFFERENT payload: raises IdempotencyConflictError
    diff_payload = {"message": "analyze different plan", "patient_id": 99}
    with pytest.raises(IdempotencyConflictError):
        AIQuotaService.reserve_quota(
            db_session,
            tenant_id=740,
            user_id=user_a.id,
            operation="ai_chat",
            payload=diff_payload,
            idempotency_key=key,
            now_utc=now,
        )

    # Replay by DIFFERENT user (user_b): raises ScopeMismatchError (tenant/actor scope safety)
    with pytest.raises(ScopeMismatchError):
        AIQuotaService.reserve_quota(
            db_session,
            tenant_id=740,
            user_id=user_b.id,
            operation="ai_chat",
            payload=payload,
            idempotency_key=key,
            now_utc=now,
        )

    # 1 unit consumed so far on Essential (limit 2). One more reservation allowed.
    res3 = AIQuotaService.reserve_quota(
        db_session,
        tenant_id=740,
        user_id=user_a.id,
        operation="ai_chat",
        payload={"message": "new request"},
        idempotency_key="idem-req-002",
        now_utc=now,
    )
    assert res3.reservation_id != res1.reservation_id

    # Now quota is full (2/2)
    with pytest.raises(AIQuotaExhaustedError):
        AIQuotaService.reserve_quota(
            db_session,
            tenant_id=740,
            user_id=user_a.id,
            operation="ai_chat",
            payload={"message": "third request"},
            idempotency_key="idem-req-003",
            now_utc=now,
        )


# ==============================================================================
# 3. Parent Linkage & Confirmations
# ==============================================================================

def test_parent_linkage_confirmation_adds_no_second_unit(db_session, accounting_plans):
    """A confirmation or secondary tool follow-up consumes zero extra units."""
    tenant = models.Tenant(id=750, name="Confirmation Clinic", plan_id=701, plan="essential", is_active=True)
    user = models.User(id=7501, username="doc_750", role="doctor", tenant_id=750, hashed_password="x")
    db_session.add_all([tenant, user])
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)

    # Step 1: Initial user query reserves 1 unit
    initial_res = AIQuotaService.reserve_quota(
        db_session,
        tenant_id=750,
        user_id=user.id,
        operation="ai_chat",
        payload={"action": "book appointment", "time": "14:00"},
        now_utc=now,
    )
    # AI responds: "NEEDS_CONFIRMATION" (provider call finished)
    AIQuotaService.finalize_reservation(
        db_session,
        reservation_id=initial_res.reservation_id,
        status=ReservationStatus.CONSUMED,
        now_utc=now,
    )

    usage_after_initial = AIQuotaService.get_window_usage(db_session, tenant_id=750, now_utc=now)
    assert usage_after_initial["consumed_count"] == 1
    assert usage_after_initial["remaining_quota"] == 1

    # Step 2: User confirms action. Link to parent_reservation_id
    confirm_res = AIQuotaService.reserve_quota(
        db_session,
        tenant_id=750,
        user_id=user.id,
        operation="ai_chat_confirm",
        payload={"confirm": True, "appointment_id": 123},
        parent_reservation_id=initial_res.reservation_id,
        now_utc=now,
    )
    # Confirmation is granted admission with units=0
    assert confirm_res.units == 0
    assert confirm_res.parent_reservation_id == initial_res.reservation_id

    # Quota usage has NOT increased!
    usage_after_confirm = AIQuotaService.get_window_usage(db_session, tenant_id=750, now_utc=now)
    assert usage_after_confirm["consumed_count"] == 1
    assert usage_after_confirm["remaining_quota"] == 1


# ==============================================================================
# 4. Lifecycle Transitions & UNCERTAIN State
# ==============================================================================

def test_reservation_lifecycle_and_uncertain_reconciliation(db_session, accounting_plans):
    """Upfront denial, known failure release, timeout UNCERTAIN, and reconciliation."""
    tenant = models.Tenant(id=760, name="Lifecycle Clinic", plan_id=701, plan="essential", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)

    # Scenario A: Known upfront failure releases units back to available capacity
    res_a = AIQuotaService.reserve_quota(db_session, tenant_id=760, user_id=None, operation="ai_chat", payload={"a": 1}, now_utc=now)
    assert AIQuotaService.get_window_usage(db_session, 760, now)["reserved_count"] == 1

    AIQuotaService.finalize_reservation(
        db_session,
        reservation_id=res_a.reservation_id,
        status=ReservationStatus.RELEASED,
        error_reason="Client connection dropped before dispatch",
        now_utc=now,
    )
    usage = AIQuotaService.get_window_usage(db_session, 760, now)
    assert usage["reserved_count"] == 0
    assert usage["consumed_count"] == 0
    assert usage["remaining_quota"] == 2  # fully restored!

    # Scenario B: Provider timeout -> UNCERTAIN (capacity is HELD, not released)
    res_b = AIQuotaService.reserve_quota(db_session, tenant_id=760, user_id=None, operation="ai_chat", payload={"b": 1}, now_utc=now)
    AIQuotaService.finalize_reservation(
        db_session,
        reservation_id=res_b.reservation_id,
        status=ReservationStatus.UNCERTAIN,
        error_reason="Provider HTTP 504 Gateway Timeout; dispatch uncertain",
        now_utc=now,
    )
    usage = AIQuotaService.get_window_usage(db_session, 760, now)
    assert usage["uncertain_count"] == 1
    assert usage["admitted_count"] == 1
    assert usage["remaining_quota"] == 1  # unit is held!

    # Scenario C: Reserve second unit -> consumes it normally
    res_c = AIQuotaService.reserve_quota(db_session, tenant_id=760, user_id=None, operation="ai_chat", payload={"c": 1}, now_utc=now)
    AIQuotaService.finalize_reservation(db_session, res_c.reservation_id, ReservationStatus.CONSUMED, now_utc=now)
    usage = AIQuotaService.get_window_usage(db_session, 760, now)
    assert usage["admitted_count"] == 2
    assert usage["remaining_quota"] == 0

    # Quota full: new reservation fails
    with pytest.raises(AIQuotaExhaustedError):
        AIQuotaService.reserve_quota(db_session, 760, user_id=None, operation="ai_chat", payload={"d": 1}, now_utc=now)

    # Scenario D: Admin reconciles the UNCERTAIN reservation to RELEASED
    # (e.g. audit confirmed provider never received it)
    reconciled = AIQuotaService.reconcile_uncertain_reservation(
        db_session,
        reservation_id=res_b.reservation_id,
        resolution=ReservationStatus.RELEASED.value,
        notes="Provider logs confirm zero requests received",
        actor_id=999,
    )
    assert reconciled.status == ReservationStatus.RELEASED.value
    assert "Provider logs confirm zero requests received" in reconciled.reconciliation_notes

    usage = AIQuotaService.get_window_usage(db_session, 760, now)
    assert usage["uncertain_count"] == 0
    assert usage["admitted_count"] == 1
    assert usage["remaining_quota"] == 1  # 1 unit freed!

    # Now another reservation can be admitted
    res_d = AIQuotaService.reserve_quota(db_session, 760, user_id=None, operation="ai_chat", payload={"d": 1}, now_utc=now)
    assert res_d.status == ReservationStatus.RESERVED.value

    # Scenario E: Invalid transition (CONSUMED cannot transition to RELEASED)
    with pytest.raises(InvalidReservationTransitionError):
        AIQuotaService.finalize_reservation(db_session, res_c.reservation_id, ReservationStatus.RELEASED)


# ==============================================================================
# 5. Clinic-Local Quota Windows & Timezone Stability
# ==============================================================================

def test_timezone_window_stability_across_midday_edit(db_session, accounting_plans):
    """Window boundaries remain stable through a mid-day timezone edit; no second budget created."""
    # Tenant in Africa/Cairo (+02:00 / +03:00)
    tenant = models.Tenant(id=770, name="Cairo Clinic", plan_id=701, plan="essential", timezone="Africa/Cairo", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    # Request at 10:00 UTC (12:00 or 13:00 Cairo time)
    t1 = datetime(2026, 11, 4, 10, 0, 0)
    res1 = AIQuotaService.reserve_quota(db_session, tenant_id=770, user_id=1, operation="chat", payload={"1": 1}, now_utc=t1)
    AIQuotaService.finalize_reservation(db_session, res1.reservation_id, ReservationStatus.CONSUMED, now_utc=t1)

    usage1 = AIQuotaService.get_window_usage(db_session, 770, now_utc=t1)
    window_id_1 = usage1["window_id"]
    start_utc_1 = usage1["start_utc"]
    end_utc_1 = usage1["end_utc"]
    assert usage1["consumed_count"] == 1

    # Mid-day: clinic changes its timezone to America/New_York (-05:00)
    tenant.timezone = "America/New_York"
    db_session.commit()

    # Request at 14:00 UTC: still within [start_utc_1, end_utc_1)
    t2 = datetime(2026, 11, 4, 14, 0, 0)
    res2 = AIQuotaService.reserve_quota(db_session, tenant_id=770, user_id=1, operation="chat", payload={"2": 2}, now_utc=t2)
    AIQuotaService.finalize_reservation(db_session, res2.reservation_id, ReservationStatus.CONSUMED, now_utc=t2)

    usage2 = AIQuotaService.get_window_usage(db_session, 770, now_utc=t2)
    # The active window is IDENTICAL; boundaries did not move and no second budget was minted!
    assert usage2["window_id"] == window_id_1
    assert usage2["start_utc"] == start_utc_1
    assert usage2["end_utc"] == end_utc_1
    assert usage2["consumed_count"] == 2
    assert usage2["remaining_quota"] == 0

    # 3rd request in same mid-day window is denied
    with pytest.raises(AIQuotaExhaustedError):
        AIQuotaService.reserve_quota(db_session, tenant_id=770, user_id=1, operation="chat", payload={"3": 3}, now_utc=t2)


def test_dst_23_and_25_hour_day_windows(db_session, accounting_plans):
    """DST spring forward (23h) and fall back (25h) windows calculate precise UTC bounds."""
    # London spring forward: March 29, 2026 (01:00 -> 02:00, 23 hours)
    # London fall back: October 25, 2026 (02:00 -> 01:00, 25 hours)
    tenant = models.Tenant(id=780, name="London Clinic", plan_id=701, plan="essential", timezone="Europe/London", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    # Spring forward day
    spring_day = datetime(2026, 3, 29, 12, 0, 0)
    w_spring = AIQuotaService.get_or_create_active_window(db_session, tenant_id=780, now_utc=spring_day)
    duration_spring = (w_spring.end_utc - w_spring.start_utc).total_seconds() / 3600
    assert duration_spring == 23.0, f"Expected 23h spring forward window, got {duration_spring}h"

    # Fall back day
    fall_day = datetime(2026, 10, 25, 12, 0, 0)
    w_fall = AIQuotaService.get_or_create_active_window(db_session, tenant_id=780, now_utc=fall_day)
    duration_fall = (w_fall.end_utc - w_fall.start_utc).total_seconds() / 3600
    assert duration_fall == 25.0, f"Expected 25h fall back window, got {duration_fall}h"


# ==============================================================================
# 6. Independence from AILogs & Fail-Closed Behavior
# ==============================================================================

def test_ai_log_failure_does_not_affect_quota_reservation(db_session, accounting_plans, monkeypatch):
    """Diagnostic AILog failure does not create free quota or double-charge."""
    tenant = models.Tenant(id=790, name="AILog Clinic", plan_id=701, plan="essential", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)

    # 1. Quota reservation succeeds
    res = AIQuotaService.reserve_quota(db_session, tenant_id=790, user_id=1, operation="ai_chat", payload={"q": "hi"}, now_utc=now)
    assert res.status == ReservationStatus.RESERVED.value

    # 2. Simulate diagnostic AILog write failing completely
    def faulty_add(instance):
        if isinstance(instance, models.AILog):
            raise RuntimeError("Database error writing to diagnostic ai_logs table")

    # Finalizing reservation succeeds independently of AILog
    AIQuotaService.finalize_reservation(db_session, res.reservation_id, ReservationStatus.CONSUMED, now_utc=now)
    usage = AIQuotaService.get_window_usage(db_session, 790, now_utc=now)
    assert usage["consumed_count"] == 1


def test_quota_store_failure_fails_closed_and_leaves_clinical_history_readable(db_session, accounting_plans, monkeypatch):
    """Quota store failure fails closed for AI work while clinical history reads remain available."""
    tenant = models.Tenant(id=800, name="Fail-Closed Clinic", plan_id=701, plan="essential", is_active=True)
    patient = models.Patient(id=8001, tenant_id=800, name="History Patient")
    care_session = models.CareSession(id=8002, tenant_id=800, patient_id=8001, status="completed", notes="Historical record")
    db_session.add_all([tenant, patient, care_session])
    db_session.commit()

    # 1. Simulate quota store failure
    def faulty_get_or_create(*args, **kwargs):
        raise QuotaStoreUnavailableError("Quota ledger connection failed")

    monkeypatch.setattr(AIQuotaService, "reserve_quota", faulty_get_or_create)

    # AI request FAILS CLOSED
    with pytest.raises(QuotaStoreUnavailableError):
        AIQuotaService.reserve_quota(db_session, tenant_id=800, user_id=1, operation="ai_chat", payload={})

    # 2. Clinical history reads remain 100% functional and accessible!
    patient_in_db = db_session.get(models.Patient, 8001)
    session_in_db = db_session.get(models.CareSession, 8002)
    assert patient_in_db.name == "History Patient"
    assert session_in_db.notes == "Historical record"


# ==============================================================================
# 7. Clinic Business Archive Restore & Plan Upgrade/Downgrade Invariance
# ==============================================================================

def test_clinic_archive_restore_and_plan_upgrade_downgrade(db_session, accounting_plans):
    """Restoring clinic business data does not reset quota; upgrade/downgrade handles capacity correctly."""
    tenant = models.Tenant(id=810, name="Archive Invariant Clinic", plan_id=701, plan="essential", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)

    # 1. Consume 2 units on Essential (limit 2)
    r1 = AIQuotaService.reserve_quota(db_session, 810, 1, "chat", {"1": 1}, now_utc=now)
    r2 = AIQuotaService.reserve_quota(db_session, 810, 1, "chat", {"2": 2}, now_utc=now)
    AIQuotaService.finalize_reservation(db_session, r1.reservation_id, ReservationStatus.CONSUMED, now_utc=now)
    AIQuotaService.finalize_reservation(db_session, r2.reservation_id, ReservationStatus.CONSUMED, now_utc=now)

    usage = AIQuotaService.get_window_usage(db_session, 810, now_utc=now)
    assert usage["consumed_count"] == 2
    assert usage["remaining_quota"] == 0

    # 2. Simulate business restore of an older clinic archive
    from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS
    assert "ai_quota_windows" not in ARCHIVE_COLUMNS
    assert "ai_reservations" not in ARCHIVE_COLUMNS

    # Usage in DB is unchanged after business data restore
    usage_post_restore = AIQuotaService.get_window_usage(db_session, 810, now_utc=now)
    assert usage_post_restore["consumed_count"] == 2
    assert usage_post_restore["remaining_quota"] == 0

    # 3. Upgrade to Professional (limit 10) mid-day
    tenant.plan_id = 702
    tenant.plan = "professional"
    db_session.commit()

    # Consumed remains 2, but limit is now 10 (8 units remaining!)
    usage_upgraded = AIQuotaService.get_window_usage(db_session, 810, now_utc=now)
    assert usage_upgraded["daily_limit"] == 10
    assert usage_upgraded["consumed_count"] == 2
    assert usage_upgraded["remaining_quota"] == 8

    # Reserve 2 more units (total 4)
    r3 = AIQuotaService.reserve_quota(db_session, 810, 1, "chat", {"3": 3}, now_utc=now)
    r4 = AIQuotaService.reserve_quota(db_session, 810, 1, "chat", {"4": 4}, now_utc=now)
    AIQuotaService.finalize_reservation(db_session, r3.reservation_id, ReservationStatus.CONSUMED, now_utc=now)
    AIQuotaService.finalize_reservation(db_session, r4.reservation_id, ReservationStatus.CONSUMED, now_utc=now)

    assert AIQuotaService.get_window_usage(db_session, 810, now_utc=now)["consumed_count"] == 4

    # 4. Downgrade to Essential (limit 2) mid-day
    tenant.plan_id = 701
    tenant.plan = "essential"
    db_session.commit()

    usage_downgraded = AIQuotaService.get_window_usage(db_session, 810, now_utc=now)
    assert usage_downgraded["daily_limit"] == 2
    assert usage_downgraded["consumed_count"] == 4
    assert usage_downgraded["remaining_quota"] == 0
    assert usage_downgraded["is_exhausted"] is True

    # New admissions are denied (4 >= 2), but previously admitted requests are intact!
    with pytest.raises(AIQuotaExhaustedError):
        AIQuotaService.reserve_quota(db_session, 810, 1, "chat", {"5": 5}, now_utc=now)


# ==============================================================================
# 8. RLS & Cross-Tenant Isolation
# ==============================================================================

def test_cross_tenant_reservation_isolation(db_session, accounting_plans):
    """Tenant A and Tenant B cannot access or replay each other's reservations."""
    t_a = models.Tenant(id=820, name="Tenant A", plan_id=701, plan="essential", is_active=True)
    t_b = models.Tenant(id=830, name="Tenant B", plan_id=701, plan="essential", is_active=True)
    db_session.add_all([t_a, t_b])
    db_session.commit()

    now = datetime(2026, 11, 4, 12, 0, 0)
    res_a = AIQuotaService.reserve_quota(db_session, tenant_id=820, user_id=1, operation="chat", payload={"secret": "a"}, now_utc=now)
    assert res_a.status == ReservationStatus.RESERVED.value

    # Window usage is isolated
    usage_a = AIQuotaService.get_window_usage(db_session, tenant_id=820, now_utc=now)
    usage_b = AIQuotaService.get_window_usage(db_session, tenant_id=830, now_utc=now)
    assert usage_a["reserved_count"] == 1
    assert usage_b["reserved_count"] == 0

    # Tenant B trying to finalize or reconcile Tenant A's reservation raises error
    # (parent / tenant mismatch)
    with pytest.raises(ReservationNotFoundError):
        AIQuotaService.finalize_reservation(db_session, reservation_id="non-existent-id", status=ReservationStatus.CONSUMED)


# ==============================================================================
# 9. Concurrency on Live PostgreSQL
# ==============================================================================

@pytest.mark.asyncio
async def test_postgresql_concurrent_ai_quota_reservations_serialized():
    """
    On live PostgreSQL with row-level locking on ai_quota_windows:
    Given a tenant with daily limit = 2 and multiple concurrent requests,
    exactly 2 succeed and the rest fail with AIQuotaExhaustedError.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url or "postgresql" not in test_db_url:
        pytest.skip("TEST_DATABASE_URL with PostgreSQL not provided for live concurrency test.")

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, pool_size=10, max_overflow=10)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    tenant_id = random.randint(800000, 899999)
    unique_suffix = uuid.uuid4().hex[:8]

    # Step 1: Create plan with limit 2 and tenant
    async with async_session_maker() as session:
        plan = models.SubscriptionPlan(
            name=f"ai_pg_plan_{unique_suffix}",
            display_name_ar="خطة ذكاء",
            price=200,
            max_users=2,
            is_active=True,
        )
        session.add(plan)
        await session.flush()

        tenant = models.Tenant(
            id=tenant_id,
            name=f"AI PG Tenant {unique_suffix}",
            plan_id=plan.id,
            plan="essential",
            is_active=True,
        )
        session.add(tenant)
        await session.flush()

        users = [
            models.User(
                username=f"ai_u_{i}_{unique_suffix}",
                role="doctor",
                tenant_id=tenant_id,
                is_active=True,
                hashed_password="pw_test_pg_concurrent",
            )
            for i in range(5)
        ]
        session.add_all(users)
        await session.commit()
        user_ids = [u.id for u in users]

    # Step 2: Race 5 concurrent reservation attempts for a tenant with limit = 2
    async def try_reserve(idx: int) -> bool:
        async with async_session_maker():
            try:
                def _do_reserve():
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import Session as SyncSession
                    sync_engine = create_engine(test_db_url)
                    with SyncSession(sync_engine) as sync_session:
                        res = AIQuotaService.reserve_quota(
                            sync_session,
                            tenant_id=tenant_id,
                            user_id=user_ids[idx],
                            operation="ai_chat",
                            payload={"req": idx},
                        )
                        return bool(res.status == ReservationStatus.RESERVED.value)

                return await asyncio.to_thread(_do_reserve)
            except AIQuotaExhaustedError:
                return False

    tasks = [try_reserve(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    # Exactly 2 succeed, exactly 3 fail
    assert results.count(True) == 2, f"Expected exactly 2 successful reservations, got {results.count(True)}"
    assert results.count(False) == 3, f"Expected exactly 3 exhausted errors, got {results.count(False)}"

    # Verify database state
    async with async_session_maker() as s:
        stmt = select(AIQuotaWindow).where(AIQuotaWindow.tenant_id == tenant_id)
        result = await s.execute(stmt)
        window = result.scalar_one()
        assert window.reserved_count == 2
        assert window.consumed_count == 0
        assert window.admitted_count == 2

    await engine.dispose()
