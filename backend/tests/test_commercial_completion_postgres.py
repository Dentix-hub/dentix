"""Real PostgreSQL serialization gates; synthetic data in an explicit test DB only."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.services.ai_quota_service import AIQuotaService
from backend.services.commercial_action_service import CommercialActionService


def pg_url():
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("Explicit PostgreSQL TEST_DATABASE_URL required")
    assert "test" in (make_url(url).database or ""), "Use an isolated test database"
    return url


def seed(engine):
    suffix = uuid4().hex
    with Session(engine, expire_on_commit=False) as db:
        plan = models.SubscriptionPlan(
            name=f"completion_{suffix}",
            display_name_ar="Synthetic",
            price=200,
            max_users=2,
            is_ai_enabled=True,
            ai_daily_limit=1,
        )
        db.add(plan)
        db.flush()
        tenant = models.Tenant(
            name=f"Synthetic {suffix}",
            plan_id=plan.id,
            plan=plan.name,
            is_active=True,
            subscription_status="active",
        )
        db.add(tenant)
        db.flush()
        admin = models.User(
            username=f"completion_{suffix}",
            hashed_password="synthetic-test-only",
            role="super_admin",
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        return tenant.id, admin


def test_postgres_duplicate_acquisition_has_one_dispatch_owner():
    engine = create_engine(pg_url())
    try:
        tenant_id, actor = seed(engine)

        def acquire(_):
            with Session(engine, expire_on_commit=False) as db:
                row = AIQuotaService.reserve_quota(
                    db,
                    tenant_id,
                    actor.id,
                    "ai_chat",
                    {"text": "synthetic"},
                    idempotency_key="same-request",
                )
                return not getattr(row, "is_replay", False)

        with ThreadPoolExecutor(max_workers=8) as pool:
            owners = list(pool.map(acquire, range(8)))
        assert sum(owners) == 1
        with Session(engine) as db:
            usage = AIQuotaService.get_window_usage(db, tenant_id)
            assert usage["admitted_count"] == 1
            assert usage["remaining_quota"] == 0
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_postgres_new_security_disable_wins_over_racing_old_undo():
    url = pg_url()
    engine = create_engine(url)
    tenant_id, actor = seed(engine)
    engine.dispose()
    async_engine = create_async_engine(
        url.replace("postgresql://", "postgresql+asyncpg://")
    )
    try:
        async with AsyncSession(async_engine, expire_on_commit=False) as db:
            await CommercialActionService.suspend_tenant(
                db,
                tenant_id,
                schemas.TenantCommercialActionRequest(
                    reason="Synthetic commercial suspension"
                ),
                actor,
            )
            audit = (
                await db.execute(
                    select(models.AuditLog).where(
                        models.AuditLog.tenant_id == tenant_id,
                        models.AuditLog.action == "TENANT_COMMERCIAL_SUSPEND",
                    )
                )
            ).scalar_one()
            audit_id = audit.id

        async def disable():
            async with AsyncSession(async_engine, expire_on_commit=False) as db:
                await CommercialActionService.security_disable_tenant(
                    db,
                    tenant_id,
                    schemas.TenantCommercialActionRequest(
                        reason="New security incident"
                    ),
                    actor,
                )

        async def reverse():
            async with AsyncSession(async_engine, expire_on_commit=False) as db:
                try:
                    await CommercialActionService.reverse_policy_action(
                        db,
                        schemas.PolicyReversalRequest(
                            audit_log_id=audit_id, reason="Reverse old commercial event"
                        ),
                        actor,
                    )
                except HTTPException as exc:
                    assert exc.status_code == 409

        await asyncio.gather(disable(), reverse())
        async with AsyncSession(async_engine) as db:
            tenant = (
                await db.execute(
                    select(models.Tenant).where(models.Tenant.id == tenant_id)
                )
            ).scalar_one()
            assert tenant.is_active is False
    finally:
        await async_engine.dispose()
