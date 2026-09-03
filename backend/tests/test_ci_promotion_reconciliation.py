import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / ".github" / "scripts"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
sys.path.insert(0, str(SCRIPT_DIR.resolve()))

from classify_ci_scope import classify_files


def _workflow_text(filename: str) -> str:
    return (WORKFLOW_DIR / filename).read_text(encoding="utf-8")


def _workflow(filename: str):
    with (WORKFLOW_DIR / filename).open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=yaml.BaseLoader)


def test_reconciled_promotion_branch_reuses_validated_staging_ci():
    result = classify_files(
        ["backend/auth.py", ".github/workflows/ci.yml", "frontend/src/App.jsx"],
        event_name="pull_request",
        target_branch="main",
        source_branch="release/promotion-20260903",
    )
    assert not any(result.values())


def test_generic_release_branch_does_not_get_promotion_shortcut():
    result = classify_files(
        [".github/workflows/ci.yml"],
        event_name="pull_request",
        target_branch="main",
        source_branch="release/workflow-sync",
    )
    assert result["force_full"] is True
    assert result["workflow_governance"] is True


def test_high_risk_label_can_force_fresh_reconciled_promotion_ci():
    result = classify_files(
        ["frontend/src/App.jsx"],
        event_name="pull_request",
        target_branch="main",
        source_branch="release/promotion-20260903",
        labels=["risk:high-risk"],
    )
    assert result["force_full"] is True


def test_governance_proves_reconciled_promotion_provenance_and_tree_identity():
    workflow = _workflow("branch-governance.yml")
    guard = workflow["jobs"]["workflow-authority"]["steps"][1]["run"]

    assert '[[ "$HEAD_BRANCH" == release/promotion-* ]]' in guard
    assert 'PR_PARENT_SHA="$(git rev-parse "${PR_HEAD_SHA}^")"' in guard
    assert 'if [ "$PR_PARENT_SHA" != "$CURRENT_MAIN_SHA" ]' in guard
    assert 'PR_TREE_SHA="$(git rev-parse "${PR_HEAD_SHA}^{tree}")"' in guard
    assert 'STAGING_TREE_SHA="$(git rev-parse "${CURRENT_STAGING_SHA}^{tree}")"' in guard
    assert 'if [ "$PR_TREE_SHA" != "$STAGING_TREE_SHA" ]' in guard
    assert "Dentix CD - HF staging smoke" in guard
    assert 'if [ "$STAGING_SMOKE_STATE" != "success" ]' in guard
    assert "git diff --quiet origin/main origin/staging -- .github/workflows/cd.yml" in guard


def test_duplicate_secret_and_flutter_work_are_skipped_only_for_trusted_promotion_family():
    history_job_if = _workflow("history-secret-scan.yml")["jobs"]["history-secret-scan"]["if"]
    mobile_job_if = _workflow("mobile.yml")["jobs"]["flutter-analyze-test"]["if"]

    for expression in (history_job_if, mobile_job_if):
        assert "github.base_ref == 'main'" in expression
        assert "github.head_ref == 'staging'" in expression
        assert "startsWith(github.head_ref, 'release/promotion-')" in expression


def test_required_workflow_names_remain_unchanged():
    assert _workflow("branch-governance.yml")["jobs"]["promotion-path"]["name"] == "Validate promotion path"
    assert _workflow("branch-governance.yml")["jobs"]["workflow-authority"]["name"] == "Protect authoritative CD workflow"
    assert _workflow("history-secret-scan.yml")["jobs"]["history-secret-scan"]["name"] == "Full Git History Secret Scan"
