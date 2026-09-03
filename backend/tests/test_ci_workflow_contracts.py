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
    "Concurrent Tenant Isolation": ("ci.yml", "rls-concurrency"),
    "Reproduce / Recover Stale Frontend Assets": (
        "ci.yml",
        "stale-deployment-recovery",
    ),
    "Responsive Acceptance Matrix": ("ci.yml", "responsive"),
    "Full Git History Secret Scan": ("history-secret-scan.yml", "history-secret-scan"),
    "Verify GitHub branch enforcement": (
        "branch-governance.yml",
        "verify-platform-branch-rules",
    ),
    "Validate promotion path": ("branch-governance.yml", "promotion-path"),
    "Protect authoritative CD workflow": (
        "branch-governance.yml",
        "workflow-authority",
    ),
}

LABEL_SENSITIVE_WORKFLOWS = {
    "ci.yml",
}

LABEL_INDEPENDENT_WORKFLOWS = {
    "history-secret-scan.yml",
    "branch-governance.yml",
}

ALL_RELEVANT_WORKFLOWS = (
    LABEL_SENSITIVE_WORKFLOWS | LABEL_INDEPENDENT_WORKFLOWS | {"mobile.yml"}
)

SELECTIVE_CI_JOBS = [
    "dependency-reproducibility",
    "backend",
    "frontend",
    "e2e",
    "production-container",
    "rls-concurrency",
    "stale-deployment-recovery",
    "responsive",
]


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
def test_label_sensitive_workflows_retain_labeled_trigger(filename):
    workflow = _load_workflow(filename)
    types = workflow["on"]["pull_request"]["types"]
    assert "labeled" in types
    assert "synchronize" in types
    assert "opened" in types


@pytest.mark.parametrize("filename", sorted(LABEL_INDEPENDENT_WORKFLOWS))
def test_label_independent_workflows_do_not_retrigger_on_labels(filename):
    workflow = _load_workflow(filename)
    types = workflow["on"]["pull_request"]["types"]
    assert "labeled" not in types
    assert "synchronize" in types
    assert "opened" in types


@pytest.mark.parametrize(
    "filename",
    sorted({"ci.yml", "branch-governance.yml", "history-secret-scan.yml"}),
)
def test_required_workflows_have_no_workflow_level_path_filtering(filename):
    workflow = _load_workflow(filename)
    triggers = workflow.get("on", {})
    for event in ("pull_request", "push"):
        if event in triggers and isinstance(triggers[event], dict):
            assert "paths" not in triggers[event]
            assert "paths-ignore" not in triggers[event]


@pytest.mark.parametrize("job_id", SELECTIVE_CI_JOBS)
def test_selective_ci_jobs_use_classifier_driven_job_level_conditions(job_id):
    workflow = _load_workflow("ci.yml")
    job = workflow["jobs"][job_id]
    assert "classify-scope" in job.get("needs", [])
    job_if = job.get("if", "")
    assert job_if, f"{job_id} must declare a job-level 'if' condition"
    assert job_if != "always()", f"{job_id} must not use always() at job level"
    assert "needs.classify-scope.result != 'success'" in job_if
    assert "needs.classify-scope.outputs.force_full != 'false'" in job_if


def test_ci_protected_push_trigger_remains_as_lightweight_cd_handoff():
    workflow = _load_workflow("ci.yml")
    triggers = workflow["on"]
    assert "push" in triggers
    assert set(triggers["push"]["branches"]) == {"main", "staging"}


def test_governance_workflow_event_contract():
    workflow = _load_workflow("branch-governance.yml")
    triggers = workflow.get("on", {})
    assert "pull_request" in triggers
    assert "push" in triggers
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"]["statuses"] == "read"

    promo_job = workflow["jobs"]["promotion-path"]
    assert "github.event_name == 'pull_request'" in promo_job.get("if", "")

    auth_job = workflow["jobs"]["workflow-authority"]
    assert "github.event_name == 'pull_request'" in auth_job.get("if", "")

    verify_job = workflow["jobs"]["verify-platform-branch-rules"]
    assert verify_job["name"] == "Verify GitHub branch enforcement"


def test_history_secret_scan_runs_on_introduction_not_again_on_protected_push():
    workflow = _load_workflow("history-secret-scan.yml")
    triggers = workflow["on"]
    assert "pull_request" in triggers
    assert "workflow_dispatch" in triggers
    assert "push" not in triggers

    job_if = workflow["jobs"]["history-secret-scan"]["if"]
    assert "github.base_ref == 'main'" in job_if
    assert "github.head_ref == 'staging'" in job_if


def test_mobile_ci_runs_at_pr_boundary_not_again_after_merge_or_promotion():
    workflow = _load_workflow("mobile.yml")
    triggers = workflow["on"]
    assert "pull_request" in triggers
    assert "push" not in triggers

    job_if = workflow["jobs"]["flutter-analyze-test"]["if"]
    assert "github.base_ref == 'main'" in job_if
    assert "github.head_ref == 'staging'" in job_if


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
    assert guard["env"]["GH_REPOSITORY"] == "${{ github.repository }}"
    assert "git rev-parse origin/staging" in guard["run"]
    assert 'if [ "$PR_HEAD_SHA" != "$CURRENT_STAGING_SHA" ]' in guard["run"]
    assert "Dentix CD - HF staging smoke" in guard["run"]
    assert 'if [ "$STAGING_SMOKE_STATE" != "success" ]' in guard["run"]
    assert "git diff --quiet origin/main -- .github/workflows/cd.yml" in guard["run"]
