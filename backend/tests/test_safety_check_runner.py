import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[2] / ".github" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from run_safety_check import DEFAULT_COMMAND, run_safety_check  # noqa: E402


def _completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=list(DEFAULT_COMMAND),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _runner_for(results, calls):
    remaining = iter(results)

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return next(remaining)

    return runner


def test_success_returns_without_retry():
    calls = []
    sleeps = []

    result = run_safety_check(
        runner=_runner_for([_completed(0, stdout="clean")], calls),
        sleeper=sleeps.append,
    )

    assert result == 0
    assert calls == [
        (
            list(DEFAULT_COMMAND),
            {"check": False, "capture_output": True, "text": True},
        )
    ]
    assert sleeps == []


def test_vulnerability_exit_fails_without_retry():
    calls = []

    result = run_safety_check(
        runner=_runner_for(
            [_completed(64, stdout="Vulnerabilities were found")],
            calls,
        ),
        sleeper=lambda _delay: pytest.fail("must not retry a vulnerability result"),
    )

    assert result == 64
    assert len(calls) == 1

def test_vulnerability_exit_with_crash_text_still_fails_without_retry():
    calls = []

    mixed_output = (
        "Vulnerabilities were found\n"
        "Unhandled exception happened: 'cuda-toolkit'"
    )

    result = run_safety_check(
        runner=_runner_for([_completed(64, stderr=mixed_output)], calls),
        sleeper=lambda _delay: pytest.fail("must not retry a vulnerability result"),
    )

    assert result == 64
    assert len(calls) == 1


def test_unrelated_error_fails_without_retry():
    calls = []

    result = run_safety_check(
        runner=_runner_for([_completed(1, stderr="network unavailable")], calls),
        sleeper=lambda _delay: pytest.fail("must not retry an unrelated error"),
    )

    assert result == 1
    assert len(calls) == 1


def test_feed_mismatch_retries_then_succeeds():
    calls = []
    sleeps = []
    mismatch = "Unhandled exception happened: 'cuda-toolkit'"

    result = run_safety_check(
        runner=_runner_for(
            [_completed(1, stderr=mismatch), _completed(0, stdout="clean")],
            calls,
        ),
        sleeper=sleeps.append,
        delay_seconds=0,
    )

    assert result == 0
    assert len(calls) == 2
    assert sleeps == [0]


def test_feed_mismatch_exhaustion_remains_failure():
    calls = []
    sleeps = []
    mismatch = "Unhandled exception happened: 'cuda-toolkit'"

    result = run_safety_check(
        max_attempts=3,
        delay_seconds=0,
        runner=_runner_for([_completed(1, stderr=mismatch)] * 3, calls),
        sleeper=sleeps.append,
    )

    assert result == 1
    assert len(calls) == 3
    assert sleeps == [0, 0]


def test_invalid_attempt_count_is_rejected():
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        run_safety_check(max_attempts=0)
