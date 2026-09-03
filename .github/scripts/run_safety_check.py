#!/usr/bin/env python3
"""Run Safety fail-closed while tolerating its transient feed mismatch."""

from collections.abc import Callable, Sequence
import re
import subprocess
import sys
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
    return run_safety_check()


if __name__ == "__main__":
    raise SystemExit(main())
