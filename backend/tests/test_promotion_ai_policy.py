"""Promotion regression: persisted AI overrides must apply on real async PostgreSQL."""

from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, selectinload, sessionmaker

from backend import models
from backend.services.ai_service import AIService
from backend.services.commercial_ai_guard import (
    async_evaluate_commercial_ai_access,
    evaluate_commercial_ai_access,
)
from backend.routers.admin_tenants import assign_plan_to_tenant, schedule_tenant_downgrade
from fastapi import HTTPException
from backend.services.ai_quota_service import (
    AIQuotaService, ScopeMismatchError, ReservationNotFoundError,
    isolated_accounting_session,
)
from backend.core.tenancy import set_current_tenant_id, clear_tenant_context


@pytest.fixture
def policy_database(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("Explicit isolated PostgreSQL TEST_DATABASE_URL required")
    assert "test" in (make_url(url).database or ""), "Test database only"
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")
    monkeypatch.setenv("AI_DISABLED", "false")
    schema = "promotion_policy_test_" + uuid4().hex
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        models.Base.metadata.create_all(scoped)
        with Session(scoped) as db:
            plan = models.SubscriptionPlan(
                name="professional", display_name_ar="Synthetic", price=400,
                max_users=5, is_active=True, is_ai_enabled=True, ai_daily_limit=10,
                features='["clinical", "billing", "ai_insights"]',
            )
            db.add(plan)
            db.flush()
            tenant = models.Tenant(
                name="Synthetic policy clinic", plan="professional", plan_id=plan.id,
                is_active=True, subscription_status="active",
                subscription_end_date=datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(days=20),
            )
            db.add(tenant)
            db.commit()
            tenant_id = tenant.id
        yield SimpleNamespace(url=url, schema=schema, engine=scoped, tenant_id=tenant_id)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
        engine.dispose()


async def load_tenant(db, tenant_id):
    return (await db.execute(
        select(models.Tenant).where(models.Tenant.id == tenant_id)
        .options(selectinload(models.Tenant.subscription_plan))
    )).scalar_one()


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expired,other_tenant,denied", [
    ("deny", False, False, True),
    ("allow", False, False, False),
    ("inherit", False, False, False),
    ("deny", True, False, False),
    ("deny", False, True, False),
])
async def test_async_guard_agrees_with_persisted_policy(
    policy_database, value, expired, other_tenant, denied
):
    case = policy_database
    with Session(case.engine) as db:
        owner_id = case.tenant_id
        if other_tenant:
            other = models.Tenant(name="Synthetic other policy clinic", is_active=True)
            db.add(other)
            db.flush()
            owner_id = other.id
        db.add(models.CommercialTenantOverride(
            tenant_id=owner_id, capability_key="ai_insights", override_value=value,
            reason="Synthetic promotion verification",
            expires_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1))
            if expired else None,
        ))
        db.commit()
        tenant = db.get(models.Tenant, case.tenant_id)
        sync_denial = evaluate_commercial_ai_access(tenant, db_session=db)
        assert bool(sync_denial) is denied
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    try:
        async with AsyncSession(engine) as db:
            tenant = await load_tenant(db, case.tenant_id)
            actual = await async_evaluate_commercial_ai_access(tenant, db=db)
            assert bool(actual) is denied
            if denied:
                assert actual[0] == "plan_restricted"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_async_deny_precedes_reservation_and_provider(policy_database, monkeypatch):
    case = policy_database
    with Session(case.engine) as db:
        db.add(models.CommercialTenantOverride(
            tenant_id=case.tenant_id, capability_key="ai_insights", override_value="deny",
            reason="Synthetic provider boundary verification",
        ))
        db.commit()
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    try:
        async with AsyncSession(engine) as db:
            tenant = await load_tenant(db, case.tenant_id)
            user = SimpleNamespace(id=123, tenant_id=tenant.id, tenant=tenant, role="admin")
            service = AIService(db, user)
            reserve = AsyncMock(side_effect=AssertionError("Denied request reached quota reservation"))
            provider = AsyncMock(side_effect=AssertionError("Denied request reached provider"))
            monkeypatch.setattr(service, "_reserve_quota", reserve)
            monkeypatch.setattr(service.agent, "_call_llm_safe", provider)
            response = await service.analyze_direct("Synthetic authorization probe")
            assert response.success is False
            assert response.error == "plan_restricted"
            reserve.assert_not_called()
            provider.assert_not_called()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_direct_assignment_cannot_activate_lower_tier_early(policy_database):
    case = policy_database
    with Session(case.engine, expire_on_commit=False) as db:
        lower = models.SubscriptionPlan(
            name="essential", display_name_ar="Synthetic lower", price=200,
            max_users=2, is_active=True, is_ai_enabled=True, ai_daily_limit=2,
        )
        actor = models.User(username="synthetic_operator", hashed_password="synthetic",
                            role="super_admin", is_active=True)
        db.add_all([lower, actor])
        db.commit()
        tenant = db.get(models.Tenant, case.tenant_id)
        original = (tenant.plan_id, tenant.subscription_end_date)
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            with pytest.raises(HTTPException) as rejected:
                await assign_plan_to_tenant(case.tenant_id, lower.id, current_user=actor, db=db)
            assert rejected.value.status_code == 409
            await db.rollback()
            tenant = await load_tenant(db, case.tenant_id)
            assert (tenant.plan_id, tenant.subscription_end_date) == original
            await schedule_tenant_downgrade(case.tenant_id, lower.id, current_user=actor, db=db)
            await db.refresh(tenant)
            assert (tenant.plan_id, tenant.subscription_end_date) == original
            assert tenant.scheduled_downgrade_plan_id == lower.id
            audit = (await db.execute(select(models.AuditLog).where(
                models.AuditLog.tenant_id == tenant.id,
                models.AuditLog.action == "SUBSCRIPTION_SCHEDULE_DOWNGRADE",
            ))).scalar_one()
            assert audit.old_value == "scheduled_downgrade=None"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_isolated_ai_accounting_honors_force_rls_and_tenant_scope(policy_database, monkeypatch):
    case = policy_database
    role = "ai_review_" + uuid4().hex
    with case.engine.begin() as connection:
        connection.exec_driver_sql(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA {case.schema} TO {role}")
        connection.exec_driver_sql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {case.schema} TO {role}")
        connection.exec_driver_sql(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {case.schema} TO {role}")
        for table in ("ai_quota_windows", "ai_reservations"):
            connection.exec_driver_sql(f"ALTER TABLE {case.schema}.{table} ENABLE ROW LEVEL SECURITY")
            connection.exec_driver_sql(f"ALTER TABLE {case.schema}.{table} FORCE ROW LEVEL SECURITY")
            connection.exec_driver_sql(
                f"CREATE POLICY tenant_scope ON {case.schema}.{table} FOR ALL "
                "USING (tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer) "
                "WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer)"
            )
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
        pool_size=1, max_overflow=0,
    )

    def restricted_role(connection, record):
        cursor = connection.cursor()
        cursor.execute(f"SET ROLE {role}")
        cursor.close()

    event.listen(engine.sync_engine, "connect", restricted_role)
    sync_engine = create_engine(case.url, execution_options={"schema_translate_map": {None: case.schema}})
    event.listen(sync_engine, "connect", restricted_role)
    monkeypatch.setattr("backend.services.ai_quota_service._SyncSessionLocal", sessionmaker(bind=sync_engine))
    token = set_current_tenant_id(case.tenant_id)
    try:
        async with AsyncSession(engine) as db:
            reservation = await AIQuotaService.async_reserve_quota(
                db, case.tenant_id, None, "ai_chat", {"text": "Synthetic RLS probe"},
                idempotency_key="rls-one-request",
            )
            assert reservation.units == 1
            completed = await AIQuotaService.async_finalize_reservation(
                db, reservation.reservation_id, "CONSUMED",
            )
            assert completed.status == "CONSUMED"
            with pytest.raises(ScopeMismatchError):
                await AIQuotaService.async_reserve_quota(
                    db, case.tenant_id + 10000, None, "ai_chat", {"text": "Cross-tenant probe"}
                )
            other_token = set_current_tenant_id(case.tenant_id + 10000)
            try:
                with pytest.raises(ReservationNotFoundError):
                    await AIQuotaService.async_finalize_reservation(db, reservation.reservation_id, "CONSUMED")
            finally:
                clear_tenant_context(tenant_token=other_token)
        with isolated_accounting_session(tenant_id=case.tenant_id) as sync_session:
            assert sync_session.scalar(text("SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user")) is False
            second = AIQuotaService.reserve_quota(
                sync_session, case.tenant_id, None, "scribe", "Synthetic synchronous quota probe"
            )
            AIQuotaService.finalize_reservation(sync_session, second.reservation_id, "RELEASED")
            assert sync_session.get(models.AIQuotaWindow, second.window_id).consumed_count == 1
        async with AsyncSession(engine) as reused:
            assert await reused.scalar(text("SELECT NULLIF(current_setting('rls.tenant_id', true), '')")) is None
            assert await reused.scalar(select(models.AIQuotaWindow.id)) is None
    finally:
        clear_tenant_context(tenant_token=token)
        await engine.dispose()
        sync_engine.dispose()
        with case.engine.begin() as connection:
            connection.exec_driver_sql(f"REVOKE ALL ON ALL TABLES IN SCHEMA {case.schema} FROM {role}")
            connection.exec_driver_sql(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {case.schema} FROM {role}")
            connection.exec_driver_sql(f"REVOKE ALL ON SCHEMA {case.schema} FROM {role}")
            connection.exec_driver_sql(f"DROP ROLE {role}")


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["chat", "analysis"])
async def test_accounting_failure_does_not_return_internal_details(policy_database, monkeypatch, operation):
    case = policy_database
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    try:
        async with AsyncSession(engine) as db:
            tenant = await load_tenant(db, case.tenant_id)
            user = SimpleNamespace(id=123, tenant_id=tenant.id, tenant=tenant, role="admin")
            service = AIService(db, user)
            private_detail = "Private SQL parameters (tenant_id=999, credential=synthetic)"
            if operation == "chat":
                monkeypatch.setattr(service, "_reserve_quota", AsyncMock(side_effect=RuntimeError(private_detail)))
                response = await service.process_query("Synthetic technical verification request")
            else:
                monkeypatch.setattr(service, "_reserve_quota", AsyncMock(return_value=SimpleNamespace(
                    reservation_id="synthetic", status="RESERVED", is_replay=False,
                )))
                monkeypatch.setattr(service, "_finalize_reservation", AsyncMock())
                monkeypatch.setattr(service.agent, "mock_mode", False)
                monkeypatch.setattr(service.agent, "_call_llm_safe", AsyncMock(side_effect=RuntimeError(private_detail)))
                response = await service.analyze_direct("Synthetic technical verification request")
            assert response.success is False
            assert response.error == ("internal_server_error" if operation == "chat" else "analysis_failed")
            assert private_detail not in response.message
            assert "credential" not in response.message
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("future_state", ["none", "pending", "started"])
async def test_assignment_preserves_future_payment_and_allows_plain_upgrade(policy_database, future_state):
    case = policy_database
    with Session(case.engine, expire_on_commit=False) as db:
        target = models.SubscriptionPlan(
            name="business", display_name_ar="Synthetic higher", price=1000,
            max_users=15, is_active=True, is_ai_enabled=True, ai_daily_limit=30,
        )
        actor = models.User(username="synthetic_assignment_operator", hashed_password="synthetic",
                            role="super_admin", is_active=True)
        db.add_all([target, actor])
        tenant = db.get(models.Tenant, case.tenant_id)
        before = (tenant.plan_id, tenant.subscription_end_date)
        if future_state != "none":
            tenant.future_plan_id = tenant.plan_id
            tenant.future_plan_start_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                days=1 if future_state == "pending" else -1
            )
        db.commit()
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            if future_state == "none":
                await assign_plan_to_tenant(case.tenant_id, target.id, current_user=actor, db=db)
                tenant = await load_tenant(db, case.tenant_id)
                assert tenant.plan_id == target.id
                assert tenant.subscription_end_date == before[1]
            else:
                with pytest.raises(HTTPException) as rejected:
                    await assign_plan_to_tenant(case.tenant_id, target.id, current_user=actor, db=db)
                assert rejected.value.status_code == 409
                await db.rollback()
                tenant = await load_tenant(db, case.tenant_id)
                assert (tenant.plan_id, tenant.subscription_end_date) == before
                assert tenant.future_plan_id == before[0]
    finally:
        await engine.dispose()
