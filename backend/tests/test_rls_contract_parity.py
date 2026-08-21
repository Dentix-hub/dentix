import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

_RUNTIME_INVENTORY_SCRIPT = r'''
import json
import backend.main  # Import the production application and all runtime routers.
from backend import models
from backend.scripts.preflight_migrations import RLS_TABLES

model_tables = sorted(
    table.name
    for table in models.Base.metadata.tables.values()
    if "tenant_id" in table.c
)
configured = sorted(set(RLS_TABLES) | {"notifications"})
print("RLS_RUNTIME_INVENTORY=" + json.dumps({
    "model_tables": model_tables,
    "configured": configured,
    "missing": sorted(set(model_tables) - set(configured)),
    "stale": sorted(set(configured) - set(model_tables)),
}))
'''


def _runtime_inventory() -> dict:
    """Measure RLS parity in a clean process, isolated from pytest collection."""
    completed = subprocess.run(
        [sys.executable, "-c", _RUNTIME_INVENTORY_SCRIPT],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    prefix = "RLS_RUNTIME_INVENTORY="
    line = next(
        (line for line in reversed(completed.stdout.splitlines()) if line.startswith(prefix)),
        None,
    )
    assert line is not None, (
        "Clean runtime RLS inventory did not produce its sentinel. "
        f"stdout={completed.stdout[-2000:]!r} stderr={completed.stderr[-2000:]!r}"
    )
    return json.loads(line[len(prefix):])


def test_every_runtime_tenant_table_is_in_production_rls_contract():
    inventory = _runtime_inventory()
    assert not inventory["missing"] and not inventory["stale"], (
        "Production runtime RLS contract drift detected. "
        f"missing={inventory['missing']}, stale={inventory['stale']}, "
        f"runtime_tables={inventory['model_tables']}, configured={inventory['configured']}"
    )


def test_runtime_tenant_rls_parity_is_exact_not_percentage_based():
    inventory = _runtime_inventory()
    assert inventory["model_tables"] == inventory["configured"]
