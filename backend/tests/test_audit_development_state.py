"""
Deterministic Unit Tests for Live Development State Auditor
============================================================
Validates read-only safety, error propagation, truthful status classification,
and strict qualification mode in scripts/audit_development_state.py.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDITOR_PATH = REPO_ROOT / "scripts" / "audit_development_state.py"

spec = importlib.util.spec_from_file_location("audit_development_state", AUDITOR_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load auditor module from {AUDITOR_PATH}")
auditor_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor_mod)


@pytest.fixture
def mock_clean_local_state():
    return {
        "current_branch": "chore/workflow-v3-movement-0",
        "head_sha": "dc0ba2fc",
        "is_clean": True,
        "uncommitted_lines": [],
        "local_origin_staging": "65be3b70",
        "local_origin_main": "86fbf612",
        "local_branches": [
            {"name": "chore/workflow-v3-movement-0", "sha": "dc0ba2fc", "ahead_vs_staging": 2, "behind_vs_staging": 0}
        ],
        "errors": [],
    }


def test_all_commands_succeed_returns_live(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in to github.com"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 0, '{"name":"main","sha":"86fbf612"}\n{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 0, "[]"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare/main...staging" in cmd_str:
            return 0, '{"files":[{"filename":"AGENTS.md","status":"modified"}]}'
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)

        assert res["status"] == "REMOTE_AUDIT_LIVE"
        assert res["remote_main_sha"] == "86fbf612"
        assert res["remote_staging_sha"] == "65be3b70"
        assert len(res["errors"]) == 0
        assert res["open_prs"] == []
        assert res["blocked_issues"] == []


def test_gh_unavailable_returns_failed(mock_clean_local_state):
    with patch("shutil.which", return_value=None):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_FAILED"
        assert "gh CLI not found" in res["reason"]


def test_auth_failure_returns_failed(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        if "auth status" in " ".join(cmd):
            return 1, "You are not logged in to any GitHub hosts."
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_FAILED"
        assert "not authenticated" in res["reason"]


def test_branch_query_fails_returns_partial(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 1, "API rate limit exceeded"
        if "pr list" in cmd_str:
            return 0, "[]"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare" in cmd_str:
            return 0, '{"files":[]}'
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_PARTIAL"
        assert any("Failed to query remote branches" in e for e in res["errors"])


def test_missing_main_or_staging_sha_returns_partial(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            # Only returns staging, main is missing
            return 0, '{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 0, "[]"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare" in cmd_str:
            return 0, '{"files":[]}'
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_PARTIAL"
        assert any("'main' not found" in e for e in res["errors"])


def test_pr_query_fails_returns_partial_and_none_prs(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 0, '{"name":"main","sha":"86fbf612"}\n{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 1, "GraphQL error: network timeout"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare" in cmd_str:
            return 0, '{"files":[]}'
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_PARTIAL"
        assert res["open_prs"] is None
        assert any("Failed to query open PRs" in e for e in res["errors"])


def test_issue_query_fails_returns_partial_and_none_issues(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 0, '{"name":"main","sha":"86fbf612"}\n{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 0, "[]"
        if "issue list" in cmd_str:
            return 1, "Internal server error"
        if "compare" in cmd_str:
            return 0, '{"files":[]}'
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_PARTIAL"
        assert res["blocked_issues"] is None
        assert any("Failed to query open issues" in e for e in res["errors"])


def test_compare_query_fails_returns_partial(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 0, '{"name":"main","sha":"86fbf612"}\n{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 0, "[]"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare" in cmd_str:
            return 1, "Comparison unavailable"
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_PARTIAL"
        assert any("Failed to compare remote main...staging" in e for e in res["errors"])


def test_malformed_json_returns_partial(mock_clean_local_state):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 0, '{"name":"main","sha":"86fbf612"}\n{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 0, "NOT VALID JSON"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare" in cmd_str:
            return 0, '{"files":[]}'
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        res = auditor_mod.audit_remote_github(REPO_ROOT, mock_clean_local_state)
        assert res["status"] == "REMOTE_AUDIT_PARTIAL"
        assert res["open_prs"] is None
        assert any("Malformed open PR JSON" in e for e in res["errors"])


def test_strict_mode_returns_nonzero_on_partial_audit(capsys):
    with patch.object(auditor_mod, "audit_local_state", return_value={"errors": [], "current_branch": "b", "head_sha": "1", "is_clean": True, "local_origin_staging": "1", "local_origin_main": "2", "local_branches": []}), \
         patch.object(auditor_mod, "audit_worktrees", return_value=([], [])), \
         patch.object(auditor_mod, "audit_remote_github", return_value={"status": "REMOTE_AUDIT_PARTIAL", "reason": "rate limit", "errors": ["rate limit"], "open_prs": None, "blocked_issues": None, "stale_tracking_refs": []}):
        code = auditor_mod.main(["--strict"])
        assert code == 1
        captured = capsys.readouterr().out
        assert "STRICT QUALIFICATION FAILURE" in captured


def test_informational_mode_labels_partial_state_truthfully(capsys):
    with patch.object(auditor_mod, "audit_local_state", return_value={"errors": [], "current_branch": "b", "head_sha": "1", "is_clean": True, "local_origin_staging": "1", "local_origin_main": "2", "local_branches": []}), \
         patch.object(auditor_mod, "audit_worktrees", return_value=([], [])), \
         patch.object(auditor_mod, "audit_remote_github", return_value={"status": "REMOTE_AUDIT_PARTIAL", "reason": "rate limit", "errors": ["rate limit"], "open_prs": None, "blocked_issues": None, "stale_tracking_refs": []}):
        code = auditor_mod.main([])
        assert code == 0
        captured = capsys.readouterr().out
        assert "Audit completed with warnings/partial state" in captured
        assert "Audit completed successfully" not in captured


def test_no_mutating_command_executed():
    executed_commands = []

    def mock_run(cmd, cwd=None):
        executed_commands.append(cmd)
        cmd_str = " ".join(cmd)
        if "branch --show-current" in cmd_str:
            return 0, "chore/workflow-v3-movement-0"
        if "rev-parse HEAD" in cmd_str:
            return 0, "dc0ba2fc"
        if "status --porcelain" in cmd_str:
            return 0, ""
        if "rev-parse origin" in cmd_str:
            return 0, "65be3b70"
        if "for-each-ref" in cmd_str:
            return 0, "main 86fbf612\nstaging 65be3b70"
        if "worktree" in cmd_str:
            return 0, ""
        if "auth status" in cmd_str:
            return 0, "Logged in"
        if "repo view" in cmd_str:
            return 0, "Dentix-hub/dentix"
        if "branches" in cmd_str:
            return 0, '{"name":"main","sha":"86fbf612"}\n{"name":"staging","sha":"65be3b70"}'
        if "pr list" in cmd_str:
            return 0, "[]"
        if "issue list" in cmd_str:
            return 0, "[]"
        if "compare" in cmd_str:
            return 0, '{"files":[]}'
        return 0, "0"

    prohibited_verbs = {
        "push", "fetch", "pull", "commit", "merge", "rebase", "checkout",
        "reset", "revert", "delete", "rm", "-d", "-D", "pr create", "pr merge",
        "pr close", "issue create", "issue close"
    }

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        auditor_mod.main([])

        for cmd in executed_commands:
            cmd_str = " ".join(cmd).lower()
            for verb in prohibited_verbs:
                assert f" {verb} " not in f" {cmd_str} ", (
                    f"Prohibited mutating verb '{verb}' detected in executed command: {cmd_str}"
                )


def test_ahead_rev_list_failure_records_error_and_fails_strict(capsys):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "branch --show-current" in cmd_str:
            return 0, "chore/test"
        if "rev-parse HEAD" in cmd_str:
            return 0, "11112222"
        if "status --porcelain" in cmd_str:
            return 0, ""
        if "rev-parse origin" in cmd_str:
            return 0, "65be3b70"
        if "for-each-ref" in cmd_str:
            return 0, "feat/branch1 12345678"
        if "staging..feat/branch1" in cmd_str:
            return 128, "fatal: bad object staging"
        if "feat/branch1..staging" in cmd_str:
            return 0, "0"
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run):
        state = auditor_mod.audit_local_state(Path("."))
        assert any("git rev-list --count staging..feat/branch1 failed" in e for e in state["errors"])
        assert state["local_branches"][0]["ahead_vs_staging"] == -1

    with patch.object(auditor_mod, "audit_local_state", return_value=state), \
         patch.object(auditor_mod, "audit_worktrees", return_value=([], [])), \
         patch.object(auditor_mod, "audit_remote_github", return_value={"status": "REMOTE_AUDIT_LIVE", "open_prs": [], "blocked_issues": [], "stale_tracking_refs": [], "repo_name": "r", "remote_branches_count": 1, "remote_main_sha": "a", "remote_staging_sha": "b"}):
        code = auditor_mod.main(["--strict"])
        assert code == 1
        assert "STRICT QUALIFICATION FAILURE" in capsys.readouterr().out


def test_behind_rev_list_failure_records_error_and_fails_strict(capsys):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "branch --show-current" in cmd_str:
            return 0, "chore/test"
        if "rev-parse HEAD" in cmd_str:
            return 0, "11112222"
        if "status --porcelain" in cmd_str:
            return 0, ""
        if "rev-parse origin" in cmd_str:
            return 0, "65be3b70"
        if "for-each-ref" in cmd_str:
            return 0, "feat/branch1 12345678"
        if "staging..feat/branch1" in cmd_str:
            return 0, "0"
        if "feat/branch1..staging" in cmd_str:
            return 128, "fatal: bad object staging"
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run):
        state = auditor_mod.audit_local_state(Path("."))
        assert any("git rev-list --count feat/branch1..staging failed" in e for e in state["errors"])
        assert state["local_branches"][0]["behind_vs_staging"] == -1

    with patch.object(auditor_mod, "audit_local_state", return_value=state), \
         patch.object(auditor_mod, "audit_worktrees", return_value=([], [])), \
         patch.object(auditor_mod, "audit_remote_github", return_value={"status": "REMOTE_AUDIT_LIVE", "open_prs": [], "blocked_issues": [], "stale_tracking_refs": [], "repo_name": "r", "remote_branches_count": 1, "remote_main_sha": "a", "remote_staging_sha": "b"}):
        code = auditor_mod.main(["--strict"])
        assert code == 1
        assert "STRICT QUALIFICATION FAILURE" in capsys.readouterr().out


def test_malformed_branch_inventory_records_error_and_fails_strict(capsys):
    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "for-each-ref" in cmd_str:
            return 0, "corrupt_branch_without_sha"
        if "branch --show-current" in cmd_str:
            return 0, "chore/test"
        if "rev-parse HEAD" in cmd_str:
            return 0, "11112222"
        if "status --porcelain" in cmd_str:
            return 0, ""
        if "rev-parse origin" in cmd_str:
            return 0, "65be3b70"
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run):
        state = auditor_mod.audit_local_state(Path("."))
        assert any("Missing SHA for branch 'corrupt_branch_without_sha'" in e for e in state["errors"])

    with patch.object(auditor_mod, "audit_local_state", return_value=state), \
         patch.object(auditor_mod, "audit_worktrees", return_value=([], [])), \
         patch.object(auditor_mod, "audit_remote_github", return_value={"status": "REMOTE_AUDIT_LIVE", "open_prs": [], "blocked_issues": [], "stale_tracking_refs": [], "repo_name": "r", "remote_branches_count": 1, "remote_main_sha": "a", "remote_staging_sha": "b"}):
        code = auditor_mod.main(["--strict"])
        assert code == 1
        assert "STRICT QUALIFICATION FAILURE" in capsys.readouterr().out


def test_worktree_status_failure_records_error_and_fails_strict(capsys):
    mock_wt_path = Path("/mock/worktree1")

    def mock_run(cmd, cwd=None):
        cmd_str = " ".join(cmd)
        if "worktree list" in cmd_str:
            return 0, f"worktree {mock_wt_path.as_posix()}\nHEAD aabb\nbranch refs/heads/wt-branch\n"
        if "status --porcelain" in cmd_str:
            return 128, "fatal: error reading status"
        return 0, ""

    with patch.object(auditor_mod, "run_cmd", side_effect=mock_run), \
         patch.object(Path, "exists", return_value=True):
        worktrees, wt_errors = auditor_mod.audit_worktrees(Path("."))
        assert len(worktrees) == 1
        assert worktrees[0]["status_failed"] is True
        assert any("git status --porcelain failed for worktree" in e for e in wt_errors)

    with patch.object(auditor_mod, "audit_local_state", return_value={"errors": [], "current_branch": "b", "head_sha": "1", "is_clean": True, "local_origin_staging": "1", "local_origin_main": "2", "local_branches": []}), \
         patch.object(auditor_mod, "audit_worktrees", return_value=(worktrees, wt_errors)), \
         patch.object(auditor_mod, "audit_remote_github", return_value={"status": "REMOTE_AUDIT_LIVE", "open_prs": [], "blocked_issues": [], "stale_tracking_refs": [], "repo_name": "r", "remote_branches_count": 1, "remote_main_sha": "a", "remote_staging_sha": "b"}):
        code = auditor_mod.main(["--strict"])
        assert code == 1
        assert "STRICT QUALIFICATION FAILURE" in capsys.readouterr().out
