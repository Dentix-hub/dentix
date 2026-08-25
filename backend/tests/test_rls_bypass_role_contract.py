"""Static fail-closed contract for application/system PostgreSQL role separation."""

from pathlib import Path

import pytest
from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[2]


def test_current_rls_installers_do_not_grant_guc_bypass():
    for relative in (
        "backend/alembic/versions/e1f2a3b4c5d6_enforce_child_tenant_rls.py",
        "backend/alembic/versions/e2f3a4b5c6d7_subscription_renewal_idempotency.py",
        "backend/scripts/preflight_migrations.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "current_setting('rls.bypass_rls'" not in source


def test_fresh_preflight_replaces_create_all_hook_policies():
    source = (ROOT / "backend/scripts/preflight_migrations.py").read_text(
        encoding="utf-8"
    )
    assert "_drop_postgresql_table_policies(connection, table)" in source
    assert '_drop_postgresql_table_policies(connection, "notifications")' in source


def test_head_migration_removes_historical_application_bypass():
    source = (
        ROOT
        / "backend/alembic/versions/e3a4b5c6d7e8_remove_application_rls_bypass.py"
    ).read_text(encoding="utf-8")
    assert "ALTER POLICY" in source
    assert "rls.bypass_rls" in source
    assert "Refusing to restore" in source


def test_runtime_uses_separate_native_bypassrls_connection():
    source = (ROOT / "backend/database.py").read_text(encoding="utf-8")
    assert "SYSTEM_DATABASE_URL" in source
    assert "non-superuser NOBYPASSRLS" in source
    assert "non-superuser BYPASSRLS" in source
    assert "current_database()" in source
    assert "rolsuper" in source
    assert "set_config('rls.bypass_rls'" not in source


def test_clinic_registration_uses_narrow_system_scope():
    bootstrap_source = (
        ROOT / "backend/services/auth_bootstrap.py"
    ).read_text(encoding="utf-8")
    register_source = (
        ROOT / "backend/routers/auth/register.py"
    ).read_text(encoding="utf-8")

    assert "async def clinic_registration_scope" in bootstrap_source
    assert 'if "postgresql" in ASYNC_DATABASE_URL' in bootstrap_source
    assert "async with system_session_scope()" in bootstrap_source
    assert "async with clinic_registration_scope(db)" in register_source


def test_ci_disposes_both_postgresql_async_pools():
    source = (ROOT / "backend/ci_tests/conftest.py").read_text(encoding="utf-8")
    assert "await async_engine.dispose()" in source
    assert "await system_async_engine.dispose()" in source


def test_postgresql_data_repair_uses_system_engine():
    source = (
        ROOT / "backend/ci_tests/test_finance_postgres_smoke.py"
    ).read_text(encoding="utf-8")
    assert "async with system_async_engine.begin()" in source


@pytest.mark.asyncio
async def test_rls_session_rebinds_after_transaction_boundaries():
    from backend.database import AsyncSessionLocal, RlsContext

    async with AsyncSessionLocal(context=RlsContext(tenant_id=7)) as session:
        await session.execute(text("SELECT 1"))
        assert session._rls_dirty is False

        await session.commit()
        assert session._rls_dirty is True

        await session.execute(text("SELECT 1"))
        assert session._rls_dirty is False

        await session.rollback()
        assert session._rls_dirty is True


def test_global_catalog_maintenance_uses_system_sessions():
    for relative in (
        "backend/scripts/fix_procedures_tenant.py",
        "backend/scripts/seed_procedures.py",
        "backend/scripts/seed_material_categories.py",
        "backend/scripts/seed_procedure_material_defaults.py",
        "backend/scripts/fix_global_procedures.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "system_session_scope" in source
