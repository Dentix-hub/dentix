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
