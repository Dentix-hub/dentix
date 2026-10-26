"""Tests for Default Procedure Catalog and Copy-on-Registration (PR3).

Verifies:
1. Parity invariant: Any catalog entry with template not in (NONE, MARKER) must exist in _RAW_PROCEDURE_ALLOWLIST.
2. New clinic registration gets the full 34 catalog procedures at price 0 and corresponding chart styles.
3. Second clinic registration gets its own isolated rows.
4. Registration failure atomically rolls back the procedures and chart styles.
5. Backfill script dry-run leaves rows unchanged; apply sets code/category without touching price.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.clinical.legacy_mapping import _RAW_PROCEDURE_ALLOWLIST
from backend.data.default_procedures import (
    DEFAULT_PROCEDURE_CATALOG,
    VALID_PROCEDURE_CATEGORIES,
)
from backend.scripts.backfill_procedure_catalog import run_backfill


# ---------------------------------------------------------------------------
# Invariant & Parity Tests
# ---------------------------------------------------------------------------

def test_catalog_entries_count_and_categories():
    """Ensure catalog contains exactly 34 classified procedures and valid categories."""
    assert len(DEFAULT_PROCEDURE_CATALOG) == 34
    codes = set()
    names = set()
    for entry in DEFAULT_PROCEDURE_CATALOG:
        assert entry.category in VALID_PROCEDURE_CATEGORIES
        assert entry.code.isupper()
        assert entry.code not in codes, f"Duplicate code: {entry.code}"
        assert entry.name not in names, f"Duplicate name: {entry.name}"
        assert entry.default_price == Decimal("0.00")
        assert entry.name_ar
        assert entry.name_en
        codes.add(entry.code)
        names.add(entry.name)


def test_catalog_allowlist_parity_for_renderable_templates():
    """Fail if any catalog entry's name is missing from the allowlist when template is not NONE/MARKER."""
    for entry in DEFAULT_PROCEDURE_CATALOG:
        if entry.chart_template not in ("NONE", "MARKER"):
            assert (
                entry.name in _RAW_PROCEDURE_ALLOWLIST
            ), f"Renderable procedure '{entry.name}' (template={entry.chart_template}) missing from legacy mapping allowlist"


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_tenant_gets_full_catalog_at_price_zero(async_db_session: AsyncSession):
    """Registering a new clinic creates all 34 procedures at price 0 and chart styles."""
    from backend import crud

    # Create plan if needed
    plan_res = await async_db_session.execute(select(models.SubscriptionPlan).filter_by(name="Trial"))
    plan = plan_res.scalars().first()
    if not plan:
        plan = models.SubscriptionPlan(
            name="Trial",
            display_name_ar="تجريبي",
            is_default=True,
            price=Decimal("0.00"),
        )
        async_db_session.add(plan)
        await async_db_session.commit()

    # Create tenant
    tenant = models.Tenant(name="Catalog Clinic A", is_active=True, plan_id=plan.id)
    async_db_session.add(tenant)
    await async_db_session.flush()

    # Seed procedures copy-on-registration
    created = await crud.seed_tenant_default_procedures(async_db_session, tenant.id)
    await async_db_session.commit()

    assert len(created) == 34

    # Query procedures for tenant
    stmt = select(models.Procedure).where(models.Procedure.tenant_id == tenant.id)
    res = await async_db_session.execute(stmt)
    tenant_procs = res.scalars().all()
    assert len(tenant_procs) == 34
    for proc in tenant_procs:
        assert proc.price == Decimal("0.00") or float(proc.price) == 0.0
        assert proc.code is not None
        assert proc.category in VALID_PROCEDURE_CATEGORIES

    # Query styles for tenant
    stmt_styles = select(models.ProcedureChartStyle).where(
        models.ProcedureChartStyle.tenant_id == tenant.id
    )
    res_styles = await async_db_session.execute(stmt_styles)
    tenant_styles = res_styles.scalars().all()
    # Expect styles for all procedures with template != NONE (20 procedures)
    expected_styles_count = sum(1 for p in DEFAULT_PROCEDURE_CATALOG if p.chart_template != "NONE")
    assert len(tenant_styles) == expected_styles_count


@pytest.mark.asyncio
async def test_second_registration_gets_isolated_rows(async_db_session: AsyncSession):
    """Second tenant gets its own separate Procedure rows with matching count and unique IDs."""
    from backend import crud

    # Tenant 1
    t1 = models.Tenant(name="Clinic One", is_active=True)
    async_db_session.add(t1)
    await async_db_session.flush()
    await crud.seed_tenant_default_procedures(async_db_session, t1.id)

    # Tenant 2
    t2 = models.Tenant(name="Clinic Two", is_active=True)
    async_db_session.add(t2)
    await async_db_session.flush()
    await crud.seed_tenant_default_procedures(async_db_session, t2.id)

    await async_db_session.commit()

    procs_t1 = (await async_db_session.execute(select(models.Procedure).where(models.Procedure.tenant_id == t1.id))).scalars().all()
    procs_t2 = (await async_db_session.execute(select(models.Procedure).where(models.Procedure.tenant_id == t2.id))).scalars().all()

    assert len(procs_t1) == 34
    assert len(procs_t2) == 34

    ids_t1 = {p.id for p in procs_t1}
    ids_t2 = {p.id for p in procs_t2}
    assert ids_t1.isdisjoint(ids_t2), "Procedures must have distinct IDs between tenants"


@pytest.mark.asyncio
async def test_registration_failure_rolls_back_procedures(async_db_session: AsyncSession):
    """If registration fails in the transaction, procedures and styles are rolled back."""
    from backend import crud

    # Start a nested savepoint or roll back manually
    t_fail = models.Tenant(name="Failing Clinic", is_active=True)
    async_db_session.add(t_fail)
    await async_db_session.flush()

    await crud.seed_tenant_default_procedures(async_db_session, t_fail.id)

    # Simulate registration error
    await async_db_session.rollback()

    # Verify no rows exist for t_fail
    res_p = await async_db_session.execute(select(models.Procedure).where(models.Procedure.tenant_id == t_fail.id))
    assert res_p.scalars().all() == []

    res_s = await async_db_session.execute(select(models.ProcedureChartStyle).where(models.ProcedureChartStyle.tenant_id == t_fail.id))
    assert res_s.scalars().all() == []


# ---------------------------------------------------------------------------
# Backfill Script Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backfill_dry_run_changes_nothing(async_db_session: AsyncSession):
    """Backfill with apply=False examines rows but leaves code and category null."""
    # Seed a tenant procedure without code and category
    t = models.Tenant(name="Backfill Dry Run Clinic", is_active=True)
    async_db_session.add(t)
    await async_db_session.flush()

    raw_proc = models.Procedure(
        name="حشو عصب – Root Canal Treatment",
        price=Decimal("150.00"),
        code=None,
        category=None,
        tenant_id=t.id,
    )
    async_db_session.add(raw_proc)
    await async_db_session.commit()
    proc_id = raw_proc.id

    # Run dry-run backfill
    summary = await run_backfill(async_db_session, apply=False)
    assert summary["dry_run"] is True
    assert summary["total_examined"] >= 1
    assert summary["total_updated"] >= 1

    # Re-fetch from DB: verify row was NOT mutated
    re_proc = await async_db_session.get(models.Procedure, proc_id)
    assert re_proc.code is None
    assert re_proc.category is None
    assert re_proc.price == Decimal("150.00")


@pytest.mark.asyncio
async def test_backfill_apply_updates_without_altering_price(async_db_session: AsyncSession):
    """Backfill with apply=True sets code/category, never touches custom price or creates rows."""
    t = models.Tenant(name="Backfill Apply Clinic", is_active=True)
    async_db_session.add(t)
    await async_db_session.flush()

    custom_price = Decimal("250.00")
    raw_proc = models.Procedure(
        name="حشو عصب – Root Canal Treatment",
        price=custom_price,
        code=None,
        category=None,
        tenant_id=t.id,
    )
    async_db_session.add(raw_proc)
    await async_db_session.commit()
    proc_id = raw_proc.id

    count_before = (await async_db_session.execute(select(func.count(models.Procedure.id)))).scalar_one()

    # Run apply backfill
    summary = await run_backfill(async_db_session, apply=True)
    assert summary["dry_run"] is False

    count_after = (await async_db_session.execute(select(func.count(models.Procedure.id)))).scalar_one()
    assert count_after == count_before, "Backfill must never create new rows"

    re_proc = await async_db_session.get(models.Procedure, proc_id)
    assert re_proc.code == "ENDO_RCT"
    assert re_proc.category == "Endodontic"
    assert re_proc.price == custom_price, "Backfill must preserve clinic price"
