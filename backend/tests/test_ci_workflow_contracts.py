from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SAFETY_POLICY_PATH = REPO_ROOT / ".safety-policy.yml"

LABEL_TRIGGERED_JOBS = {
    "ci.yml": (
        "classify-scope",
        "dependency-reproducibility",
        "backend",
        "frontend",
        "e2e",
        "production-container",
    ),
    "cross-tenant-http-postgres.yml": ("postgres-http-idor",),
    "rls-concurrency.yml": ("rls-concurrency",),
    "mobile-responsive.yml": ("responsive",),
    "stale-deployment-recovery.yml": ("stale-deployment-recovery",),
    "history-secret-scan.yml": ("history-secret-scan",),
    "branch-governance.yml": ("promotion-path", "workflow-authority"),
    "platform-branch-protection.yml": ("verify-platform-branch-rules",),
}

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
    "Validate promotion path": ("branch-governance.yml", "promotion-path"),
    "Protect authoritative CD workflow": ("branch-governance.yml", "workflow-authority"),
    "Verify GitHub branch enforcement": (
        "platform-branch-protection.yml",
        "verify-platform-branch-rules",
    ),
}

CONCURRENT_WORKFLOWS = {
    "ci.yml",
    "cross-tenant-http-postgres.yml",
    "rls-concurrency.yml",
    "mobile-responsive.yml",
    "stale-deployment-recovery.yml",
    "history-secret-scan.yml",
}


def _load_workflow(filename):
    with (WORKFLOW_DIR / filename).open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=yaml.BaseLoader)


@pytest.mark.parametrize(
    ("filename", "job_id"),
    [
        (filename, job_id)
        for filename, job_ids in LABEL_TRIGGERED_JOBS.items()
        for job_id in job_ids
    ],
)
def test_agent_label_events_use_distinct_noop_job_names(filename, job_id):
    workflow = _load_workflow(filename)
    assert "labeled" in workflow["on"]["pull_request"]["types"]

    job = workflow["jobs"][job_id]
    condition = job.get("if", "")
    name = job.get("name", "")

    assert "github.event.action != 'labeled'" in condition
    assert "startsWith(github.event.label.name, 'agent:')" in condition
    assert "Agent label no-op /" in name


@pytest.mark.parametrize("context", sorted(REQUIRED_CONTEXT_LOCATIONS))
def test_required_context_names_are_preserved_only_for_validation_events(context):
    filename, job_id = REQUIRED_CONTEXT_LOCATIONS[context]
    job_name = _load_workflow(filename)["jobs"][job_id]["name"]

    assert context in job_name
    assert f"Agent label no-op / {context}" in job_name


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


@pytest.mark.parametrize("filename", sorted(CONCURRENT_WORKFLOWS))
def test_agent_label_runs_cannot_cancel_validation_runs(filename):
    concurrency_group = _load_workflow(filename)["concurrency"]["group"]
    assert "github.event.label.name" in concurrency_group
    assert "'validation'" in concurrency_group


def test_mobile_responsive_runs_on_both_protected_push_branches():
    branches = _load_workflow("mobile-responsive.yml")["on"]["push"]["branches"]
    assert set(branches) == {"main", "staging"}


def test_authoritative_cd_context_materializes_and_guards_main_promotions():
    job = _load_workflow("branch-governance.yml")["jobs"]["workflow-authority"]

    assert "github.base_ref == 'staging'" not in job["if"]
    guard = job["steps"][1]
    assert guard["name"] == "Protect authoritative CD workflow"
    assert guard["env"]["PR_HEAD_SHA"] == (
        "${{ github.event.pull_request.head.sha }}"
    )
    assert "git rev-parse origin/staging" in guard["run"]
    assert 'if [ "$PR_HEAD_SHA" != "$CURRENT_STAGING_SHA" ]' in guard["run"]
    assert "git diff --quiet origin/main -- .github/workflows/cd.yml" in guard["run"]


def test_agent_ci_signal_uses_trusted_code_and_minimal_permissions():
    workflow = _load_workflow("agent-ci-signal.yml")
    assert workflow["permissions"] == {
        "contents": "read",
        "checks": "read",
        "issues": "write",
    }
    assert workflow["concurrency"] == {
        "group": "agent-ci-signal-${{ github.event.workflow_run.head_sha }}",
        "cancel-in-progress": "true",
    }

    checkout = workflow["jobs"]["signal-evaluator"]["steps"][0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"]["ref"] == "${{ github.event.repository.default_branch }}"
    assert checkout["with"]["persist-credentials"] == "false"
    assert checkout["with"]["sparse-checkout"].strip() == ".github/scripts"
