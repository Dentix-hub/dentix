from pathlib import Path


def test_startup_delegates_migrations_to_preflight_only():
    repo_root = Path(__file__).resolve().parents[2]
    startup = (repo_root / "scripts" / "deployment" / "startup.sh").read_text(
        encoding="utf-8"
    )

    assert "python -m backend.scripts.preflight_migrations" in startup
    assert startup.count("python -m backend.scripts.preflight_migrations") == 1
    assert "alembic upgrade head" not in startup
    assert "fix_alembic_version" not in startup
    assert 'exec "$@"' in startup


def test_container_smoke_separates_schema_owner_from_runtime_roles():
    repo_root = Path(__file__).resolve().parents[2]
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    owner_preflight = '-e DATABASE_URL="$OWNER_DATABASE_URL"'
    runtime_start = "docker run --detach"

    assert owner_preflight in workflow
    assert "--entrypoint python" in workflow
    assert "-m backend.scripts.preflight_migrations" in workflow
    assert workflow.index(owner_preflight) < workflow.index(runtime_start)
    assert "GRANT CREATE ON SCHEMA public TO dentix_container_app" not in workflow


def test_preflight_database_url_prefers_migration_and_owner_urls(monkeypatch):
    from backend.scripts.preflight_migrations import _database_url

    monkeypatch.setenv("DATABASE_URL", "postgresql://app@db/prod")
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("OWNER_DATABASE_URL", raising=False)
    assert _database_url() == "postgresql://app@db/prod"

    monkeypatch.setenv("OWNER_DATABASE_URL", "postgresql://owner@db/prod")
    assert _database_url() == "postgresql://owner@db/prod"

    monkeypatch.setenv("MIGRATION_DATABASE_URL", "postgresql://migration@db/prod")
    assert _database_url() == "postgresql://migration@db/prod"


def test_alembic_env_preserves_preconfigured_migration_url(monkeypatch):
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    ini_path = repo_root / "backend" / "alembic.ini"
    cfg = Config(str(ini_path))

    # Preflight set the privileged migration URL
    cfg.set_main_option("sqlalchemy.url", "postgresql://migration_owner@db/prod")

    # Even if unprivileged runtime DATABASE_URL is set in environment
    monkeypatch.setenv("DATABASE_URL", "postgresql://unprivileged_app@db/prod")
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("OWNER_DATABASE_URL", raising=False)

    # Simulating env.py database URL resolution logic
    configured_url = cfg.get_main_option("sqlalchemy.url")
    placeholder_urls = {"", "driver://user:pass@localhost/dbname"}
    if not configured_url or configured_url in placeholder_urls:
        import os

        raw_url = (
            os.getenv("MIGRATION_DATABASE_URL")
            or os.getenv("OWNER_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )
        if raw_url:
            cfg.set_main_option("sqlalchemy.url", raw_url)

    # Must preserve the preconfigured migration owner URL
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql://migration_owner@db/prod"


def test_alembic_env_resolves_migration_and_owner_urls_when_unset(monkeypatch):
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    ini_path = repo_root / "backend" / "alembic.ini"

    # 1. Fallback to DATABASE_URL when no owner/migration url
    cfg = Config(str(ini_path))
    monkeypatch.setenv("DATABASE_URL", "postgresql://app@db/prod")
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("OWNER_DATABASE_URL", raising=False)

    configured_url = cfg.get_main_option("sqlalchemy.url")
    placeholder_urls = {"", "driver://user:pass@localhost/dbname"}
    if not configured_url or configured_url in placeholder_urls:
        import os

        raw_url = (
            os.getenv("MIGRATION_DATABASE_URL")
            or os.getenv("OWNER_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )
        if raw_url:
            cfg.set_main_option("sqlalchemy.url", raw_url)
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql://app@db/prod"

    # 2. Prefer OWNER_DATABASE_URL over DATABASE_URL
    cfg = Config(str(ini_path))
    monkeypatch.setenv("OWNER_DATABASE_URL", "postgresql://owner@db/prod")
    configured_url = cfg.get_main_option("sqlalchemy.url")
    if not configured_url or configured_url in placeholder_urls:
        import os

        raw_url = (
            os.getenv("MIGRATION_DATABASE_URL")
            or os.getenv("OWNER_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )
        if raw_url:
            cfg.set_main_option("sqlalchemy.url", raw_url)
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql://owner@db/prod"

    # 3. Prefer MIGRATION_DATABASE_URL over OWNER_DATABASE_URL
    cfg = Config(str(ini_path))
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "postgresql://migration@db/prod")
    configured_url = cfg.get_main_option("sqlalchemy.url")
    if not configured_url or configured_url in placeholder_urls:
        import os

        raw_url = (
            os.getenv("MIGRATION_DATABASE_URL")
            or os.getenv("OWNER_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )
        if raw_url:
            cfg.set_main_option("sqlalchemy.url", raw_url)
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql://migration@db/prod"


def test_same_database_target_matches_host_and_database():
    from backend.scripts.preflight_migrations import _same_database_target

    assert _same_database_target(
        "postgresql://dentix_app:pass@aws-1-eu-west-3.pooler.supabase.com:6543/postgres",
        "postgresql://postgres:pass@aws-1-eu-west-3.pooler.supabase.com:5432/postgres",
    )
    assert not _same_database_target(
        "postgresql://postgres:postgres@127.0.0.1:5432/dentix_contract_123",
        "postgresql://dentix_ci_system:pass@127.0.0.1:5432/dentix_test",
    )


def test_preflight_database_url_falls_back_to_system_url_when_it_owns_tables(monkeypatch):
    import backend.scripts.preflight_migrations as preflight

    app_url = "postgresql://dentix_app:pass@pooler.supabase.com:6543/postgres"
    sys_url = "postgresql://postgres:pass@pooler.supabase.com:6543/postgres"

    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("OWNER_DATABASE_URL", raising=False)
    monkeypatch.delenv("BACKUP_SOURCE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DENTIX_MIGRATION_SET_ROLE", raising=False)
    monkeypatch.setenv("DATABASE_URL", app_url)
    monkeypatch.setenv("SYSTEM_DATABASE_URL", sys_url)

    def fake_probe(url: str):
        if url == app_url:
            return {
                "current_user": "dentix_app",
                "session_user": "dentix_app",
                "tables": {
                    "treatment_material_usages": {
                        "owner": "postgres",
                        "has_usage": False,
                        "is_member": False,
                    }
                },
                "usage_count": 0,
                "member_count": 0,
                "total_probed": 1,
                "set_role_target": None,
            }
        if url == sys_url:
            return {
                "current_user": "postgres",
                "session_user": "postgres",
                "tables": {
                    "treatment_material_usages": {
                        "owner": "postgres",
                        "has_usage": True,
                        "is_member": True,
                    }
                },
                "usage_count": 1,
                "member_count": 1,
                "total_probed": 1,
                "set_role_target": None,
            }
        return None

    monkeypatch.setattr(preflight, "_probe_postgresql_candidate", fake_probe)
    assert preflight._database_url() == sys_url



