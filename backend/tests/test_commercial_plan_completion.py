import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend import models, schemas
from backend.auth import create_access_token
from backend.database import get_async_db
from backend.main import app
from backend.services.subscription_service import SubscriptionService
from backend.services.subscription_renewal_service import renew_subscription
from backend.services.commercial_decision import CommercialDecisionEngine
from backend.services.ai_quota_service import AIQuotaService
from backend.services.entitlement_diagnostics_service import (
    build_tenant_entitlement_diagnostics,
)
from backend.tests import test_commercial_release_hardening as fixtures

sample = fixtures.sample
enforced = fixtures.enforced
URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture
def pg_case():
    if not URL.startswith("postgresql"):
        pytest.skip("Isolated TEST_DATABASE_URL PostgreSQL required")
    engine = create_engine(URL)
    with Session(engine, expire_on_commit=False) as db:
        plans = {}
        for name, price, seats, ai in [
            ("professional", 400, 5, 10),
            ("essential", 200, 2, 2),
        ]:
            plan = db.query(models.SubscriptionPlan).filter_by(name=name).first()
            if plan is None:
                plan = models.SubscriptionPlan(
                    name=name,
                    display_name_ar="Synthetic",
                    price=price,
                    max_users=seats,
                    is_ai_enabled=True,
                    ai_daily_limit=ai,
                    features='{"clinical":true,"billing":true,"ai_insights":true}',
                    is_active=True,
                )
                db.add(plan)
                db.flush()
            plans[name] = plan
        tenant = models.Tenant(
            name="Synthetic plan audit " + uuid4().hex,
            plan_id=plans["professional"].id,
            plan="professional",
            subscription_status="active",
            is_active=True,
            subscription_end_date=datetime.utcnow() + timedelta(days=20),
        )
        db.add(tenant)
        db.flush()
        admin = models.User(
            username="audit_admin_" + uuid4().hex,
            hashed_password="synthetic-not-real",
            role="super_admin",
            is_active=True,
        )
        db.add(admin)
        for _ in range(3):
            db.add(
                models.User(
                    username="audit_user_" + uuid4().hex,
                    hashed_password="synthetic-not-real",
                    role="doctor",
                    tenant_id=tenant.id,
                    is_active=True,
                    is_deleted=False,
                )
            )
        db.commit()
        yield SimpleNamespace(tenant=tenant, admin=admin, plans=plans, db=db)
    engine.dispose()


@pytest.fixture
def pg_client(client, pg_case, monkeypatch):
    old = app.dependency_overrides.get(get_async_db)

    async def session():
        engine = create_async_engine(
            URL.replace("postgresql://", "postgresql+asyncpg://")
        )
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                yield db
        finally:
            await engine.dispose()

    monkeypatch.setattr(
        "backend.database.system_session_scope", asynccontextmanager(session)
    )
    app.dependency_overrides[get_async_db] = session
    try:
        yield client
    finally:
        if old is None:
            app.dependency_overrides.pop(get_async_db, None)
        else:
            app.dependency_overrides[get_async_db] = old


def headers(case):
    token = create_access_token(
        data={"sub": case.admin.username, "role": "super_admin", "tenant_id": None}
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Idempotency-Key": "same-manual-receipt",
    }


def test_manual_receipt_retry_extends_only_once(pg_case, pg_client):
    payload = {
        "tenant_id": pg_case.tenant.id,
        "plan_id": pg_case.plans["professional"].id,
        "amount": 400,
        "payment_method": "cash",
    }
    for _ in range(2):
        response = pg_client.post(
            "/api/v1/admin/subscriptions/payments",
            json=payload,
            headers=headers(pg_case),
        )
        assert response.status_code == 200, response.text
    pg_case.db.expire_all()
    count = (
        pg_case.db.query(models.SubscriptionPayment)
        .filter_by(tenant_id=pg_case.tenant.id)
        .count()
    )
    assert count == 1, (
        f"Identical receipt/header created {count} payment records and extended the period twice"
    )


def test_payment_cannot_bypass_lower_plan_account_cap(pg_case, pg_client):
    response = pg_client.post(
        "/api/v1/admin/subscriptions/payments",
        json={
            "tenant_id": pg_case.tenant.id,
            "plan_id": pg_case.plans["essential"].id,
            "amount": 200,
            "payment_method": "cash",
        },
        headers=headers(pg_case),
    )
    pg_case.db.expire_all()
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    assert tenant.plan_id == pg_case.plans["professional"].id, (
        f"HTTP {response.status_code} activated Essential with 3 active clinic accounts (cap=2)"
    )


@pytest.mark.asyncio
async def test_manual_renewal_cannot_bypass_lower_plan_account_cap(pg_case):
    engine = create_async_engine(URL.replace("postgresql://", "postgresql+asyncpg://"))
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            try:
                await renew_subscription(
                    db,
                    tenant_id=pg_case.tenant.id,
                    request=schemas.TenantManualRenewalRequest(
                        plan_id=pg_case.plans["essential"].id,
                        idempotency_key=uuid4().hex,
                    ),
                    admin=pg_case.admin,
                )
            except Exception as exc:
                assert getattr(exc, "status_code", None) in (400, 409)
            tenant = (
                await db.execute(
                    select(models.Tenant).where(models.Tenant.id == pg_case.tenant.id)
                )
            ).scalar_one()
            assert tenant.plan_id == pg_case.plans["professional"].id, (
                "Direct renewal plan_id bypassed scheduled-downgrade seat check"
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("paid_plan", ["professional", "essential"])
async def test_prepaid_trial_expires_with_paid_grace(pg_case, paid_plan):
    engine = create_async_engine(URL.replace("postgresql://", "postgresql+asyncpg://"))
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            tenant = (
                await db.execute(
                    select(models.Tenant).where(models.Tenant.id == pg_case.tenant.id)
                )
            ).scalar_one()
            # Trial purchase chooses a lower tier only after explicit seat reduction.
            if paid_plan == "essential":
                user = (
                    (
                        await db.execute(
                            select(models.User).where(
                                models.User.tenant_id == tenant.id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
                user.is_active = False
            tenant.subscription_status = "trial"
            tenant.subscription_end_date = datetime.utcnow() + timedelta(days=5)
            await db.commit()
            await SubscriptionService.record_payment(
                db,
                schemas.SubscriptionPaymentCreate(
                    tenant_id=tenant.id,
                    plan_id=pg_case.plans[paid_plan].id,
                    amount=400,
                    payment_method="cash",
                ),
                pg_case.admin.username,
            )
            await db.refresh(tenant)
            # Populate relationships so this is not a lazy-loading false result.
            tenant.subscription_plan = await db.get(
                models.SubscriptionPlan, tenant.plan_id
            )
            if tenant.future_plan_id:
                tenant.future_plan = await db.get(
                    models.SubscriptionPlan, tenant.future_plan_id
                )
            within = CommercialDecisionEngine.evaluate_capability(
                tenant,
                "clinical",
                "write_business",
                now=tenant.subscription_end_date + timedelta(days=1),
                override_mode="enforce",
            )
            after = CommercialDecisionEngine.evaluate_capability(
                tenant,
                "clinical",
                "write_business",
                now=tenant.subscription_end_date + timedelta(days=8),
                override_mode="enforce",
            )
            assert within.allowed is True, (
                f"Paid {paid_plan} month lost approved 7-day grace; raw status={tenant.subscription_status}"
            )
            assert after.allowed is False, (
                f"Paid {paid_plan} future plan still active after end+8 days without worker normalization"
            )
    finally:
        await engine.dispose()


def test_saved_trial_policy_controls_registration(db_session, client, sample):
    token = create_access_token(
        data={"sub": sample.admin.username, "role": "super_admin", "tenant_id": None}
    )
    response = client.put(
        "/api/v1/admin/subscriptions/trial-policy",
        json={
            "trial_plan_name": "professional",
            "trial_duration_days": 21,
            "reason": "Synthetic future-policy test",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    name = "Synthetic registration " + uuid4().hex
    response = client.post(
        "/api/v1/auth/register_clinic",
        data={
            "clinic_name": name,
            "admin_username": "reg_" + uuid4().hex,
            "admin_email": uuid4().hex + "@example.invalid",
            "admin_password": "SyntheticPass!42",
            "contact_phone": "01000000000",
        },
    )
    assert response.status_code == 201, response.text
    tenant = db_session.query(models.Tenant).filter_by(name=name).one()
    days = (tenant.subscription_end_date - tenant.subscription_start_date).days
    assert days == 21, (
        f"Saved future-trial policy is 21 days, actual registration created {days}"
    )


@pytest.mark.asyncio
async def test_diagnostics_uses_current_quota_ledger(
    db_session, async_db_session, sample
):
    AIQuotaService.reserve_quota(
        db_session,
        sample.tenant.id,
        sample.user.id,
        "ai_chat",
        "Synthetic audit request",
    )
    diagnostics = await build_tenant_entitlement_diagnostics(
        async_db_session, sample.tenant.id
    )
    quota = diagnostics["capacities"]["ai"]
    assert quota["quota_ledger_source"] == "ai_quota_windows", (
        f"Ledger exists, diagnostics still reports {quota}"
    )
    assert quota["remaining_quota"] == 9


@pytest.mark.asyncio
async def test_same_plan_manual_renewal_persists_on_postgresql(pg_case):
    engine = create_async_engine(URL.replace("postgresql://", "postgresql+asyncpg://"))
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            await renew_subscription(
                db,
                tenant_id=pg_case.tenant.id,
                request=schemas.TenantManualRenewalRequest(idempotency_key=uuid4().hex),
                admin=pg_case.admin,
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_direct_renewal_refuses_over_capacity_downgrade_on_sqlite(
    db_session, async_db_session, sample
):
    lower = models.SubscriptionPlan(
        name="essential",
        display_name_ar="Synthetic Essential",
        price=200,
        max_users=2,
        is_ai_enabled=True,
        ai_daily_limit=2,
        is_active=True,
    )
    db_session.add(lower)
    for _ in range(2):
        db_session.add(
            models.User(
                username="extra_" + uuid4().hex,
                hashed_password="synthetic",
                tenant_id=sample.tenant.id,
                role="doctor",
                is_active=True,
                is_deleted=False,
            )
        )
    db_session.commit()
    try:
        await renew_subscription(
            async_db_session,
            tenant_id=sample.tenant.id,
            request=schemas.TenantManualRenewalRequest(
                plan_id=lower.id, idempotency_key=uuid4().hex
            ),
            admin=sample.admin,
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) in (400, 409)
    db_session.expire_all()
    assert db_session.get(models.Tenant, sample.tenant.id).plan_id == sample.plan.id, (
        "Direct renewal accepted Essential with three active accounts; no scheduled downgrade was needed"
    )


def test_paid_grace_end_is_exclusive(sample):
    sample.tenant.grace_period_until = sample.tenant.subscription_end_date + timedelta(
        days=7
    )
    decision = CommercialDecisionEngine.evaluate_capability(
        sample.tenant,
        "clinical",
        "write_business",
        now=sample.tenant.grace_period_until,
        override_mode="enforce",
    )
    assert decision.allowed is False, (
        "Business write allowed at exact end-exclusive grace timestamp"
    )


def test_scribe_known_pre_dispatch_failure_does_not_spend_quota(
    db_session, sample, monkeypatch
):
    from backend.services.scribe_service import ScribeService

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    scribe = ScribeService()
    assert scribe.client is None
    with pytest.raises(ValueError, match="Groq API Key not configured"):
        scribe.analyze_dictation(
            "Synthetic non-patient text",
            tenant_id=sample.tenant.id,
            user_id=sample.user.id,
            session=db_session,
            idempotency_key="known-no-provider",
        )
    usage = AIQuotaService.get_window_usage(db_session, sample.tenant.id)
    admitted = (
        usage["reserved_count"] + usage["consumed_count"] + usage["uncertain_count"]
    )
    assert admitted == 0, (
        f"Known missing credentials never dispatches provider, but consumes/holds {admitted} quota unit: {usage}"
    )


@pytest.mark.asyncio
async def test_saved_tool_policy_blocks_executor_before_handler(
    db_session, async_db_session, sample, monkeypatch
):
    from unittest.mock import AsyncMock
    from backend.ai.executor import ToolExecutor

    sample.plan.ai_features = "[]"
    db_session.commit()
    executor = ToolExecutor(async_db_session, sample.user)
    handler = AsyncMock(wraps=executor.patient.search_patients)
    monkeypatch.setattr(executor.patient, "search_patients", handler)
    denied = await executor.execute("search_patients", {"query": "Synthetic"})
    assert denied["error_code"] == "tool_not_in_plan"
    handler.assert_not_called()
    sample.plan.ai_features = '["search_patients"]'
    db_session.commit()
    # A fresh authenticated user/session gets the persisted policy.
    async_db_session.expire_all()
    user = (
        await async_db_session.execute(
            select(models.User).where(models.User.id == sample.user.id)
        )
    ).scalar_one()
    authorized = ToolExecutor(async_db_session, user)
    allowed_handler = AsyncMock(wraps=authorized.patient.search_patients)
    monkeypatch.setattr(authorized.patient, "search_patients", allowed_handler)
    result = await authorized.execute(
        "search_patients", {"query": "No such synthetic record"}
    )
    assert result["success"] is True
    allowed_handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_quota_snapshot_is_read_only_without_window(
    db_session, async_db_session, sample
):
    from backend.models.ai_accounting import AIQuotaWindow

    snapshot = await build_tenant_entitlement_diagnostics(
        async_db_session, sample.tenant.id
    )
    assert snapshot["capacities"]["ai"]["remaining_quota"] == 10
    assert snapshot["capacities"]["ai"]["consumed_count"] == 0
    assert db_session.query(AIQuotaWindow).count() == 0


@pytest.mark.asyncio
async def test_payment_early_downgrade_preserves_current_period(
    db_session, async_db_session, sample
):
    lower = models.SubscriptionPlan(
        name="essential",
        display_name_ar="Synthetic",
        price=200,
        max_users=2,
        is_ai_enabled=True,
        ai_daily_limit=2,
        is_active=True,
    )
    db_session.add(lower)
    db_session.commit()
    old_end = sample.tenant.subscription_end_date
    await SubscriptionService.record_payment(
        async_db_session,
        schemas.SubscriptionPaymentCreate(
            tenant_id=sample.tenant.id,
            plan_id=lower.id,
            amount=200,
            payment_method="cash",
            idempotency_key="early-lower-receipt",
        ),
        sample.admin.username,
    )
    db_session.expire_all()
    tenant = db_session.get(models.Tenant, sample.tenant.id)
    assert tenant.plan_id == sample.plan.id
    assert tenant.future_plan_id == lower.id
    assert tenant.future_plan_start_date == old_end
    assert tenant.scheduled_downgrade_plan_id == lower.id
    assert tenant.subscription_end_date > old_end


@pytest.mark.asyncio
async def test_payment_changed_payload_replay_conflicts(
    db_session, async_db_session, sample
):
    from fastapi import HTTPException

    payload = schemas.SubscriptionPaymentCreate(
        tenant_id=sample.tenant.id,
        plan_id=sample.plan.id,
        amount=400,
        payment_method="cash",
        idempotency_key="one-receipt-identity",
    )
    first = await SubscriptionService.record_payment(
        async_db_session, payload, sample.admin.username
    )
    before = sample.tenant.subscription_end_date
    with pytest.raises(HTTPException) as error:
        await SubscriptionService.record_payment(
            async_db_session,
            payload.model_copy(update={"amount": 800}),
            sample.admin.username,
        )
    assert error.value.status_code == 409
    assert (
        db_session.query(models.SubscriptionPayment).filter_by(id=first.id).one().amount
        == 400
    )
    assert sample.tenant.subscription_end_date == before


@pytest.mark.asyncio
async def test_receipt_then_renewal_same_operation_never_grants_twice(
    async_db_session, sample
):
    key = "same-paid-operation-across-adapters"
    receipt = schemas.SubscriptionPaymentCreate(
        tenant_id=sample.tenant.id,
        plan_id=sample.plan.id,
        amount=400,
        payment_method="cash",
        idempotency_key=key,
    )
    await SubscriptionService.record_payment(
        async_db_session, receipt, sample.admin.username
    )
    tenant = (
        await async_db_session.execute(
            select(models.Tenant).where(models.Tenant.id == sample.tenant.id)
        )
    ).scalar_one()
    end = tenant.subscription_end_date
    result = await renew_subscription(
        async_db_session,
        tenant_id=tenant.id,
        request=schemas.TenantManualRenewalRequest(
            idempotency_key=key, plan_id=sample.plan.id
        ),
        admin=sample.admin,
    )
    await async_db_session.refresh(tenant)
    assert result["is_idempotent_duplicate"] is True
    assert tenant.subscription_end_date == end


@pytest.mark.asyncio
async def test_concurrent_manual_receipt_replays_grant_once_on_postgres(pg_case):
    import asyncio
    from backend.services.subscription_calendar import add_calendar_months

    engine = create_async_engine(URL.replace("postgresql://", "postgresql+asyncpg://"))
    before = pg_case.tenant.subscription_end_date

    async def submit():
        async with AsyncSession(engine, expire_on_commit=False) as db:
            receipt = schemas.SubscriptionPaymentCreate(
                tenant_id=pg_case.tenant.id,
                plan_id=pg_case.plans["professional"].id,
                amount=400,
                payment_method="cash",
                idempotency_key="concurrent-one-receipt",
            )
            result = await SubscriptionService.record_payment(
                db, receipt, pg_case.admin.username
            )
            return result.id

    try:
        ids = await asyncio.gather(*(submit() for _ in range(3)))
        assert len(set(ids)) == 1
        pg_case.db.expire_all()
        assert (
            pg_case.db.query(models.SubscriptionPayment)
            .filter_by(tenant_id=pg_case.tenant.id)
            .count()
            == 1
        )
        assert (
            pg_case.db.get(models.Tenant, pg_case.tenant.id).subscription_end_date
            == add_calendar_months(before)[0]
        )
    finally:
        await engine.dispose()


def test_ai_quota_http_snapshot_preserves_ledger_fields(client, db_session, sample):
    AIQuotaService.reserve_quota(
        db_session,
        sample.tenant.id,
        sample.user.id,
        "ai_chat",
        "Synthetic ledger snapshot",
    )
    token = create_access_token(
        data={"sub": sample.admin.username, "role": "super_admin", "tenant_id": None}
    )
    response = client.get(
        f"/api/v1/admin/tenants/{sample.tenant.id}/entitlements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    quota = response.json()["data"]["capacities"]["ai"]
    assert quota["reserved_count"] == 1
    assert quota["remaining_quota"] == 9
    assert quota["end_utc"].endswith("Z")


@pytest.mark.asyncio
async def test_demo_analysis_and_chat_never_spend_provider_quota(
    db_session, async_db_session, sample, monkeypatch
):
    from unittest.mock import AsyncMock
    from backend.services.ai_service import AIService
    from backend.ai.agent.core import get_agent

    agent = get_agent()
    monkeypatch.setattr(agent, "mock_mode", True)
    transport = AsyncMock()
    monkeypatch.setattr(
        agent.client.chat.completions, "create", transport
    ) if agent.client else None
    service = AIService(async_db_session, sample.user)
    await service.analyze_direct(
        "Synthetic demo analysis", idempotency_key="demo-analysis-nonbillable"
    )
    await service.process_query(
        "Please provide synthetic general dental advice",
        idempotency_key="demo-chat-nonbillable",
    )
    usage = AIQuotaService.get_window_usage(db_session, sample.tenant.id)
    assert (
        usage["consumed_count"] + usage["reserved_count"] + usage["uncertain_count"]
        == 0
    )
    transport.assert_not_called()


@pytest.mark.asyncio
async def test_future_paid_plan_is_effective_without_waiting_for_worker(
    db_session, async_db_session, sample
):
    from sqlalchemy.orm import selectinload
    from backend.services.entitlement_service import EntitlementService
    from backend.services.account_admission_service import AccountAdmissionService

    business = models.SubscriptionPlan(
        name="business",
        display_name_ar="Synthetic Business",
        price=1000,
        max_users=15,
        is_ai_enabled=True,
        ai_daily_limit=30,
        features='{"clinical":true,"ai_insights":true}',
        is_active=True,
    )
    db_session.add(business)
    db_session.flush()
    sample.tenant.future_plan_id = business.id
    sample.tenant.future_plan_start_date = datetime.utcnow() - timedelta(hours=1)
    sample.tenant.subscription_status = "trial"
    db_session.commit()
    tenant = (
        await async_db_session.execute(
            select(models.Tenant)
            .where(models.Tenant.id == sample.tenant.id)
            .options(
                selectinload(models.Tenant.subscription_plan),
                selectinload(models.Tenant.future_plan),
            )
        )
    ).scalar_one()
    assert (
        EntitlementService.evaluate_tenant_entitlements(
            tenant, override_mode="enforce"
        ).plan_id
        == business.id
    )
    assert AccountAdmissionService.resolve_effective_max_users(tenant) == 15
    snapshot = await build_tenant_entitlement_diagnostics(async_db_session, tenant.id)
    assert snapshot["plan_id"] == business.id
    assert snapshot["capacities"]["ai"]["daily_limit"] == 30
    assert snapshot["capacities"]["seats"]["limit"] == 15


def test_enforced_manual_payment_without_identity_is_denied_before_mutation(
    client, db_session, sample
):
    token = create_access_token(
        data={"sub": sample.admin.username, "role": "super_admin", "tenant_id": None}
    )
    before = sample.tenant.subscription_end_date
    response = client.post(
        "/api/v1/admin/subscriptions/payments",
        json={
            "tenant_id": sample.tenant.id,
            "plan_id": sample.plan.id,
            "amount": 400,
            "payment_method": "cash",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert db_session.query(models.SubscriptionPayment).count() == 0
    db_session.refresh(sample.tenant)
    assert sample.tenant.subscription_end_date == before


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", ["receipt", "renewal"])
async def test_first_paid_month_anchors_to_trial_end_not_signup(
    db_session, async_db_session, sample, monkeypatch, adapter
):
    # Worked contract: Nov 5 + 14-day trial = Nov 19; one paid month ends Dec 19.
    # A registration-day anchor of 5 must not truncate that paid month to Dec 5.
    instant = datetime(2026, 11, 5, 12)

    class PaymentClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.replace(tzinfo=timezone.utc) if tz else instant

    monkeypatch.setattr(
        SubscriptionService, "_utc_now_naive", staticmethod(lambda: instant)
    )
    monkeypatch.setattr(
        "backend.services.subscription_renewal_service.datetime", PaymentClock
    )
    sample.tenant.subscription_status = "trial"
    sample.tenant.subscription_start_date = instant
    sample.tenant.subscription_end_date = datetime(2026, 11, 19, 12)
    sample.tenant.billing_day_anchor = 5
    db_session.commit()
    if adapter == "receipt":
        await SubscriptionService.record_payment(
            async_db_session,
            schemas.SubscriptionPaymentCreate(
                tenant_id=sample.tenant.id,
                plan_id=sample.plan.id,
                amount=400,
                payment_method="cash",
            ),
            sample.admin.username,
        )
    else:
        await renew_subscription(
            async_db_session,
            tenant_id=sample.tenant.id,
            request=schemas.TenantManualRenewalRequest(
                plan_id=sample.plan.id, idempotency_key="first-full-month"
            ),
            admin=sample.admin,
        )
    db_session.expire_all()
    tenant = db_session.get(models.Tenant, sample.tenant.id)
    assert tenant.future_plan_start_date == datetime(2026, 11, 19, 12)
    assert tenant.subscription_end_date == datetime(2026, 12, 19, 12)
    assert tenant.grace_period_until == datetime(2026, 12, 26, 12)
    assert tenant.billing_day_anchor == 19


@pytest.mark.asyncio
async def test_observe_mode_does_not_enforce_commercial_tool_policy(
    db_session, async_db_session, sample, monkeypatch
):
    from unittest.mock import AsyncMock
    from backend.ai.executor import ToolExecutor

    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "observe")
    sample.plan.ai_features = "[]"
    db_session.commit()
    executor = ToolExecutor(async_db_session, sample.user)
    handler = AsyncMock(wraps=executor.patient.search_patients)
    monkeypatch.setattr(executor.patient, "search_patients", handler)
    result = await executor.execute("search_patients", {"query": "Synthetic"})
    assert result["success"] is True, result
    handler.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("assignment", ["current", "future"])
async def test_catalog_retirement_does_not_revoke_existing_renewable_contract(
    db_session, async_db_session, sample, assignment
):
    original_end = sample.tenant.subscription_end_date
    if assignment == "current":
        contract = sample.plan
    else:
        contract = models.SubscriptionPlan(
            name="business",
            display_name_ar="Synthetic retired paid contract",
            price=1000,
            max_users=15,
            is_ai_enabled=True,
            ai_daily_limit=30,
            is_active=False,
        )
        db_session.add(contract)
        db_session.flush()
        sample.tenant.future_plan_id = contract.id
        sample.tenant.future_plan_start_date = datetime.utcnow() - timedelta(hours=1)
    contract.is_active = False
    db_session.commit()
    await renew_subscription(
        async_db_session,
        tenant_id=sample.tenant.id,
        request=schemas.TenantManualRenewalRequest(
            plan_id=contract.id, idempotency_key="renew-valid-retired-contract"
        ),
        admin=sample.admin,
    )
    db_session.expire_all()
    tenant = db_session.get(models.Tenant, sample.tenant.id)
    assert tenant.subscription_end_date > original_end
    assert tenant.is_active is True
    assert tenant.plan_id == contract.id
    assert db_session.get(models.SubscriptionPlan, contract.id).is_active is False


@pytest.mark.asyncio
async def test_explicit_missing_trial_reference_preview_conflicts_after_assignment(
    async_db_session, sample
):
    from fastapi import HTTPException

    # A preview that observed no reference cannot overwrite a newly assigned policy.
    before = await SubscriptionService.get_trial_policy(async_db_session)
    assert before.trial_plan_id == sample.plan.id
    with pytest.raises(HTTPException) as error:
        await SubscriptionService.update_trial_policy(
            async_db_session,
            schemas.TrialPolicyUpdateRequest(
                trial_plan_name="professional",
                trial_duration_days=21,
                expected_trial_plan_id=None,
                expected_trial_duration_days=14,
                reason="Synthetic stale missing-reference preview",
            ),
            sample.admin,
        )
    assert error.value.status_code == 409
    after = await SubscriptionService.get_trial_policy(async_db_session)
    assert after.trial_duration_days == 14
    assert after.trial_plan_id == sample.plan.id


@pytest.mark.asyncio
async def test_provider_reference_cannot_bypass_operation_payload_conflict(
    async_db_session, sample
):
    from fastapi import HTTPException

    receipt = schemas.SubscriptionPaymentCreate(
        tenant_id=sample.tenant.id,
        plan_id=sample.plan.id,
        amount=400,
        payment_method="cash",
        provider="synthetic-manual",
        provider_payment_id="one-external-receipt",
        idempotency_key="one-external-receipt-operation",
    )
    first = await SubscriptionService.record_payment(
        async_db_session, receipt, sample.admin.username
    )
    for changed in (
        {"notes": "Changed body"},
        {"idempotency_key": "different-identity-same-receipt"},
    ):
        with pytest.raises(HTTPException) as error:
            await SubscriptionService.record_payment(
                async_db_session,
                receipt.model_copy(update=changed),
                sample.admin.username,
            )
        assert error.value.status_code == 409
    same = await SubscriptionService.record_payment(
        async_db_session, receipt, sample.admin.username
    )
    assert same.id == first.id
