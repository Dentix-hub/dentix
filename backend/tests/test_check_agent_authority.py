"""
Tests for DENTIX Static Authority Linter (.github/scripts/check_agent_authority.py)
==================================================================================
Validates the 4-skill native architecture, retired skill detection,
authority pointer validation, classification rules, and governance checks.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LINTER_PATH = REPO_ROOT / ".github" / "scripts" / "check_agent_authority.py"

spec = importlib.util.spec_from_file_location("check_agent_authority", LINTER_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load linter module from {LINTER_PATH}")
linter_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linter_mod)
run_linter = linter_mod.run_linter

APPROVED_SKILLS = list(linter_mod.APPROVED_NATIVE_SKILLS)
RETIRED_SKILLS = list(linter_mod.RETIRED_SKILLS)


def create_valid_fixture(root: Path) -> None:
    """Create a minimal, valid DENTIX authority fixture with exactly 4 approved skills."""
    # Canonical files
    (root / "PROJECT_STANDARDS.md").write_text("# Project Standards\nArchitecture authority.\n", encoding="utf-8")

    (root / "docs" / "engineering").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "product").mkdir(parents=True, exist_ok=True)

    (root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Development Workflow\nSole development lifecycle authority.\n",
        encoding="utf-8",
    )

    (root / "AGENTS.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Instructions\n\n"
        "## 1. Authority\n\n"
        "Architecture → `PROJECT_STANDARDS.md`\n"
        "Lifecycle → `docs/engineering/DEVELOPMENT_WORKFLOW.md`\n\n"
        "## 2. HARD Invariants\n\nTenant isolation, RBAC, privacy, clinical integrity, financial integrity.\n",
        encoding="utf-8",
    )

    # Create exactly the 4 approved skills
    for skill_name in APPROVED_SKILLS:
        skill_dir = root / ".agents" / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: {skill_name} skill\n---\n# Content\n",
            encoding="utf-8",
        )

    (root / ".agents" / "README.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Catalog\n\n## Skill Catalog (4 Native Skills)\n\n"
        + "\n".join(f"- `{s}`: Description." for s in APPROVED_SKILLS)
        + "\n",
        encoding="utf-8",
    )

    (root / "docs" / "AI_AGENT_STACK.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# AI Stack\n\n"
        "Lifecycle → `docs/engineering/DEVELOPMENT_WORKFLOW.md`\n\n"
        "## Native DENTIX Skills (4)\n\n"
        + "\n".join(f"- `{s}`" for s in APPROVED_SKILLS)
        + "\n",
        encoding="utf-8",
    )

    # Historical files with required headers
    historical_header = (
        "<!-- STATUS: HISTORICAL / NON-AUTHORITATIVE -->\n"
        "<!-- CLASSIFICATION: HISTORICAL -->\n"
        "# STATUS: HISTORICAL / NON-AUTHORITATIVE\n"
        "> Archived.\n\n"
    )
    (root / "docs" / "soul.md").write_text(historical_header + "# Soul\n", encoding="utf-8")
    (root / "docs" / "tttt.md").write_text(historical_header + "# Scratch\n", encoding="utf-8")
    (root / "docs" / "engineering" / "DENTIX_WORKFLOW_V2_1_PHASE7_PILOT_EVIDENCE.md").write_text(
        historical_header + "# Pilot\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "ODONTOGRAM_VNEXT_TICKET_GRAPH.md").write_text(
        historical_header + "# Ticket Graph\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "M3A_PILOT_B_ACCEPTANCE.md").write_text(
        historical_header + "# Pilot B Acceptance\n", encoding="utf-8"
    )
    (root / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md").write_text(
        historical_header + "# Master Plan\n", encoding="utf-8"
    )

    # Classified documents
    (root / "docs" / "AI_GOVERNANCE_RULES.md").write_text(
        "<!-- CLASSIFICATION: RUNTIME-AI -->\n# AI Rules\n", encoding="utf-8"
    )
    (root / "docs" / "HERMES_AGENT_GUIDE.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Technical Guide\n", encoding="utf-8"
    )
    (root / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md").write_text(
        "# Odontogram Spec\n<!-- CLASSIFICATION: PRODUCT-SPEC -->\n", encoding="utf-8"
    )
    (root / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md").write_text(
        "# Traceability Matrix\n<!-- CLASSIFICATION: PRODUCT-SPEC -->\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "BRANCH_DISPOSITION_LEDGER.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Ledger\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "CLINICAL_CHART_DISPOSITION.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Disposition\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "BRANCH_CLEANUP_INSTRUCTIONS.md").write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Branch Cleanup\n", encoding="utf-8"
    )

    # External skills provenance artifacts
    real_lock = REPO_ROOT / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    real_verifier = REPO_ROOT / "scripts" / "verify_external_skills.py"
    shutil.copy2(real_lock, root / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(real_verifier, root / "scripts" / "verify_external_skills.py")
    (root / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md").write_text(
        historical_header
        + "# Completed V3 Plan\n\n## Movement 2\nPrerequisite Gate: EXTERNAL_SKILL_PROVENANCE = PASS\n",
        encoding="utf-8",
    )


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        create_valid_fixture(tmp_path)
        yield tmp_path


# ==============================================================================
# Core: Valid fixture passes
# ==============================================================================


def test_valid_canonical_fixture_passes(temp_repo):
    code, failures, skill_count = run_linter(temp_repo)
    assert code == 0, f"Expected 0, got failures: {failures}"
    assert len(failures) == 0
    assert skill_count == 4


# ==============================================================================
# Exact native skill set enforcement
# ==============================================================================


def test_exact_skill_set_unexpected_skill_fails(temp_repo):
    """Adding a 5th skill outside the approved set must fail."""
    extra_dir = temp_repo / ".agents" / "skills" / "dentix-extra-skill"
    extra_dir.mkdir(parents=True, exist_ok=True)
    (extra_dir / "SKILL.md").write_text("---\nname: dentix-extra-skill\ndescription: extra\n---\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("Unexpected native skill(s)" in f and "dentix-extra-skill" in f for f in failures)


def test_exact_skill_set_missing_approved_skill_fails(temp_repo):
    """Removing an approved skill must fail."""
    shutil.rmtree(temp_repo / ".agents" / "skills" / "dentix-code-review")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("Missing approved native skill(s)" in f and "dentix-code-review" in f for f in failures)


def test_exact_skill_set_retired_skill_on_disk_fails(temp_repo):
    """A retired skill directory on disk must fail."""
    retired_dir = temp_repo / ".agents" / "skills" / "dentix-orchestration"
    retired_dir.mkdir(parents=True, exist_ok=True)
    (retired_dir / "SKILL.md").write_text("---\nname: dentix-orchestration\ndescription: old\n---\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("Unexpected native skill(s)" in f and "dentix-orchestration" in f for f in failures)


# ==============================================================================
# Retired skill reference detection
# ==============================================================================


@pytest.mark.parametrize("retired_skill", RETIRED_SKILLS)
def test_retired_skill_in_agents_md_fails(temp_repo, retired_skill):
    """Any retired skill name in AGENTS.md must fail."""
    agents = temp_repo / "AGENTS.md"
    content = agents.read_text(encoding="utf-8")
    agents.write_text(content + f"\nActivate `{retired_skill}` for debugging.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any(
        f"references retired skill '{retired_skill}'" in f and "AGENTS.md" in f
        for f in failures
    )


def test_retired_skill_in_ai_agent_stack_fails(temp_repo):
    """Retired skill reference in AI_AGENT_STACK.md must fail."""
    stack = temp_repo / "docs" / "AI_AGENT_STACK.md"
    content = stack.read_text(encoding="utf-8")
    stack.write_text(content + "\nUse `dentix-backend-fastapi` for backend work.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("references retired skill 'dentix-backend-fastapi'" in f for f in failures)


def test_retired_skill_in_historical_doc_does_not_fail(temp_repo):
    """Retired skill references in HISTORICAL docs are allowed."""
    hist = temp_repo / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md"
    content = hist.read_text(encoding="utf-8")
    hist.write_text(content + "\nUsed dentix-orchestration for coordination.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    retired_ref_failures = [f for f in failures if "references retired skill" in f]
    assert len(retired_ref_failures) == 0
    assert code == 0


def test_retired_skill_in_other_active_doc_fails(temp_repo):
    """Any other classified ACTIVE document referencing a retired skill must fail."""
    guide = temp_repo / "docs" / "HERMES_AGENT_GUIDE.md"
    content = guide.read_text(encoding="utf-8")
    guide.write_text(content + "\nUse `dentix-orchestration` for planning.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any(
        "references retired skill 'dentix-orchestration'" in f and "HERMES_AGENT_GUIDE.md" in f
        for f in failures
    )


def test_retired_skill_in_active_template_fails(temp_repo):
    """An active agent issue template referencing a retired skill must fail."""
    tpl_dir = temp_repo / ".github" / "ISSUE_TEMPLATE"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    (tpl_dir / "dentix-agent-task.yml").write_text(
        "name: Task\nbody:\n  - type: input\n    placeholder: dentix-systematic-debugging\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any(
        "references retired skill 'dentix-systematic-debugging'" in f and "dentix-agent-task.yml" in f
        for f in failures
    )


def test_retired_skill_in_product_spec_does_not_fail(temp_repo):
    """Product spec documents are allowed to preserve historical mentions."""
    spec = temp_repo / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md"
    content = spec.read_text(encoding="utf-8")
    spec.write_text(content + "\nHistorical notes mention dentix-frontend-react.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    retired_ref_failures = [f for f in failures if "references retired skill" in f]
    assert len(retired_ref_failures) == 0
    assert code == 0


# ==============================================================================
# Authority pointer validation
# ==============================================================================


def test_missing_project_standards_ref_fails(temp_repo):
    agents = temp_repo / "AGENTS.md"
    agents.write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Instructions\n\nLifecycle → DEVELOPMENT_WORKFLOW.md\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("missing reference to 'PROJECT_STANDARDS.md'" in f for f in failures)


def test_missing_workflow_ref_fails(temp_repo):
    agents = temp_repo / "AGENTS.md"
    agents.write_text(
        "<!-- CLASSIFICATION: ACTIVE -->\n# Instructions\n\nArchitecture → PROJECT_STANDARDS.md\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("missing reference to 'DEVELOPMENT_WORKFLOW.md'" in f for f in failures)


# ==============================================================================
# Skill catalog bidirectional matching
# ==============================================================================


def test_missing_skill_from_catalog_fails(temp_repo):
    extra_dir = temp_repo / ".agents" / "skills" / "dentix-new-valid"
    extra_dir.mkdir(parents=True, exist_ok=True)
    (extra_dir / "SKILL.md").write_text("---\nname: dentix-new-valid\ndescription: new\n---\nContent\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("exists on disk but is not cataloged" in f for f in failures)


def test_catalog_entry_without_directory_fails(temp_repo):
    readme = temp_repo / ".agents" / "README.md"
    content = readme.read_text(encoding="utf-8")
    readme.write_text(content + "\n- `dentix-ghost-skill`: Non-existent\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("does not exist as a directory" in f for f in failures)


# ==============================================================================
# Workflow authority checks
# ==============================================================================


def test_missing_development_workflow_fails(temp_repo):
    (temp_repo / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").unlink()
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("DEVELOPMENT_WORKFLOW.md" in f for f in failures)


def test_development_workflow_described_as_subordinate_fails(temp_repo):
    agents = temp_repo / "AGENTS.md"
    content = agents.read_text(encoding="utf-8")
    agents.write_text(content + "\nNotice: DEVELOPMENT_WORKFLOW.md is optional for quick fixes.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("describes 'docs/engineering/DEVELOPMENT_WORKFLOW.md' as optional or subordinate" in f for f in failures)


# ==============================================================================
# Obsolete paths and CI signal checks
# ==============================================================================


def test_stale_agent_path_in_active_authority_fails(temp_repo):
    agents_path = temp_repo / "AGENTS.md"
    content = agents_path.read_text(encoding="utf-8")
    agents_path.write_text(content + "\nLegacy path: .agent/workflows/tdd.md\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("obsolete '.agent/' reference" in f for f in failures)


def test_retired_ci_signal_in_active_authority_fails(temp_repo):
    agents_path = temp_repo / "AGENTS.md"
    content = agents_path.read_text(encoding="utf-8")
    agents_path.write_text(content + "\nSignal: agent-ci-signal.yml\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("retired 'agent-ci-signal' reference" in f for f in failures)


# ==============================================================================
# Hardcoded coverage checks
# ==============================================================================


def test_hardcoded_skill_coverage_threshold_fails(temp_repo):
    skill_file = temp_repo / ".agents" / "skills" / "dentix-code-review" / "SKILL.md"
    skill_file.write_text(
        "---\nname: dentix-code-review\ndescription: skill\n---\n"
        "Must maintain 80% coverage.\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("hard-codes coverage percentage" in f for f in failures)


# ==============================================================================
# Historical header checks
# ==============================================================================


def test_missing_historical_header_fails(temp_repo):
    soul_file = temp_repo / "docs" / "soul.md"
    soul_file.write_text("# Soul\nNo archive header here.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("missing mandatory 'STATUS: HISTORICAL / NON-AUTHORITATIVE'" in f for f in failures)


def test_completed_v3_plan_cannot_claim_active_workflow_authority(temp_repo):
    plan = temp_repo / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md"
    content = plan.read_text(encoding="utf-8")
    plan.write_text(
        content + "\nThis plan establishes one lean DENTIX development workflow.\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("still claims active workflow authority" in f for f in failures)


# ==============================================================================
# Document classification checks
# ==============================================================================


@pytest.mark.parametrize(
    "classification",
    ["ARCHITECTURE-REFERENCE", "ENGINEERING-RUNBOOK", "NOT-ACTIVE", "ACTIVE-REFERENCE"],
)
def test_unsupported_document_classification_fails(temp_repo, classification):
    guide = temp_repo / "docs" / "HERMES_AGENT_GUIDE.md"
    guide.write_text(
        f"<!-- CLASSIFICATION: {classification} -->\n# Technical Guide\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("HERMES_AGENT_GUIDE.md" in f and "unsupported classification" in f for f in failures)


def test_missing_document_classification_marker_fails(temp_repo):
    guide = temp_repo / "docs" / "HERMES_AGENT_GUIDE.md"
    guide.write_text("# Technical Guide\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("HERMES_AGENT_GUIDE.md" in f and "missing canonical classification marker" in f for f in failures)


def test_active_doc_claiming_master_plan_execution_authority_fails(temp_repo):
    spec = temp_repo / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md"
    spec.write_text(
        "<!-- CLASSIFICATION: PRODUCT-SPEC -->\n# Odontogram Spec\nThis derives from the authoritative master plan.\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("improperly describes legacy master plan as an active execution/source authority" in f for f in failures)


# ==============================================================================
# External skills provenance checks
# ==============================================================================


def test_missing_external_skills_lock_fails(temp_repo):
    (temp_repo / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json").unlink()
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("EXTERNAL_SKILLS_LOCK.json" in f and "Missing" in f for f in failures)


def test_missing_delegate_skill_from_lock_fails(temp_repo):
    lock_file = temp_repo / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    data = json.loads(lock_file.read_text(encoding="utf-8"))
    del data["skills"]["codex-delegate"]
    lock_file.write_text(json.dumps(data), encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("codex-delegate" in f and "missing" in f.lower() for f in failures)


def test_missing_provenance_verifier_fails(temp_repo):
    (temp_repo / "scripts" / "verify_external_skills.py").unlink()
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("verify_external_skills.py" in f and "Missing" in f for f in failures)


def test_external_skills_lock_malformed_schema_fails(temp_repo):
    lock_file = temp_repo / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    data = json.loads(lock_file.read_text(encoding="utf-8"))
    data["unexpected_root_key"] = "prohibited"
    lock_file.write_text(json.dumps(data), encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("Unexpected root field(s)" in f for f in failures)


def test_external_skills_lock_canonical_pin_drift_fails(temp_repo):
    lock_file = temp_repo / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    data = json.loads(lock_file.read_text(encoding="utf-8"))
    data["source"]["pinned_commit"] = "0000000000000000000000000000000000000000"
    lock_file.write_text(json.dumps(data), encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("canonical pinned commit" in f for f in failures)


def test_plan_missing_external_skill_provenance_gate_fails(temp_repo):
    plan_file = temp_repo / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md"
    plan_file.write_text("# Plan\nMovement 2 without gate.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("EXTERNAL_SKILL_PROVENANCE = PASS" in f for f in failures)


# ==============================================================================
# Broken skill directory checks
# ==============================================================================


def test_broken_skill_directory_missing_skill_md_fails(temp_repo):
    broken_dir = temp_repo / ".agents" / "skills" / "dentix-broken-skill"
    broken_dir.mkdir(parents=True, exist_ok=True)
    # Intentionally do not create SKILL.md inside broken_dir
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("missing required 'SKILL.md'" in f for f in failures)


# ==============================================================================
# Product spec files are optional (not agent governance)
# ==============================================================================


def test_missing_product_specs_does_not_fail(temp_repo):
    """Product spec files are optional — their absence should not cause linter failure."""
    (temp_repo / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md").unlink()
    (temp_repo / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md").unlink()
    code, failures, _ = run_linter(temp_repo)
    assert code == 0, f"Expected 0, got failures: {failures}"


# ==============================================================================
# Real repository conformance test
# ==============================================================================


def test_real_repository_conforms():
    """Verify the actual DENTIX repository passes the linter."""
    root = Path(__file__).resolve().parent.parent.parent
    code, failures, skill_count = run_linter(root)
    assert code == 0, f"Real repository linter failures: {failures}"
    assert skill_count == 4
