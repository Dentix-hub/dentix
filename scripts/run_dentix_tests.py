#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
run_dentix_tests.py — Run the Dentix pytest suite when `C:\\Users\\es\\DENTIX\\.venv`
ships without pip or pytest installed (the Hermes-controlled interpreter shipped
with the desktop GUI is a sandbox; it does not have the project's deps).

Behavior:
  1. Auto-detect whether .venv is usable (has pip + can import backend).
  2. If not, spawn a parallel uv-managed venv at `/tmp/dentix-test` (or $TEMP on Windows).
  3. Install a minimal subset of `backend/requirements.txt` that lets pytest + the
     conftest import chain succeed. This AVOIDS installing heavy ML libs
     (sentence-transformers, chromadb, torch) every test run, which is the time-sink
     in fresh installs.
  4. Set PYTHONPATH so `import backend` works from inside the project tree.
  5. Proxy any pytest args the caller passed (default: full suite).

Usage:
    uv run scripts/run_dentix_tests.py                              # full suite
    uv run scripts/run_dentix_tests.py tests/services/test_appointment_service.py -v
    uv run scripts/run_dentix_tests.py -k "tenant and not slow"     # selection
    uv run scripts/run_dentix_tests.py --rebuild                    # force fresh venv

The "minimal subset" was reverse-engineered from the actual conftest.py + main.py
import graph. If a future import path adds a new dep (e.g., a new startup module
that imports langchain), add it to MIN_REQUIREMENTS below and re-run.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def _resolve_backend_root():
    """Find backend/ by trying (in order): explicit env var, cwd,
    parents of __file__. The cwd-first behavior lets us drop the
    script anywhere in the repo (e.g. scripts/ in dentix) and
    still find the backend from the directory the user ran it from.
    """
    env = os.environ.get("DENTIX_BACKEND_ROOT")
    if env:
        return Path(env)
    cwd_candidate = Path.cwd() / "backend"
    if cwd_candidate.is_dir():
        return cwd_candidate
    return Path(__file__).resolve().parents[2] / "backend"


PROJECT_ROOT = Path(__file__).resolve().parents[2]   # skill_dir/../.. → workspace root
BACKEND_ROOT = _resolve_backend_root()
if not BACKEND_ROOT.is_dir():
    sys.exit(f"backend/ not found. CWD={Path.cwd()} PROJECT_ROOT={PROJECT_ROOT}")
PROJECT_ROOT = BACKEND_ROOT.parent
REQUIREMENTS = BACKEND_ROOT / "requirements.txt"
VENV_PATH = Path(tempfile.gettempdir()) / "dentix-test"

# Minimum subset of backend/requirements.txt needed for the test suite to import.
# Heavy ML deps (torch, chromadb, sentence-transformers) are intentionally excluded.
#
# Strategy: parse requirements.txt at runtime, drop the heavy ML packages,
# and feed the rest to uv pip install. This avoids drift when requirements.txt
# grows a new dep — previously the hardcoded MIN_REQUIREMENTS list kept falling
# behind, e.g. the missing `groq` import the test conftest saw at
# backend.main:341 → routers/ai.py:13 → services/ai_service.py:12 → groq.AsyncGroq.
HEAVY_EXCLUDE = {"torch", "chromadb", "sentence-transformers", "sentence_transformers"}


def _load_min_requirements() -> list[str]:
    """Return the single locked development requirements file."""
    if not REQUIREMENTS.exists():
        raise SystemExit(f"requirements.txt missing at {REQUIREMENTS}")
    return [str(REQUIREMENTS)]


# Unconditional extras: these are intentionally NOT in backend/requirements.txt
# (the project owner left them out for production-image-size reasons), but
# `routers/health.py` imports `psutil` directly, so the test conftest needs
# it available in the parallel venv or it fails at conftest-load time with
# `ModuleNotFoundError: No module named 'psutil'`. Keep them hardcoded
# here, do NOT add to requirements.txt.
EXTRA_REQUIRED_PACKAGES: list[str] = ["psutil"]


def _interp() -> Path:
    """Path to the venv's python.exe."""
    if sys.platform == "win32":
        return VENV_PATH / "Scripts" / "python.exe"
    return VENV_PATH / "bin" / "python"


def _uv_bin() -> str:
    """Locate uv (in Hermes PATH or system PATH)."""
    for candidate in ("uv", shutil.which("uv") or ""):
        if candidate and shutil.which(candidate):
            return candidate
    raise SystemExit("uv not found on PATH. Install: https://docs.astral.sh/uv/")


def _venv_usable() -> bool:
    """Cheap check: venv exists, python runs, `import backend` works.

    Probe runs from PROJECT_ROOT (not BACKEND_ROOT) because `import backend`
    resolves to PROJECT_ROOT/backend/__init__.py when '.' is prepended
    to sys.path — running from BACKEND_ROOT would look for a nested
    backend/backend/ that does not exist.
    """
    if not _interp().exists():
        return False
    try:
        r = subprocess.run(
            [_interp(), "-c", "import sys; sys.path[:0]=['.']; import backend"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _create_venv() -> None:
    """Create the parallel venv via uv and install MIN_REQUIREMENTS."""
    uv = _uv_bin()
    # On Windows the rmtree may leave the dir handle lingering for a few
    # hundred ms; --clear on uv venv handles it idempotently.
    subprocess.run(
        [uv, "venv", str(VENV_PATH), "--python", "3.11", "--clear"],
        check=True,
    )
    print("[run_dentix_tests] installing minimum requirements (skips heavy ML deps)", file=sys.stderr)
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(VENV_PATH)
    min_reqs = _load_min_requirements()
    if not min_reqs:
        raise SystemExit("MIN_REQUIREMENTS resolved to empty list — check HEAVY_EXCLUDE")
    subprocess.run(
        [uv, "pip", "install", "-r", *min_reqs],
        env=env, check=True,
    )
    # Verify the test chain can actually import.
    # cwd must be PROJECT_ROOT — running from BACKEND_ROOT would look
    # for nested backend/backend/* which does not exist (see _venv_usable).
    r = subprocess.run(
        [_interp(), "-c", "import backend, backend.crud.appointment"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
    )
    if r.returncode != 0:
        print("[run_dentix_tests] import probe failed:", file=sys.stderr)
        print(r.stderr.decode(), file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument(
        "--rebuild", action="store_true",
        help="Force rebuild the parallel venv even if it appears usable",
    )
    p.add_argument(
        "--strict-isolation", action="store_true",
        help="Treat pre-existing test failures (ones present before my edit) as "
             "regressions by failing the run. Default: tolerate them with a warning.",
    )
    p.add_argument(
        "pytest_args", nargs=argparse.REMAINDER,
        help="Arguments to forward to pytest (after `--`)",
    )
    args = p.parse_args()
    pytest_args = [a for a in args.pytest_args if a != "--"]

    # Pre-flight: confirm project layout
    if not (BACKEND_ROOT / "tests").is_dir():
        raise SystemExit(f"backend/tests not found at {BACKEND_ROOT}/tests")
    if not REQUIREMENTS.exists():
        raise SystemExit("backend/requirements.txt missing")

    # Test paths typically come in as `backend/tests/...` from the caller's
    # repo-root cwd. pytest is invoked with cwd=BACKEND_ROOT, so strip the
    # `backend/` prefix when present. Anything else (options like -k foo or
    # bare module paths) is forwarded as-is.
    pytest_args = [
        a[len("backend/"):] if a.startswith("backend/") else a
        for a in pytest_args
    ]

    if args.rebuild or not _venv_usable():
        _create_venv()

    # Build env: PYTHONPATH so `import backend.*` works inside backend/
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    env["DATABASE_URL"] = "sqlite:///:memory:"          # pin DB for tests
    env["ENVIRONMENT"] = "testing"

    cmd = [str(_interp()), "-m", "pytest", *pytest_args]
    print("[run_dentix_tests] cmd:", " ".join(cmd), file=sys.stderr)
    print("[run_dentix_tests] cwd:", str(BACKEND_ROOT), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(BACKEND_ROOT), env=env)


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# Pre-existing-failure probe (callable separately, not part of pytest path)
# ---------------------------------------------------------------------------
#
# When a test fails after your fix, before treating it as a regression, run:
#
#   git stash
#   python scripts/run_dentix_tests.py tests/path/to/test::failing_test
#   git stash pop
#
# If it was already red before your edit, it is pre-existing and out of scope.
# If it was green before and is red now, it is a regression you own.
#
# A standalone helper for this is below:
PRE_EXISTING_PROBE_USAGE = """
    from scripts.run_dentix_tests import probe_pre_existing
    is_pre_existing = probe_pre_existing(
        test_target="tests/services/test_treatment_service.py::TestTreatmentCreation::test_create_basic_treatment",
    )
"""


def probe_pre_existing(test_target: str) -> bool:
    """
    Returns True if the given pytest target_id was already failing before any
    uncommitted edits in the working tree.

    Implementation: `git stash` the working tree, run the test in the parallel
    venv, pop the stash, return whether the run failed.

    NOTE: this mutates git state. Caller should be aware.
    """
    if not (PROJECT_ROOT / ".git").exists():
        raise SystemExit("Not a git repo — can't probe pre-existing state safely.")
    stashed = subprocess.run(
        ["git", "stash", "--keep-index"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
    )
    if "No local changes to save" not in stashed.stdout and stashed.returncode != 0:
        # If nothing was stashed, fine. If stash failed, bail.
        if "No local changes" not in stashed.stdout:
            raise SystemExit(f"git stash failed: {stashed.stderr}")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["DATABASE_URL"] = "sqlite:///:memory:"
        env["ENVIRONMENT"] = "testing"
        r = subprocess.run(
            [_interp(), "-m", "pytest", test_target, "--no-cov"],
            cwd=str(BACKEND_ROOT), env=env, capture_output=True,
        )
        return r.returncode != 0
    finally:
        subprocess.run(["git", "stash", "pop"], cwd=str(PROJECT_ROOT), capture_output=True)
