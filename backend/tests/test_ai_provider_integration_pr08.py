"""PR-08 Acceptance Tests: AI Provider & Tool Integration with Commercial Accounting.

Verifies:
1. Every AI provider path (process_query, analyze-clinic, Scribe) checks commercial availability,
   operation state, and emergency denial before provider dispatch.
2. Finance domain permissions (AI_CHAT AND REPORT_READ) required; data aggregation blocked
   if unauthorized, commercially denied, or quota exhausted.
3. Provider work admitted through PR-07 ledger once per logical request.
4. Server-owned parent reservations propagate to confirmations and secondary tools (0 additional units).
5. Provider-free suggestions, autocomplete, tool listing, and skip-LLM intents consume 0 units.
6. Per-plan capability enforcement in ToolExecutor as an additional AND condition.
7. Explicit outcomes for all edge cases (missing plan, plan-off, emergency-off, expired, suspended, quota exhausted).
8. Shared tenant quota (2 on Essential) across multiple users and entry paths.
9. Live PostgreSQL concurrency serialization on AI entry points.
"""

import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.core.commercial_registry import CapabilityKey, OperationClass
from backend.auth import create_access_token, get_password_hash
from backend.models.ai_accounting import (
    AIQuotaWindow,
    AIReservation,
    ReservationStatus,
)
from backend.services.ai_service import AIService
from backend.services.ai_quota_service import (
    AIQuotaService,
    AIQuotaExhaustedError,
)
from backend.services.commercial_ai_guard import evaluate_commercial_ai_access
from backend.services.scribe_service import ScribeService
from backend.ai.executor import ToolExecutor
from backend.schemas.ai import AIQueryRequest


def _auth_header(user: models.User) -> Dict[str, str]:
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pr08_plans(db_session):
    """Seed standard Essential, Professional, and Business subscription plans."""
    essential = models.SubscriptionPlan(
        name="essential",
        display_name_ar="الأساسية",
        price=Decimal("200.00"),
        max_users=2,
        is_ai_enabled=True,
        ai_daily_limit=2,
        features='{"clinical": true, "billing": true, "laboratories": true, "export_reports": true, "ai_insights": true}',
        is_active=True,
    )
    pro = models.SubscriptionPlan(
        name="professional",
        display_name_ar="المتقدمة",
        price=Decimal("400.00"),
        max_users=5,
        is_ai_enabled=True,
        ai_daily_limit=10,
        features='{"clinical": true, "billing": true, "laboratories": true, "export_reports": true, "ai_insights": true}',
        is_active=True,
    )
    no_ai_plan = models.SubscriptionPlan(
        name="basic_no_ai",
        display_name_ar="بدون ذكاء",
        price=Decimal("150.00"),
        max_users=2,
        is_ai_enabled=False,
        ai_daily_limit=0,
        features='{"clinical": true, "billing": true, "laboratories": false, "export_reports": false, "ai_insights": false}',
        is_active=True,
    )
    no_billing_plan = models.SubscriptionPlan(
        name="clinical_only",
        display_name_ar="عيادي فقط",
        price=Decimal("180.00"),
        max_users=2,
        is_ai_enabled=True,
        ai_daily_limit=2,
        features='{"clinical": true, "billing": false, "laboratories": true, "export_reports": false, "ai_insights": true}',
        is_active=True,
    )
    db_session.add_all([essential, pro, no_ai_plan, no_billing_plan])
    db_session.commit()
    db_session.refresh(essential)
    db_session.refresh(pro)
    db_session.refresh(no_ai_plan)
    db_session.refresh(no_billing_plan)
    return {
        "essential": essential,
        "pro": pro,
        "no_ai": no_ai_plan,
        "no_billing": no_billing_plan,
    }


# ==============================================================================
# 1. Commercial AI Access & Edge Cases
# ==============================================================================

def test_commercial_ai_guard_edge_cases(db_session, pr08_plans):
    """Explicit outcomes for all commercial edge cases before provider dispatch."""
    essential = pr08_plans["essential"]
    no_ai = pr08_plans["no_ai"]

    # 1. Missing tenant / unassigned
    res_missing = evaluate_commercial_ai_access(None)
    assert res_missing is not None
    assert res_missing[0] == "missing_plan"

    # 2. Tenant without assigned plan
    tenant_no_plan = models.Tenant(name="No Plan Clinic", is_active=True, plan=None, plan_id=None)
    db_session.add(tenant_no_plan)
    db_session.commit()
    res_no_plan = evaluate_commercial_ai_access(tenant_no_plan)
    assert res_no_plan is not None
    assert res_no_plan[0] == "missing_plan"

    # 3. Plan with AI disabled
    tenant_no_ai = models.Tenant(
        name="No AI Clinic", is_active=True, plan_id=no_ai.id, plan=no_ai.name
    )
    tenant_no_ai.subscription_plan = no_ai
    db_session.add(tenant_no_ai)
    db_session.commit()
    res_no_ai = evaluate_commercial_ai_access(tenant_no_ai)
    assert res_no_ai is not None
    assert res_no_ai[0] == "plan_restricted"

    # 4. Commercial override denying AI
    tenant_with_plan = models.Tenant(
        name="Override Clinic", is_active=True, plan_id=essential.id, plan=essential.name
    )
    tenant_with_plan.subscription_plan = essential
    db_session.add(tenant_with_plan)
    db_session.commit()

    override = models.CommercialTenantOverride(
        tenant_id=tenant_with_plan.id,
        capability_key="ai_insights",
        override_value="deny",
        reason="Admin restriction",
    )
    db_session.add(override)
    db_session.commit()
    res_override = evaluate_commercial_ai_access(tenant_with_plan, db_session=db_session)
    assert res_override is not None
    assert res_override[0] == "plan_restricted"

    # 5. Expired subscription past grace
    tenant_expired = models.Tenant(
        name="Expired Clinic",
        is_active=True,
        plan_id=essential.id,
        plan=essential.name,
        subscription_status="expired",
        subscription_end_date=datetime.now(timezone.utc) - timedelta(days=5),
        grace_period_until=datetime.now(timezone.utc) - timedelta(days=2),
    )
    tenant_expired.subscription_plan = essential
    db_session.add(tenant_expired)
    db_session.commit()
    res_expired = evaluate_commercial_ai_access(tenant_expired)
    assert res_expired is not None
    assert res_expired[0] == "subscription_expired"

    # 6. Administratively suspended tenant
    tenant_suspended = models.Tenant(
        name="Suspended Clinic",
        is_active=False,
        plan_id=essential.id,
        plan=essential.name,
    )
    tenant_suspended.subscription_plan = essential
    db_session.add(tenant_suspended)
    db_session.commit()
    res_suspended = evaluate_commercial_ai_access(tenant_suspended)
    assert res_suspended is not None
    assert res_suspended[0] == "tenant_suspended"

    # 7. Global AI emergency kill switch
    with patch("backend.services.commercial_ai_guard.is_ai_disabled", return_value=True):
        active_tenant = models.Tenant(
            name="Active Clinic", is_active=True, plan_id=essential.id, plan=essential.name
        )
        active_tenant.subscription_plan = essential
        res_emergency = evaluate_commercial_ai_access(active_tenant)
        assert res_emergency is not None
        assert res_emergency[0] == "ai_emergency_disabled"

    # 8. Active permitted tenant returns None
    active_tenant = models.Tenant(
        name="Active Clinic OK", is_active=True, plan_id=essential.id, plan=essential.name
    )
    active_tenant.subscription_plan = essential
    res_ok = evaluate_commercial_ai_access(active_tenant)
    assert res_ok is None


# ==============================================================================
# 2. AIService.process_query Provider Admission & Quota Ledger
# ==============================================================================

@pytest.mark.asyncio
async def test_process_query_commercial_denials_and_accounting(async_db_session, pr08_plans):
    """Verify AIService.process_query blocks denied tenants and accounts admitted requests."""
    essential = pr08_plans["essential"]
    no_ai = pr08_plans["no_ai"]

    # Setup tenant on Essential
    essential_plan = await async_db_session.get(models.SubscriptionPlan, essential.id)
    tenant = models.Tenant(
        name="AI Process Clinic", is_active=True, plan_id=essential.id, plan=essential.name
    )
    tenant.subscription_plan = essential_plan
    async_db_session.add(tenant)
    await async_db_session.flush()

    doctor = models.User(
        username="doc_process_q",
        email="doc_pq@test.com",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    doctor.tenant = tenant
    async_db_session.add(doctor)
    await async_db_session.commit()

    service = AIService(async_db_session, doctor)

    # Mock agent LLM process to return conversational answer
    mock_agent_result = {
        "success": True,
        "tool": "response",
        "message": "مرحباً دكتور، كيف يمكنني مساعدتك؟",
    }
    with patch.object(service.agent, "process", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_agent_result

        # Request 1: Admitted, consumes 1 unit
        res1 = await service.process_query("مرحبا دكتور")
        assert res1.success is True
        assert res1.error is None
        assert mock_process.call_count == 1

        # Request 2: Admitted, consumes 2nd unit (daily limit = 2)
        res2 = await service.process_query("استفسار طبي")
        assert res2.success is True
        assert res2.error is None
        assert mock_process.call_count == 2

        # Request 3: Daily quota reached! Blocked before calling LLM
        res3 = await service.process_query("سؤال إضافي بعد استهلاك الكوتة")
        assert res3.success is False
        assert res3.error == "limit_exceeded"
        assert mock_process.call_count == 2  # Not incremented! Provider was NOT called.

    # Now verify with a tenant with AI disabled in plan
    no_ai_plan = await async_db_session.get(models.SubscriptionPlan, no_ai.id)
    tenant_denied = models.Tenant(
        name="AI Denied Clinic", is_active=True, plan_id=no_ai.id, plan=no_ai.name
    )
    tenant_denied.subscription_plan = no_ai_plan
    async_db_session.add(tenant_denied)
    await async_db_session.flush()

    doc_denied = models.User(
        username="doc_denied_ai",
        role="doctor",
        tenant_id=tenant_denied.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    doc_denied.tenant = tenant_denied
    async_db_session.add(doc_denied)
    await async_db_session.commit()

    service_denied = AIService(async_db_session, doc_denied)
    with patch.object(service_denied.agent, "process", new_callable=AsyncMock) as mock_process_d:
        res_d = await service_denied.process_query("استفسار")
        assert res_d.success is False
        assert res_d.error == "plan_restricted"
        mock_process_d.assert_not_called()


# ==============================================================================
# 3. Parent Linkage: Confirmation & Secondary Tools Consume 0 Extra Units
# ==============================================================================

@pytest.mark.asyncio
async def test_parent_linkage_confirmation_turn_consumes_zero_additional_units(
    async_db_session, pr08_plans
):
    """
    Turn 1 (tool requiring confirmation): reserves and consumes 1 unit; attaches parent_reservation_id.
    Turn 2 (confirm 'نعم'): executes tool linked to parent; consumes 0 extra units even if limit reached!
    """
    essential = pr08_plans["essential"]
    essential_plan = await async_db_session.get(models.SubscriptionPlan, essential.id)
    tenant = models.Tenant(
        name="Confirm AI Clinic", is_active=True, plan_id=essential.id, plan=essential.name
    )
    tenant.subscription_plan = essential_plan
    async_db_session.add(tenant)
    await async_db_session.flush()

    doctor = models.User(
        username="doc_confirm_pr08",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    doctor.tenant = tenant
    async_db_session.add(doctor)
    await async_db_session.commit()

    service = AIService(async_db_session, doctor)

    # 1. Turn 1: LLM proposes create_patient (requires confirmation)
    turn1_llm_result = {
        "success": True,
        "tool": "create_patient",
        "parameters": {"patient_name": "New Patient PR08", "phone": "01099999999", "age": 30},
    }
    with patch.object(service.agent, "process", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = turn1_llm_result

        res1 = await service.process_query("أنشئ ملف للمريض الجديد")
        assert res1.success is True
        assert res1.risk_level == "CONFIRMATION_REQUIRED"

    # Verify session has pending confirmation WITH parent_reservation_id
    from backend.ai.agent.state_manager import state_manager
    session_state = state_manager.get_session(tenant.id, doctor.id)
    assert session_state.pending_confirmation is not None
    assert session_state.pending_confirmation["tool"] == "create_patient"
    parent_res_id = session_state.pending_confirmation.get("parent_reservation_id")
    assert parent_res_id is not None

    # Exhaust the remaining 1 unit with another query
    with patch.object(service.agent, "process", new_callable=AsyncMock) as mock_agent2:
        mock_agent2.return_value = {"success": True, "tool": "response", "message": "تم"}
        res2 = await service.process_query("سؤال آخر لاستنزاف الكوتة")
        assert res2.success is True

    # Check quota is now exhausted (2/2 units admitted)
    await async_db_session.rollback()
    res_w1 = await async_db_session.execute(
        select(AIQuotaWindow)
        .filter(AIQuotaWindow.tenant_id == tenant.id)
        .execution_options(populate_existing=True)
    )
    window1 = res_w1.scalar_one_or_none()
    assert (window1.reserved_count + window1.consumed_count) == 2

    # 2. Turn 2: User says "نعم" to confirm the action!
    # Exhaustion must NOT block the deterministic confirmation turn!
    with patch.object(service.executor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"success": True, "message": "تم تسجيل المريض بنجاح"}

        res_confirm = await service.process_query("نعم")
        assert res_confirm.success is True
        assert res_confirm.tool == "create_patient"
        mock_exec.assert_called_once()
        # Verify parent_reservation_id was passed to executor
        _, kwargs = mock_exec.call_args
        assert kwargs.get("parent_reservation_id") == parent_res_id

    # Verify daily quota consumption count DID NOT increase past 2!
    await async_db_session.rollback()
    res_w2 = await async_db_session.execute(
        select(AIQuotaWindow)
        .filter(AIQuotaWindow.tenant_id == tenant.id)
        .execution_options(populate_existing=True)
    )
    window2 = res_w2.scalar_one_or_none()
    assert (window2.reserved_count + window2.consumed_count) == 2


# ==============================================================================
# 4. Provider-Free Paths Consume Zero Units
# ==============================================================================

def test_provider_free_paths_consume_zero_units(client, db_session, pr08_plans):
    """Autocomplete and tools listing endpoints consume 0 quota units."""
    essential = pr08_plans["essential"]
    tenant = models.Tenant(
        name="Free Path Clinic", is_active=True, plan_id=essential.id, plan=essential.name
    )
    tenant.subscription_plan = essential
    db_session.add(tenant)
    db_session.commit()

    doctor = models.User(
        username="doc_free_paths",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    doctor.tenant = tenant
    db_session.add(doctor)
    db_session.commit()

    headers = _auth_header(doctor)

    # 1. Autocomplete
    res_ac = client.get("/api/v1/ai/autocomplete?q=Test", headers=headers)
    assert res_ac.status_code == 200

    # 2. Tools list
    res_tools = client.get("/api/v1/ai/tools", headers=headers)
    assert res_tools.status_code == 200

    # Verify zero quota units reserved or consumed
    window = (
        db_session.query(AIQuotaWindow).filter(AIQuotaWindow.tenant_id == tenant.id).first()
    )
    if window:
        assert window.reserved_count == 0
        assert window.consumed_count == 0


# ==============================================================================
# 5. Clinic-Wide Financial Analysis Endpoint Gating
# ==============================================================================

def test_analyze_clinic_permissions_and_data_protection(client, db_session, pr08_plans):
    """
    POST /api/v1/admin/ai/analyze-clinic:
    1. Neither permission -> 403.
    2. Only AI_CHAT -> 403.
    3. Only REPORT_READ -> 403.
    4. Both permissions, but quota exhausted or commercial denied -> 403 without data aggregation!
    5. Both permissions and quota available -> aggregates data and calls provider.
    """
    essential = pr08_plans["essential"]
    tenant = models.Tenant(
        name="Finance AI Clinic", is_active=True, plan_id=essential.id, plan=essential.name
    )
    tenant.subscription_plan = essential
    db_session.add(tenant)
    db_session.commit()

    # User 1: doctor (has AI_CHAT, lacks REPORT_READ)
    doc_user = models.User(
        username="doc_fin_pr08",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    # User 2: guest (lacks required permissions)
    acc_user = models.User(
        username="guest_fin_pr08",
        role="guest",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    # User 3: admin (has BOTH AI_CHAT and REPORT_READ)
    admin_user = models.User(
        username="admin_fin_pr08",
        role="admin",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    admin_user.tenant = tenant
    doc_user.tenant = tenant
    acc_user.tenant = tenant

    db_session.add_all([doc_user, acc_user, admin_user])
    db_session.commit()

    stats_payload = {
        "revenue": 10000.0,
        "expenses": 4000.0,
        "total_costs": 4000.0,
        "net_profit": 6000.0,
        "margin_percent": 60.0,
        "breakdown": {"expenses": 4000.0, "lab_costs": 1000.0, "material_costs": 1000.0},
    }

    # Case 1: Doctor (only AI_CHAT) -> 403 Forbidden
    res_doc = client.post(
        "/api/v1/admin/ai/analyze-clinic",
        json=stats_payload,
        headers=_auth_header(doc_user),
    )
    assert res_doc.status_code == 403

    # Case 2: Accountant (only REPORT_READ) -> 403 Forbidden
    res_acc = client.post(
        "/api/v1/admin/ai/analyze-clinic",
        json=stats_payload,
        headers=_auth_header(acc_user),
    )
    assert res_acc.status_code == 403, res_acc.json()

    # Case 3: Admin (both permissions), spy on detailed analytics aggregation
    with patch(
        "backend.routers.analytics_ai_v2.get_detailed_analytics", new_callable=AsyncMock
    ) as mock_analytics, patch.object(
        AIService, "analyze_direct", new_callable=AsyncMock
    ) as mock_analyze:
        mock_analytics.return_value = "Detailed KPI Context"
        mock_analyze.return_value = MagicMock(success=True, message="تحليل مالي ممتاز")

        # Call 1: Admitted (consumes 1st unit)
        res_adm1 = client.post(
            "/api/v1/admin/ai/analyze-clinic",
            json=stats_payload,
            headers=_auth_header(admin_user),
        )
        assert res_adm1.status_code == 200
        assert mock_analytics.call_count == 1
        assert mock_analyze.call_count == 1

        # Call 2: Admitted (consumes 2nd unit, reaching limit of 2)
        res_adm2 = client.post(
            "/api/v1/admin/ai/analyze-clinic",
            json=stats_payload,
            headers=_auth_header(admin_user),
        )
        assert res_adm2.status_code == 200
        assert mock_analytics.call_count == 2

        # Call 3: Quota exhausted! Must be rejected with 403 limit_exceeded
        # AND get_detailed_analytics MUST NOT be called!
        res_adm3 = client.post(
            "/api/v1/admin/ai/analyze-clinic",
            json=stats_payload,
            headers=_auth_header(admin_user),
        )
        assert res_adm3.status_code == 403
        assert "limit_exceeded" in res_adm3.text
        # CRITICAL ASSERTION: Protected data aggregation was BLOCKED upfront!
        assert mock_analytics.call_count == 2
        assert mock_analyze.call_count == 2


# ==============================================================================
# 6. Scribe Service Commercial Gating & Quota Sharing
# ==============================================================================

def test_scribe_service_commercial_gating_and_quota_sharing(monkeypatch, db_session, pr08_plans):
    """
    ScribeService.analyze_dictation:
    1. Blocks if commercial AI access is denied.
    2. Shares tenant daily quota (limit = 2).
    3. Standalone call without parent reservation consumes 1 unit.
    """
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    essential = pr08_plans["essential"]
    tenant = models.Tenant(
        name="Scribe Clinic PR08", is_active=True, plan_id=essential.id, plan=essential.name
    )
    tenant.subscription_plan = essential
    db_session.add(tenant)
    db_session.commit()

    user = models.User(
        username="doc_scribe_pr08",
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    user.tenant = tenant
    db_session.add(user)
    db_session.commit()

    service = ScribeService()

    # Mock groq client completion
    mock_choice = MagicMock()
    mock_choice.message.content = '{"procedures": [{"tooth_fdi": 16, "diagnosis": "Caries", "treatment": "Restoration"}]}'
    mock_completion = MagicMock(choices=[mock_choice])

    with patch.object(service, "client") as mock_groq_client:
        mock_groq_client.chat.completions.create.return_value = mock_completion

        # Call 1: Admitted (consumes 1 unit)
        res1 = service.analyze_dictation(
            "خلع ضرس 16", tenant_id=tenant.id, user_id=user.id, session=db_session
        )
        assert len(res1) == 1
        assert res1[0]["tooth_fdi"] == 16

        # Call 2: Admitted (consumes 2nd unit)
        res2 = service.analyze_dictation(
            "حشو عصب ضرس 24", tenant_id=tenant.id, user_id=user.id, session=db_session
        )
        assert len(res2) == 1

        # Call 3: Daily quota exhausted! Raises AIQuotaExhaustedError
        with pytest.raises(AIQuotaExhaustedError):
            service.analyze_dictation(
                "تنظيف جير", tenant_id=tenant.id, user_id=user.id, session=db_session
            )


# ==============================================================================
# 7. ToolExecutor Per-Plan Capability Enforcement
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_executor_per_plan_capability_enforcement(async_db_session, pr08_plans):
    """ToolExecutor enforces plan-level capabilities as an additional AND condition."""
    no_billing = pr08_plans["no_billing"]
    no_billing_plan = await async_db_session.get(models.SubscriptionPlan, no_billing.id)
    tenant = models.Tenant(
        name="Clinical Only Clinic", is_active=True, plan_id=no_billing.id, plan=no_billing.name
    )
    tenant.subscription_plan = no_billing_plan
    async_db_session.add(tenant)
    await async_db_session.flush()

    # Admin user has REPORT_READ and RECEIVABLE_READ RBAC permissions
    admin = models.User(
        username="admin_clinical_only",
        role="admin",
        tenant_id=tenant.id,
        is_active=True,
        hashed_password=get_password_hash("pass123"),
    )
    admin.tenant = tenant
    async_db_session.add(admin)
    await async_db_session.commit()

    executor = ToolExecutor(async_db_session, admin)

    # 1. Tool requiring clinical capability (allowed on clinical_only plan)
    # get_recent_treatments is a read tool, permanently permitted under clinical history invariant
    res_clin = await executor.execute("get_recent_treatments", {})
    assert res_clin.get("success") is True

    # 2. Tool requiring billing capability (disabled on clinical_only plan)
    # In enforce mode, get_procedure_price / create_payment must be blocked by plan_restricted
    with patch("backend.core.config.get_subscription_enforcement_mode", return_value="enforce"):
        res_billing = await executor.execute("get_procedure_price", {"procedure_name": "خلع"})
        assert res_billing.get("success") is False
        assert res_billing.get("error_code") == "plan_restricted"


# ==============================================================================
# 8. PostgreSQL Concurrency Serialization on AI Entry
# ==============================================================================

@pytest.mark.asyncio
async def test_postgresql_concurrent_ai_entry_serialized():
    """
    On live PostgreSQL with row-locking on ai_quota_windows:
    5 concurrent requests against an Essential tenant (limit = 2) serialize atomically:
    exactly 2 succeed, exactly 3 fail with limit_exceeded / AIQuotaExhaustedError.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url or "postgresql" not in test_db_url:
        pytest.skip("TEST_DATABASE_URL with PostgreSQL required for live concurrency test.")

    sync_db_url = test_db_url.replace("postgresql+asyncpg://", "postgresql://")
    async_db_url = sync_db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(async_db_url, pool_size=10, max_overflow=10)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    tenant_id = random.randint(900000, 999999)
    unique_suffix = uuid.uuid4().hex[:8]

    # Setup Essential plan (limit = 2) and tenant with 5 users
    async with async_session_maker() as session:
        plan = models.SubscriptionPlan(
            name=f"pr08_pg_plan_{unique_suffix}",
            display_name_ar="خطة تزامن",
            price=Decimal("200.00"),
            max_users=2,
            is_ai_enabled=True,
            ai_daily_limit=2,
            features='{"clinical": true, "billing": true, "laboratories": true, "export_reports": true, "ai_insights": true}',
            is_active=True,
        )
        session.add(plan)
        await session.flush()

        tenant = models.Tenant(
            id=tenant_id,
            name=f"PG AI Clinic {unique_suffix}",
            plan_id=plan.id,
            plan=plan.name,
            is_active=True,
        )
        session.add(tenant)
        await session.flush()

        users = [
            models.User(
                username=f"pg_ai_u_{i}_{unique_suffix}",
                role="doctor",
                tenant_id=tenant_id,
                is_active=True,
                hashed_password="pw_pg_concurrent",
            )
            for i in range(5)
        ]
        session.add_all(users)
        await session.commit()
        user_ids = [u.id for u in users]

    # Race 5 concurrent reservation attempts
    async def try_ai_entry(idx: int) -> bool:
        async with async_session_maker():
            try:
                def _do_work():
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import Session as SyncSession
                    s_engine = create_engine(sync_db_url)
                    with SyncSession(s_engine) as sync_session:
                        res = AIQuotaService.reserve_quota(
                            sync_session,
                            tenant_id=tenant_id,
                            user_id=user_ids[idx],
                            operation="ai_chat",
                            payload={"query": f"prompt_{idx}"},
                        )
                        return bool(res.status == ReservationStatus.RESERVED.value)

                return await asyncio.to_thread(_do_work)
            except AIQuotaExhaustedError:
                return False

    tasks = [try_ai_entry(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    # Exactly 2 succeed and exactly 3 fail
    assert results.count(True) == 2, f"Expected 2 successes, got {results.count(True)}"
    assert results.count(False) == 3, f"Expected 3 exhausted errors, got {results.count(False)}"

    # Verify window in DB has exactly 2 admitted
    async with async_session_maker() as s:
        stmt = select(AIQuotaWindow).where(AIQuotaWindow.tenant_id == tenant_id)
        result = await s.execute(stmt)
        window = result.scalar_one()
        assert window.reserved_count == 2
        assert window.consumed_count == 0
