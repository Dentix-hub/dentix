#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
run_dentix_tests.py — lightweight local Dentix pytest launcher.

Canonical dependency truth is `pyproject.toml` + `uv.lock`. CI and production use
`uv sync --frozen`. This helper intentionally keeps its historical lightweight
parallel-venv behavior for quick local test runs by reading dependency constraints
from pyproject.toml and excluding the heavy ML stack.

Usage:
    uv run scripts/run_dentix_tests.py
    uv run scripts/run_dentix_tests.py tests/services/test_appointment_service.py -v
    uv run scripts/run_dentix_tests.py -k "tenant and not slow"
    uv run scripts/run_dentix_tests.py --rebuild
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def _resolve_backend_root() -> Path:
    env = os.environ.get("DENTIX_BACKEND_ROOT")
    if env:
        return Path(env)

    cwd_candidate = Path.cwd() / "backend"
    if cwd_candidate.is_dir():
        return cwd_candidate

    script_candidate = Path(__file__).resolve().parents[1] / "backend"
    return script_candidate


BACKEND_ROOT = _resolve_backend_root()
if not BACKEND_ROOT.is_dir():
    sys.exit(f"backend/ not found. CWD={Path.cwd()}")

PROJECT_ROOT = BACKEND_ROOT.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
VENV_PATH = Path(tempfile.gettempdir()) / "dentix-test"

HEAVY_EXCLUDE = {
    "torch",
    "chromadb",
    "sentence-transformers",
    "sentence_transformers",
}
TEST_TOOL_PREFIXES = ("pytest",)


def _package_name(spec: str) -> str:
    return re.split(r"[<>=!~;\[]", spec, 1)[0].strip().lower()


def _load_min_requirements() -> list[str]:
    """Read lightweight runtime + pytest constraints from canonical pyproject.toml."""
    if not PYPROJECT.exists():
        raise SystemExit(f"pyproject.toml missing at {PYPROJECT}")

    with PYPROJECT.open("rb") as handle:
        manifest = tomllib.load(handle)

    runtime = list(manifest.get("project", {}).get("dependencies", []))
    dev = list(manifest.get("dependency-groups", {}).get("dev", []))
    pytest_deps = [
        spec for spec in dev if _package_name(spec).startswith(TEST_TOOL_PREFIXES)
    ]

    keep: list[str] = []
    for spec in [*runtime, *pytest_deps]:
        if _package_name(spec) in HEAVY_EXCLUDE:
            continue
        keep.append(spec)

    if not keep:
        raise SystemExit("Lightweight dependency set resolved to empty")
    return keep


def _interp() -> Path:
    if sys.platform == "win32":
        return VENV_PATH / "Scripts" / "python.exe"
    return VENV_PATH / "bin" / "python"


def _uv_bin() -> str:
    resolved = shutil.which("uv")
    if resolved:
        return resolved
    raise SystemExit("uv not found on PATH. Install: https://docs.astral.sh/uv/")


def _venv_usable() -> bool:
    if not _interp().exists():
        return False
    try:
        result = subprocess.run(
            [_interp(), "-c", "import sys; sys.path[:0]=['.']; import backend, pytest"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _create_venv() -> None:
    uv = _uv_bin()
    subprocess.run(
        [uv, "venv", str(VENV_PATH), "--python", "3.11", "--clear"],
        check=True,
    )

    print(
        "[run_dentix_tests] installing lightweight dependencies from pyproject.toml",
        file=sys.stderr,
    )
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(VENV_PATH)
    subprocess.run(
        [uv, "pip", "install", *_load_min_requirements()],
        env=env,
        check=True,
    )

    result = subprocess.run(
        [_interp(), "-c", "import backend, backend.crud.appointment, pytest"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
    )
    if result.returncode != 0:
        print("[run_dentix_tests] import probe failed:", file=sys.stderr)
        print(result.stderr.decode(), file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild the parallel venv even if it appears usable",
    )
    parser.add_argument(
        "--strict-isolation",
        action="store_true",
        help="Reserved compatibility flag; pytest exit behavior remains strict.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments to forward to pytest (after `--`)",
    )
    args = parser.parse_args()
    pytest_args = [arg for arg in args.pytest_args if arg != "--"]

    if not (BACKEND_ROOT / "tests").is_dir():
        raise SystemExit(f"backend/tests not found at {BACKEND_ROOT}/tests")
    if not PYPROJECT.exists():
        raise SystemExit(f"pyproject.toml missing at {PYPROJECT}")

    pytest_args = [
        arg[len("backend/") :] if arg.startswith("backend/") else arg
        for arg in pytest_args
    ]

    if args.rebuild or not _venv_usable():
        _create_venv()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    env["DATABASE_URL"] = "sqlite:///:memory:"
    env["ENVIRONMENT"] = "testing"

    cmd = [str(_interp()), "-m", "pytest", *pytest_args]
    print("[run_dentix_tests] cmd:", " ".join(cmd), file=sys.stderr)
    print("[run_dentix_tests] cwd:", str(BACKEND_ROOT), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(BACKEND_ROOT), env=env)


if __name__ == "__main__":
    sys.exit(main())


PRE_EXISTING_PROBE_USAGE = """
    from scripts.run_dentix_tests import probe_pre_existing
    is_pre_existing = probe_pre_existing(
        test_target="tests/services/test_treatment_service.py::TestTreatmentCreation::test_create_basic_treatment",
    )
"""


def probe_pre_existing(test_target: str) -> bool:
    """Return whether a target fails with uncommitted changes temporarily stashed."""
    if not (PROJECT_ROOT / ".git").exists():
        raise SystemExit("Not a git repo — can't probe pre-existing state safely.")

    stashed = subprocess.run(
        ["git", "stash", "--keep-index"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if "No local changes to save" not in stashed.stdout and stashed.returncode != 0:
        if "No local changes" not in stashed.stdout:
            raise SystemExit(f"git stash failed: {stashed.stderr}")

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["DATABASE_URL"] = "sqlite:///:memory:"
        env["ENVIRONMENT"] = "testing"
        result = subprocess.run(
            [_interp(), "-m", "pytest", test_target, "--no-cov"],
            cwd=str(BACKEND_ROOT),
            env=env,
            capture_output=True,
        )
        return result.returncode != 0
    finally:
        subprocess.run(
            ["git", "stash", "pop"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
        )
