#!/usr/bin/env python3
"""Run Safety fail-closed while tolerating its transient feed mismatch."""

from collections.abc import Callable, Sequence
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import time


FEED_MISMATCH_PATTERN = re.compile(r"Unhandled exception happened: '[^'\r\n]+'")
DEFAULT_COMMAND = ("safety", "check", "--full-report")
VULNERABILITY_EXIT_CODES = frozenset({64})


def run_safety_check(
    *,
    max_attempts: int = 3,
    delay_seconds: float = 15.0,
    command: Sequence[str] = DEFAULT_COMMAND,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    """Return Safety's exit code, retrying only its exact feed-mismatch crash."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(1, max_attempts + 1):
        completed = runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)

        if completed.returncode == 0:
            return 0

        if completed.returncode in VULNERABILITY_EXIT_CODES:
            return completed.returncode

        feed_mismatch = FEED_MISMATCH_PATTERN.search(f"{stdout}\n{stderr}")
        if completed.returncode != 1 or not feed_mismatch or attempt == max_attempts:
            return completed.returncode

        print(
            "::warning::Safety vulnerability feeds were inconsistent "
            f"(attempt {attempt}/{max_attempts}); retrying in {delay_seconds:g}s.",
            file=sys.stderr,
        )
        sleeper(delay_seconds)

    raise AssertionError("unreachable")


def main() -> int:
    installed = subprocess.run(
        ("uv", "pip", "freeze", "--python", sys.executable),
        check=True,
        capture_output=True,
        text=True,
    )
    # Safety 3.8.1 requires filelock < 4. Keep its tools out of the app environment
    # and scan every installed app and test dependency from the frozen environment.
    with TemporaryDirectory(prefix="dentix-safety-") as tmp_dir:
        requirements = Path(tmp_dir) / "requirements.txt"
        requirements.write_text(installed.stdout, encoding="utf-8")
        return run_safety_check(
            command=("uvx", "--from", "safety==3.8.1", *DEFAULT_COMMAND, "--file", str(requirements))
        )


if __name__ == "__main__":
    raise SystemExit(main())
