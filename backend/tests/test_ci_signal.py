import sys
from pathlib import Path
import pytest

script_path = Path(__file__).parent.parent.parent / ".github" / "scripts"
sys.path.insert(0, str(script_path.resolve()))
from evaluate_ci_signal import (
    REQUIRED_CHECK_CONTEXTS,
    GITHUB_ACTIONS_APP_ID,
    evaluate_checks,
    post_transition_comment,
    sync_labels,
    verify_sha_still_current,
)


def _make_check_run(name, status="completed", conclusion="success", app_id=GITHUB_ACTIONS_APP_ID, url=""):
    """Helper to create a check-run dict with the expected app.id."""
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "html_url": url,
        "app": {"id": app_id},
    }


def test_required_contexts_list():
    assert len(REQUIRED_CHECK_CONTEXTS) == 12
    assert "Protect authoritative CD workflow" in REQUIRED_CHECK_CONTEXTS
    assert "Validate promotion path" in REQUIRED_CHECK_CONTEXTS
    assert "Verify GitHub branch enforcement" in REQUIRED_CHECK_CONTEXTS
    assert "Backend Tests + Security" in REQUIRED_CHECK_CONTEXTS
    assert "Frontend Tests" in REQUIRED_CHECK_CONTEXTS
    assert "E2E Critical Path (Playwright)" in REQUIRED_CHECK_CONTEXTS
    assert "Validate Production Container" in REQUIRED_CHECK_CONTEXTS
    assert "Concurrent Tenant Isolation" in REQUIRED_CHECK_CONTEXTS
    assert "Reproduce / Recover Stale Frontend Assets" in REQUIRED_CHECK_CONTEXTS
    assert "Responsive Acceptance Matrix" in REQUIRED_CHECK_CONTEXTS
    assert "Full Git History Secret Scan" in REQUIRED_CHECK_CONTEXTS
    assert "Frozen Dependency Reproducibility" in REQUIRED_CHECK_CONTEXTS


def test_evaluate_checks_all_green(monkeypatch):
    check_runs = [_make_check_run(name) for name in REQUIRED_CHECK_CONTEXTS]

    def fake_api(endpoint, **kwargs):
        return {"check_runs": check_runs}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "GREEN"
    assert len(failing) == 0
    assert len(pending) == 0


def test_evaluate_checks_missing_cd_authority_pending(monkeypatch):
    check_runs = [
        _make_check_run(name) for name in REQUIRED_CHECK_CONTEXTS
        if name != "Protect authoritative CD workflow"
    ]

    def fake_api(endpoint, **kwargs):
        return {"check_runs": check_runs}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "PENDING"
    assert "Protect authoritative CD workflow" in pending


def test_evaluate_checks_failing_cd_authority_red(monkeypatch):
    check_runs = []
    for name in REQUIRED_CHECK_CONTEXTS:
        if name == "Protect authoritative CD workflow":
            check_runs.append(_make_check_run(name, conclusion="failure", url="https://ci/job/1"))
        else:
            check_runs.append(_make_check_run(name))

    def fake_api(endpoint, **kwargs):
        return {"check_runs": check_runs}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "RED"
    assert len(failing) == 1
    assert failing[0]["name"] == "Protect authoritative CD workflow"


@pytest.mark.parametrize("conclusion", ["action_required", "stale", "startup_failure"])
def test_completed_nonaccepted_conclusion_is_red(monkeypatch, conclusion):
    check_runs = [_make_check_run(name) for name in REQUIRED_CHECK_CONTEXTS]
    check_runs[0] = _make_check_run(
        REQUIRED_CHECK_CONTEXTS[0],
        conclusion=conclusion,
        url="https://ci/job/terminal",
    )

    monkeypatch.setattr(
        "evaluate_ci_signal.github_api_request",
        lambda endpoint, **kwargs: {"check_runs": check_runs},
    )

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "RED"
    assert failing[0]["conclusion"] == conclusion
    assert pending == []


def test_neutral_and_skipped_are_accepted_terminal_conclusions(monkeypatch):
    check_runs = [_make_check_run(name) for name in REQUIRED_CHECK_CONTEXTS]
    check_runs[0] = _make_check_run(REQUIRED_CHECK_CONTEXTS[0], conclusion="neutral")
    check_runs[1] = _make_check_run(REQUIRED_CHECK_CONTEXTS[1], conclusion="skipped")

    monkeypatch.setattr(
        "evaluate_ci_signal.github_api_request",
        lambda endpoint, **kwargs: {"check_runs": check_runs},
    )

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "GREEN"
    assert failing == []
    assert pending == []


def test_untrusted_app_id_filtered_out(monkeypatch):
    """Check runs from a non-GitHub-Actions app should be filtered, leaving them PENDING."""
    # All runs from a different app ID should be ignored
    check_runs = [_make_check_run(name, app_id=99999) for name in REQUIRED_CHECK_CONTEXTS]

    def fake_api(endpoint, **kwargs):
        return {"check_runs": check_runs}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "PENDING"
    assert len(pending) == 12, "All 12 contexts should be pending when runs are untrusted"


def test_mixed_app_ids(monkeypatch):
    """Mix of trusted and untrusted runs: trusted pass, untrusted spoofed pass ignored."""
    check_runs = []
    for i, name in enumerate(REQUIRED_CHECK_CONTEXTS):
        if i == 0:
            # First context has only a spoofed run (wrong app_id)
            check_runs.append(_make_check_run(name, app_id=99999))
        else:
            check_runs.append(_make_check_run(name, app_id=GITHUB_ACTIONS_APP_ID))

    def fake_api(endpoint, **kwargs):
        return {"check_runs": check_runs}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    state, failing, pending = evaluate_checks("dummy_sha", "token", "repo")
    assert state == "PENDING"
    assert len(pending) == 1
    assert REQUIRED_CHECK_CONTEXTS[0] in pending


def test_verify_sha_still_current_match(monkeypatch):
    """SHA matches current HEAD — should return True."""
    def fake_api(endpoint, **kwargs):
        return {"number": 42, "head": {"sha": "abc123"}}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    assert verify_sha_still_current(42, "abc123", "token", "repo") is True


def test_verify_sha_still_current_stale(monkeypatch):
    """SHA doesn't match current HEAD — should return False."""
    def fake_api(endpoint, **kwargs):
        return {"number": 42, "head": {"sha": "def456"}}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)

    assert verify_sha_still_current(42, "abc123", "token", "repo") is False


def test_sync_labels_refuses_first_mutation_when_sha_is_stale(monkeypatch):
    calls = []

    def fake_api(endpoint, method="GET", **kwargs):
        calls.append((endpoint, method))
        return {"labels": [{"name": "agent:ci-red"}]}

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)
    monkeypatch.setattr(
        "evaluate_ci_signal.verify_sha_still_current",
        lambda *args, **kwargs: False,
    )

    assert sync_labels(42, "agent:ci-green", "abc123", "token", "repo") is False
    assert calls == [("issues/42", "GET")]


def test_sync_labels_rechecks_sha_before_every_mutation(monkeypatch):
    mutations = []
    sha_checks = []

    def fake_api(endpoint, method="GET", **kwargs):
        if endpoint == "issues/42":
            return {
                "labels": [
                    {"name": "agent:ci-red"},
                    {"name": "agent:awaiting-ci"},
                ]
            }
        mutations.append((endpoint, method))
        return {}

    def fake_sha_check(*args, **kwargs):
        sha_checks.append(args)
        return True

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)
    monkeypatch.setattr(
        "evaluate_ci_signal.verify_sha_still_current",
        fake_sha_check,
    )

    assert sync_labels(42, "agent:ci-green", "abc123", "token", "repo") is True
    assert len(mutations) == 3
    assert len(sha_checks) == 3


def test_transition_comment_refuses_post_when_sha_is_stale(monkeypatch):
    calls = []

    def fake_api(endpoint, method="GET", **kwargs):
        calls.append((endpoint, method))
        return []

    monkeypatch.setattr("evaluate_ci_signal.github_api_request", fake_api)
    monkeypatch.setattr(
        "evaluate_ci_signal.verify_sha_still_current",
        lambda *args, **kwargs: False,
    )

    result = post_transition_comment(
        42,
        "GREEN",
        "abc123",
        [],
        [],
        token="token",
        repo="repo",
    )
    assert result is False
    assert calls == [("issues/42/comments", "GET")]


if __name__ == "__main__":
    test_required_contexts_list()

    class SimpleMonkeyPatch:
        def setattr(self, target, val):
            mod_name, func_name = target.rsplit(".", 1)
            setattr(sys.modules[mod_name], func_name, val)

    mp = SimpleMonkeyPatch()
    test_evaluate_checks_all_green(mp)
    test_evaluate_checks_missing_cd_authority_pending(mp)
    test_evaluate_checks_failing_cd_authority_red(mp)
    print("All CI signal evaluator unit tests passed successfully!")
