"""Static fail-closed contract for application/system PostgreSQL role separation."""

from pathlib import Path


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
