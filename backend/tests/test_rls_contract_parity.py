import json
import os
from pathlib import Path
import subprocess
import sys

from backend.scripts.preflight_migrations import RLS_TABLES


def _runtime_tenant_tables() -> set[str]:
    """Inspect only the production import graph, isolated from pytest models."""
    repo_root = Path(__file__).resolve().parents[2]
    probe = """
import json
import backend.main  # noqa: F401 - register the production application/model graph
from backend.models import Base
print(json.dumps(sorted(
    table.name
    for table in Base.metadata.tables.values()
    if "tenant_id" in table.c
)))
"""
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite:///./test.db")
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = completed.stdout.strip().splitlines()[-1]
    return set(json.loads(payload))


def test_runtime_tenant_models_match_canonical_rls_contract():
    model_tables = _runtime_tenant_tables()
    # `notifications` is intentionally outside generic RLS_TABLES because its
    # FORCE-RLS policy allows current-tenant rows plus deliberate global rows.
    # preflight installs/verifies `notifications_tenant_policy` separately.
    configured_tables = set(RLS_TABLES) | {"notifications"}

    missing = sorted(model_tables - configured_tables)
    stale = sorted(configured_tables - model_tables)

    assert not missing, (
        "tenant-scoped runtime tables missing from the PostgreSQL RLS contract: "
        f"{missing}"
    )
    assert not stale, (
        "RLS contract entries no longer represented by a runtime tenant_id model: "
        f"{stale}"
    )
