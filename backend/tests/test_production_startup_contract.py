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
