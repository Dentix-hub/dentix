"""Independent PostgreSQL transactions prove setup serialization and rollback."""

import asyncio
import os
from uuid import uuid4
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, func, event
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from backend import models, schemas
from backend.services.catalog_setup_service import (
    preview_catalog_setup,
    apply_catalog_setup,
)


@pytest.fixture
def isolated_catalog():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("Isolated PostgreSQL test database required")
    assert "test" in (make_url(url).database or ""), "Test database only"
    schema = "catalog_setup_test_" + uuid4().hex
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE SCHEMA {schema}")
    scoped = engine.execution_options(schema_translate_map={None: schema})
    models.Base.metadata.create_all(scoped)
    with Session(scoped, expire_on_commit=False) as db:
        plan = models.SubscriptionPlan(
            name="pro", display_name_ar="Synthetic legacy", price=1000, is_active=True
        )
        db.add(plan)
        db.flush()
        tenant = models.Tenant(
            name="Synthetic history",
            plan_id=plan.id,
            plan="pro",
            subscription_end_date=datetime(2027, 1, 31),
        )
        actor = models.User(
            username="catalog_admin",
            role="super_admin",
            hashed_password="synthetic",
            is_active=True,
        )
        db.add_all([tenant, actor])
        db.commit()
        yield SimpleNamespace(
            url=url,
            schema=schema,
            engine=scoped,
            actor=actor,
            tenant_id=tenant.id,
            plan_id=plan.id,
        )
    with engine.begin() as conn:
        conn.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
    engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_postgres_setup_atomicity_and_duplicate_confirmations(
    isolated_catalog, failure
):
    c = isolated_catalog
    engine = create_async_engine(
        c.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: c.schema}},
    )
    try:
        async with AsyncSession(engine) as db:
            before = await preview_catalog_setup(db)
        request = schemas.CatalogSetupRequest(
            expected_snapshot=before["snapshot"],
            reason="Owner approved synthetic setup",
        )

        async def apply():
            async with AsyncSession(engine, expire_on_commit=False) as db:
                try:
                    await apply_catalog_setup(db, request, c.actor)
                    return 200
                except HTTPException as err:
                    return err.status_code

        if failure:

            def fail_audit(conn, cursor, statement, parameters, context, executemany):
                if "audit_logs" in statement and "COMMERCIAL_CATALOG_SETUP" in str(
                    parameters
                ):
                    raise RuntimeError("Synthetic audit storage failure")

            event.listen(engine.sync_engine, "before_cursor_execute", fail_audit)
            with pytest.raises(RuntimeError, match="Synthetic audit storage failure"):
                await apply()
            event.remove(engine.sync_engine, "before_cursor_execute", fail_audit)
        else:
            assert sorted(await asyncio.gather(apply(), apply())) == [200, 409]
        with Session(c.engine) as db:
            assert db.scalar(select(func.count(models.SubscriptionPlan.id))) == (
                1 if failure else 4
            )
            assert db.scalar(select(func.count(models.SystemSetting.key))) == (
                0 if failure else 2
            )
            assert db.scalar(
                select(func.count(models.AuditLog.id)).where(
                    models.AuditLog.action == "COMMERCIAL_CATALOG_SETUP"
                )
            ) == (0 if failure else 1)
            tenant = db.get(models.Tenant, c.tenant_id)
            assert (tenant.plan_id, tenant.subscription_end_date) == (
                c.plan_id,
                datetime(2027, 1, 31),
            )
    finally:
        await engine.dispose()
