"""Real PostgreSQL FORCE-RLS and tenant isolation gate for procedure_chart_styles."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import models
from backend.database import AsyncSessionLocal, RlsContext

TENANT_A = 99681
TENANT_B = 99682


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_A) is not None:
                return
            tenant_a = models.Tenant(id=TENANT_A, name="Styles RLS A")
            tenant_b = models.Tenant(id=TENANT_B, name="Styles RLS B")
            db.add_all([tenant_a, tenant_b])
            await db.flush()

            # Procedures for tenants
            p_a = models.Procedure(id=996811, tenant_id=TENANT_A, name="حشو عصب", price=250.0)
            p_b = models.Procedure(id=996821, tenant_id=TENANT_B, name="حشو عصب", price=300.0)
            db.add_all([p_a, p_b])
            await db.commit()


@pytest.mark.asyncio
async def test_procedure_chart_styles_table_has_force_rls_enabled():
    await _seed()
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            result = await db.execute(
                text(
                    """
                    SELECT c.relrowsecurity, c.relforcerowsecurity
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'procedure_chart_styles'
                      AND n.nspname = current_schema()
                    """
                )
            )
            row = result.first()
            assert row is not None, "procedure_chart_styles table missing from pg_class"
            assert row.relrowsecurity is True, "procedure_chart_styles must have rowsecurity enabled"
            assert row.relforcerowsecurity is True, "procedure_chart_styles must have forcerowsecurity enabled"


@pytest.mark.asyncio
async def test_procedure_chart_styles_tenant_isolation_and_uniqueness():
    await _seed()
    # 1. Insert style for Tenant A
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        style_a = models.ProcedureChartStyle(
            tenant_id=TENANT_A,
            procedure_name="حشو عصب",
            template="ENDO_RCT",
            color_key="teal",
        )
        session.add(style_a)
        await session.commit()

        # Query under Tenant A: sees it
        res_a = await session.execute(
            select(models.ProcedureChartStyle).where(
                models.ProcedureChartStyle.procedure_name == "حشو عصب"
            )
        )
        found_a = res_a.scalars().all()
        assert len(found_a) == 1
        assert found_a[0].color_key == "teal"

    # 2. Query under Tenant B: RLS isolates it (returns 0 rows)
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_B)) as session:
        res_b = await session.execute(
            select(models.ProcedureChartStyle).where(
                models.ProcedureChartStyle.procedure_name == "حشو عصب"
            )
        )
        found_b = res_b.scalars().all()
        assert len(found_b) == 0

        # Tenant B can insert own style for same procedure name (unique constraint is tenant-scoped)
        style_b = models.ProcedureChartStyle(
            tenant_id=TENANT_B,
            procedure_name="حشو عصب",
            template="ENDO_RCT",
            color_key="purple",
        )
        session.add(style_b)
        await session.commit()

        res_b2 = await session.execute(
            select(models.ProcedureChartStyle).where(
                models.ProcedureChartStyle.procedure_name == "حشو عصب"
            )
        )
        assert len(res_b2.scalars().all()) == 1

    # 3. Duplicate insert under Tenant A fails uniqueness constraint
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        dup_style = models.ProcedureChartStyle(
            tenant_id=TENANT_A,
            procedure_name="حشو عصب",
            template="ENDO_RCT",
            color_key="orange",
        )
        session.add(dup_style)
        with pytest.raises((IntegrityError, DBAPIError)):
            await session.commit()
