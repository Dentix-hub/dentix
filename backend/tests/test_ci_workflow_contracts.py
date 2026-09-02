from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SAFETY_POLICY_PATH = REPO_ROOT / ".safety-policy.yml"

REQUIRED_CONTEXT_LOCATIONS = {
    "Frozen Dependency Reproducibility": ("ci.yml", "dependency-reproducibility"),
    "Backend Tests + Security": ("ci.yml", "backend"),
    "Frontend Tests": ("ci.yml", "frontend"),
    "E2E Critical Path (Playwright)": ("ci.yml", "e2e"),
    "Validate Production Container": ("ci.yml", "production-container"),
    "Concurrent Tenant Isolation": ("rls-concurrency.yml", "rls-concurrency"),
    "Reproduce / Recover Stale Frontend Assets": (
        "stale-deployment-recovery.yml",
        "stale-deployment-recovery",
    ),
    "Responsive Acceptance Matrix": ("mobile-responsive.yml", "responsive"),
    "Full Git History Secret Scan": ("history-secret-scan.yml", "history-secret-scan"),
    "Verify GitHub branch enforcement": (
        "platform-branch-protection.yml",
        "verify-platform-branch-rules",
    ),
}

LABEL_SENSITIVE_WORKFLOWS = {
    "ci.yml",
    "cross-tenant-http-postgres.yml",
    "rls-concurrency.yml",
    "mobile-responsive.yml",
    "stale-deployment-recovery.yml",
    "history-secret-scan.yml",
    "platform-branch-protection.yml",
}

ALL_RELEVANT_WORKFLOWS = LABEL_SENSITIVE_WORKFLOWS | {"branch-governance.yml", "mobile.yml"}


def _load_workflow(filename):
    with (WORKFLOW_DIR / filename).open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=yaml.BaseLoader)


@pytest.mark.parametrize("context", sorted(REQUIRED_CONTEXT_LOCATIONS))
def test_required_context_names_are_static_and_exact(context):
    filename, job_id = REQUIRED_CONTEXT_LOCATIONS[context]
    job_name = _load_workflow(filename)["jobs"][job_id]["name"]
    assert job_name == context


@pytest.mark.parametrize("filename", sorted(ALL_RELEVANT_WORKFLOWS))
def test_workflows_have_no_agent_label_special_casing(filename):
    with (WORKFLOW_DIR / filename).open(encoding="utf-8") as stream:
        content = stream.read()

    assert ("agent" + ":") not in content
    assert ("Agent label" + " no-op") not in content
    assert ("startsWith" + "(github.event.label.name") not in content
    assert "github.event.label.name" not in content


@pytest.mark.parametrize("filename", sorted(LABEL_SENSITIVE_WORKFLOWS))
def test_legitimate_label_safety_remains_on_pr_workflows(filename):
    workflow = _load_workflow(filename)
    types = workflow["on"]["pull_request"]["types"]
    assert "labeled" in types
    assert "synchronize" in types
    assert "opened" in types


def test_safety_dependency_check_uses_fail_closed_retry_runner():
    backend_steps = _load_workflow("ci.yml")["jobs"]["backend"]["steps"]
    safety_step = next(
        step
        for step in backend_steps
        if step.get("name") == "Dependency vulnerability check — Safety"
    )

    assert safety_step["run"] == "python .github/scripts/run_safety_check.py"
    assert "continue-on-error" not in safety_step
    assert "|| true" not in safety_step["run"]


def test_cuda_toolkit_exception_is_scoped_and_time_bounded():
    with SAFETY_POLICY_PATH.open(encoding="utf-8") as stream:
        security_policy = yaml.load(stream, Loader=yaml.BaseLoader)["security"]

    exception = security_policy["ignore-vulnerabilities"]["SFTY-20260120-40557"]
    reason = exception["reason"].lower()

    assert exception["expires"] == "2026-09-30"
    assert "torch 2.13.0" in reason
    assert "gfx_hotspot" in reason
    assert "does not invoke" in reason
    assert security_policy["continue-on-vulnerability-error"] == "false"


def test_mobile_responsive_runs_on_both_protected_push_branches():
    branches = _load_workflow("mobile-responsive.yml")["on"]["push"]["branches"]
    assert set(branches) == {"main", "staging"}


def test_authoritative_cd_context_materializes_and_guards_main_promotions():
    workflow = _load_workflow("branch-governance.yml")
    assert "labeled" not in workflow["on"]["pull_request"]["types"]
    assert workflow["jobs"]["promotion-path"]["name"] == "Validate promotion path"

    job = workflow["jobs"]["workflow-authority"]
    assert job["name"] == "Protect authoritative CD workflow"
    assert "github.base_ref == 'staging'" not in job.get("if", "")
    guard = job["steps"][1]
    assert guard["name"] == "Protect authoritative CD workflow"
    assert guard["env"]["PR_HEAD_SHA"] == (
        "${{ github.event.pull_request.head.sha }}"
    )
    assert "git rev-parse origin/staging" in guard["run"]
    assert 'if [ "$PR_HEAD_SHA" != "$CURRENT_STAGING_SHA" ]' in guard["run"]
    assert "git diff --quiet origin/main -- .github/workflows/cd.yml" in guard["run"]
