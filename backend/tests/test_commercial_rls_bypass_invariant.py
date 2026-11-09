"""Test strict RLS bypass invariants for commercial and AI tables."""

from pathlib import Path

from backend.scripts import preflight_migrations as preflight


def test_rls_tables_include_commercial_and_ai():
    """commercial_tenant_overrides, ai_quota_windows, ai_reservations must be tracked in RLS_TABLES."""
    required = {"commercial_tenant_overrides", "ai_quota_windows", "ai_reservations"}
    assert required.issubset(set(preflight.RLS_TABLES))


def test_migration_files_contain_no_application_bypass_in_policies():
    """No post-historical migration file should create a table policy with rls.bypass_rls."""
    versions_dir = Path("backend/alembic/versions")
    target_migrations = [
        versions_dir / "e4a5b6c7d8e9_commercial_policy_persistence.py",
        versions_dir / "1f2e3d4c5b6a_ai_quota_reservation_ledger.py",
    ]
    for path in target_migrations:
        assert path.is_file(), f"Migration file {path} not found"
        content = path.read_text(encoding="utf-8")
        assert "rls.bypass_rls" not in content, (
            f"Found forbidden application GUC 'rls.bypass_rls' in {path.name}"
        )


def test_cleanup_migration_exists_and_is_head():
    """Migration 2a3b4c5d6e7f must exist, target 1f2e3d4c5b6a, and clean any bypass policies."""
    cleanup_path = Path("backend/alembic/versions/2a3b4c5d6e7f_remove_commercial_and_ai_rls_bypass.py")
    assert cleanup_path.is_file()
    content = cleanup_path.read_text(encoding="utf-8")
    assert 'down_revision: Union[str, Sequence[str], None] = "1f2e3d4c5b6a"' in content
    assert "ALTER POLICY" in content
    assert "rls.bypass_rls" in content


def test_ai_reservations_trigger_migration_exists():
    """Migration 3b4c5d6e7f8a must exist and install child tenant triggers for ai_reservations."""
    trigger_path = Path("backend/alembic/versions/3b4c5d6e7f8a_ai_reservations_child_tenant_triggers.py")
    assert trigger_path.is_file()
    content = trigger_path.read_text(encoding="utf-8")
    assert 'down_revision: Union[str, Sequence[str], None] = "2a3b4c5d6e7f"' in content
    assert "trg_ai_reservations_window_id_parent_tenant" in content
    assert "trg_ai_reservations_user_id_parent_tenant" in content
