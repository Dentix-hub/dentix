"""
Tests for DENTIX Static Authority Linter (.github/scripts/check_agent_authority.py)
==================================================================================
Validates deterministic detection of the canonical nine-layer authority hierarchy,
bidirectional skill catalog integrity, coverage ownership, and classification rules.
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
check_orchestration_authority_links = linter_mod.check_orchestration_authority_links

CANONICAL_HIERARCHY_TEXT = """1. Non-negotiable safety, tenant isolation, RBAC, data integrity, privacy, clinical integrity, and financial integrity constraints.
2. Explicit current user requirement or approved implementation plan (within safety constraints).
3. `PROJECT_STANDARDS.md` (architecture authority).
4. `docs/engineering/DEVELOPMENT_WORKFLOW.md` (development lifecycle authority).
5. This `AGENTS.md` (cross-runtime execution and safety contract).
6. Active product / domain specifications.
7. Relevant `.agents/skills/` instructions.
8. External skills (optional methodology / transport only).
9. General engineering conventions."""


def create_valid_fixture(root: Path) -> None:
    """Create a minimal, valid DENTIX authority fixture in a temporary directory."""
    # Canonical files
    (root / "PROJECT_STANDARDS.md").write_text("# Project Standards\nArchitecture authority.\n", encoding="utf-8")

    (root / "docs" / "engineering").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "product").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "remediation").mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "skills" / "dentix-backend-fastapi").mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "skills" / "dentix-orchestration").mkdir(parents=True, exist_ok=True)

    (root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").write_text(
        "# Development Workflow\nSole development lifecycle authority.\n",
        encoding="utf-8",
    )

    (root / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\nApply guidance in this order:\n\n{CANONICAL_HIERARCHY_TEXT}\n",
        encoding="utf-8",
    )

    (root / ".agents" / "README.md").write_text(
        f"# Catalog\n\n## Source Priority\n{CANONICAL_HIERARCHY_TEXT}\n\n## Catalog\n"
        "1. `dentix-backend-fastapi`: FastAPI layered architecture.\n"
        "2. `dentix-orchestration`: Lean multi-agent router.\n",
        encoding="utf-8",
    )

    (root / ".agents" / "skills" / "dentix-backend-fastapi" / "SKILL.md").write_text(
        "---\n"
        "name: dentix-backend-fastapi\n"
        "description: FastAPI backend skill\n"
        "---\n"
        "# Content\n"
        "Verify coverage meets active CI configuration thresholds.\n",
        encoding="utf-8",
    )

    (root / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md").write_text(
        "---\n"
        "name: dentix-orchestration\n"
        "description: Lean orchestration and router\n"
        "---\n"
        "# Content\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n"
        "Coverage thresholds must defer to active CI configuration.\n",
        encoding="utf-8",
    )

    (root / "docs" / "AI_AGENT_STACK.md").write_text(
        f"# AI Stack\n\n## 3. Source-of-Truth Hierarchy\n{CANONICAL_HIERARCHY_TEXT}\n\nCoverage governed by active CI.\n",
        encoding="utf-8",
    )

    # Historical files with required headers
    historical_header = (
        "<!-- STATUS: HISTORICAL / NON-AUTHORITATIVE -->\n"
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
    (root / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md").write_text(
        historical_header + "# Master Plan\n", encoding="utf-8"
    )

    # Classified documents
    (root / "docs" / "AI_GOVERNANCE_RULES.md").write_text(
        "# AI Rules\nClassification: RUNTIME-AI\n", encoding="utf-8"
    )
    (root / "docs" / "HERMES_AGENT_GUIDE.md").write_text(
        "# Technical Guide\n<!-- CLASSIFICATION: ARCHITECTURE-REFERENCE -->\n", encoding="utf-8"
    )
    (root / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md").write_text(
        "# Odontogram Spec\n<!-- CLASSIFICATION: PRODUCT-SPEC -->\n", encoding="utf-8"
    )
    (root / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md").write_text(
        "# Traceability Matrix\n<!-- CLASSIFICATION: PRODUCT-SPEC -->\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "BRANCH_DISPOSITION_LEDGER.md").write_text(
        "# Ledger\nClassification: ARCHITECTURE-REFERENCE\n", encoding="utf-8"
    )
    (root / "docs" / "engineering" / "CLINICAL_CHART_DISPOSITION.md").write_text(
        "# Disposition\nClassification: ARCHITECTURE-REFERENCE\n", encoding="utf-8"
    )

    # External skills provenance artifacts
    real_lock = REPO_ROOT / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    real_verifier = REPO_ROOT / "scripts" / "verify_external_skills.py"
    shutil.copy2(real_lock, root / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(real_verifier, root / "scripts" / "verify_external_skills.py")
    (root / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md").write_text(
        "# Plan\n\n## Movement 2\nPrerequisite Gate: EXTERNAL_SKILL_PROVENANCE = PASS\n",
        encoding="utf-8",
    )


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        create_valid_fixture(tmp_path)
        yield tmp_path


def test_valid_canonical_fixture_passes(temp_repo):
    code, failures, skill_count = run_linter(temp_repo)
    assert code == 0, f"Expected 0, got failures: {failures}"
    assert len(failures) == 0
    assert skill_count == 2


def test_missing_layer_in_hierarchy_fails(temp_repo):
    # Omit layer 9 from AGENTS.md
    truncated_hierarchy = "\n".join(CANONICAL_HIERARCHY_TEXT.splitlines()[:8])
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{truncated_hierarchy}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("must contain an explicit sequential 1..9 authority hierarchy list" in f for f in failures)


def test_reordered_layers_in_hierarchy_fails(temp_repo):
    lines = CANONICAL_HIERARCHY_TEXT.splitlines()
    # Swap layer 3 and 4
    lines[2], lines[3] = "3. " + lines[3][3:], "4. " + lines[2][3:]
    reordered_hierarchy = "\n".join(lines)
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{reordered_hierarchy}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("layer 3 mismatch" in f or "layer 4 mismatch" in f for f in failures)


def test_duplicated_layer_number_in_hierarchy_fails(temp_repo):
    lines = CANONICAL_HIERARCHY_TEXT.splitlines()
    lines[1] = "1. Duplicate layer"
    dup_hierarchy = "\n".join(lines)
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{dup_hierarchy}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("duplicated hierarchy number 1" in f for f in failures)


def test_layer_mismatch_fails(temp_repo):
    lines = CANONICAL_HIERARCHY_TEXT.splitlines()
    lines[0] = "1. General engineering practices take priority."
    bad_hierarchy = "\n".join(lines)
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{bad_hierarchy}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("layer 1 mismatch" in f for f in failures)


def test_development_workflow_described_as_subordinate_fails(temp_repo):
    agents = temp_repo / "AGENTS.md"
    content = agents.read_text(encoding="utf-8")
    agents.write_text(content + "\nNotice: DEVELOPMENT_WORKFLOW.md is optional for quick fixes.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("describes 'docs/engineering/DEVELOPMENT_WORKFLOW.md' as optional or subordinate" in f for f in failures)


def test_external_skills_ranked_above_native_fails(temp_repo):
    lines = CANONICAL_HIERARCHY_TEXT.splitlines()
    # Rank external skills as 7, native skills as 8
    lines[6] = "7. External skills (helpers)"
    lines[7] = "8. Relevant .agents/skills/ instructions"
    inverted = "\n".join(lines)
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{inverted}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("incorrectly ranks External skills higher" in f for f in failures)


def test_external_skills_claiming_overriding_authority_fails(temp_repo):
    agents = temp_repo / "AGENTS.md"
    content = agents.read_text(encoding="utf-8")
    agents.write_text(content + "\nExternal skills override repository conventions when needed.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("incorrectly attributes overriding authority to External skills" in f for f in failures)


def test_missing_hierarchy_section_fails(temp_repo):
    (temp_repo / "AGENTS.md").write_text("# Instructions\nNo precedence section here.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("is missing explicit authority hierarchy section" in f for f in failures)


def test_missing_development_workflow_fails(temp_repo):
    (temp_repo / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").unlink()
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("DEVELOPMENT_WORKFLOW.md" in f for f in failures)


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


def test_hardcoded_skill_coverage_threshold_fails(temp_repo):
    skill_file = temp_repo / ".agents" / "skills" / "dentix-backend-fastapi" / "SKILL.md"
    skill_file.write_text(
        "---\nname: dentix-backend-fastapi\ndescription: skill\n---\n"
        "Must maintain 80% coverage.\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("hard-codes coverage percentage" in f for f in failures)


def test_missing_skill_from_catalog_fails(temp_repo):
    extra_dir = temp_repo / ".agents" / "skills" / "dentix-frontend-react"
    extra_dir.mkdir(parents=True, exist_ok=True)
    (extra_dir / "SKILL.md").write_text(
        "---\nname: dentix-frontend-react\ndescription: react skill\n---\nContent\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("exists on disk but is not cataloged" in f for f in failures)


def test_catalog_entry_without_directory_fails(temp_repo):
    readme = temp_repo / ".agents" / "README.md"
    content = readme.read_text(encoding="utf-8")
    readme.write_text(content + "\n2. `dentix-ghost-skill`: Non-existent\n", encoding="utf-8")

    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("does not exist as a directory" in f for f in failures)


def test_missing_historical_header_fails(temp_repo):
    soul_file = temp_repo / "docs" / "soul.md"
    soul_file.write_text("# Soul\nNo archive header here.\n", encoding="utf-8")

    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("missing mandatory 'STATUS: HISTORICAL / NON-AUTHORITATIVE'" in f for f in failures)


def test_stale_missing_workflow_authority_in_ai_agent_stack_fails(temp_repo):
    stack_doc = temp_repo / "docs" / "AI_AGENT_STACK.md"
    stack_doc.write_text("# AI Agent Stack\nOmitting the workflow doc.\n", encoding="utf-8")

    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("AI_AGENT_STACK.md" in f and "must explicitly reference" in f for f in failures)


def test_legacy_master_plan_missing_historical_header_fails(temp_repo):
    master_plan = temp_repo / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md"
    master_plan.write_text("# Master Plan\nNo archive header here.\n", encoding="utf-8")
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md" in f and "missing mandatory 'STATUS: HISTORICAL / NON-AUTHORITATIVE'" in f for f in failures)


def test_active_doc_claiming_master_plan_execution_authority_fails(temp_repo):
    spec = temp_repo / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md"
    spec.write_text(
        "<!-- CLASSIFICATION: PRODUCT-SPEC -->\n# Odontogram Spec\nThis derives from the authoritative master plan.\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("improperly describes legacy master plan as an active execution/source authority" in f for f in failures)


def test_layer_1_missing_clinical_integrity_fails(temp_repo):
    lines = CANONICAL_HIERARCHY_TEXT.splitlines()
    # Remove clinical integrity from layer 1
    lines[0] = "1. Non-negotiable safety, tenant isolation, RBAC, data integrity, privacy, and financial integrity constraints."
    bad_hierarchy = "\n".join(lines)
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{bad_hierarchy}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("layer 1 mismatch" in f for f in failures)


def test_layer_1_missing_financial_integrity_fails(temp_repo):
    lines = CANONICAL_HIERARCHY_TEXT.splitlines()
    # Remove financial integrity from layer 1
    lines[0] = "1. Non-negotiable safety, tenant isolation, RBAC, data integrity, privacy, and clinical integrity constraints."
    bad_hierarchy = "\n".join(lines)
    (temp_repo / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\n{bad_hierarchy}\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("layer 1 mismatch" in f for f in failures)


def test_broken_skill_directory_missing_skill_md_fails(temp_repo):
    broken_dir = temp_repo / ".agents" / "skills" / "dentix-broken-skill"
    broken_dir.mkdir(parents=True, exist_ok=True)
    # Intentionally do not create SKILL.md inside broken_dir
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("missing required 'SKILL.md'" in f for f in failures)


def test_orchestration_skill_exists_and_conforms():
    root = Path(__file__).resolve().parent.parent.parent
    orchestration_md = root / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"
    readme_md = root / ".agents" / "README.md"
    agent_stack_md = root / "docs" / "AI_AGENT_STACK.md"

    assert orchestration_md.exists(), "dentix-orchestration/SKILL.md must exist"
    content = orchestration_md.read_text(encoding="utf-8")
    assert "name: dentix-orchestration" in content
    assert "NORMAL" in content and "HIGH_RISK" in content
    assert "Codex Leader" in content
    assert "Antigravity Implementer" in content
    assert "DEVELOPMENT_WORKFLOW.md" in content

    readme_content = readme_md.read_text(encoding="utf-8")
    assert "`dentix-orchestration`" in readme_content
    assert "11 Native Skills" in readme_content

    stack_content = agent_stack_md.read_text(encoding="utf-8")
    assert "`dentix-orchestration`" in stack_content
    assert "11 Native DENTIX Skills" in stack_content


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


def test_missing_repo_url_or_pinned_commit_fails(temp_repo):
    lock_file = temp_repo / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    data = json.loads(lock_file.read_text(encoding="utf-8"))
    data["source"]["repository_url"] = ""
    lock_file.write_text(json.dumps(data), encoding="utf-8")

    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("repository_url" in f.lower() or "repository url" in f.lower() for f in failures)

    data["source"]["repository_url"] = "https://github.com/amElnagdy/delegate-skills.git"
    data["source"]["pinned_commit"] = ""
    lock_file.write_text(json.dumps(data), encoding="utf-8")

    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("pinned_commit" in f.lower() or "pinned commit" in f.lower() for f in failures)


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
# Movement 3A Pilot B: Orchestration Authority Links Regression Tests
# ==============================================================================


def test_orchestration_authority_links_canonical_pass(temp_repo):
    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert len(failures) == 0

    # Also test valid variant with backtick-wrapped labels and angle brackets
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Governed by [`PROJECT_STANDARDS.md`](<../../../PROJECT_STANDARDS.md>) and "
        "[`DEVELOPMENT_WORKFLOW.md`](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_alt: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_alt)
    assert len(failures_alt) == 0


def test_orchestration_authority_links_original_broken_links_fail(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )

    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert len(failures) == 2
    assert any(
        "has invalid authority link '../../PROJECT_STANDARDS.md'" in f
        and "expected 'PROJECT_STANDARDS.md'" in f
        for f in failures
    )
    assert any(
        "has invalid authority link '../../docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        and "expected 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        for f in failures
    )

    code, linter_failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("has invalid authority link" in f for f in linter_failures)


def test_orchestration_authority_links_missing_either_link_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Case A: Missing PROJECT_STANDARDS.md link
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_a: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_a)
    assert len(failures_a) == 1
    assert any(
        "is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures_a
    )

    # Case B: Missing DEVELOPMENT_WORKFLOW.md link
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    failures_b: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_b)
    assert len(failures_b) == 1
    assert any(
        "is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        for f in failures_b
    )


def test_orchestration_authority_links_missing_source_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"
    orch_skill.unlink()

    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert len(failures) == 1
    assert any(
        "cannot supply required authority links" in f
        and "source must be a file inside the repository" in f
        for f in failures
    )

    code, linter_failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("cannot supply required authority links" in f for f in linter_failures)


def test_orchestration_authority_links_wrong_file_same_basename_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Case A: PROJECT_STANDARDS.md in wrong directory (docs/PROJECT_STANDARDS.md)
    wrong_standards = temp_repo / "docs" / "PROJECT_STANDARDS.md"
    wrong_standards.write_text("# Wrong Standards\n", encoding="utf-8")

    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../docs/PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_a: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_a)
    assert any(
        "has invalid authority link '../../../docs/PROJECT_STANDARDS.md'" in f
        and "link does not resolve to the canonical file inside the repository" in f
        for f in failures_a
    )

    # Case B: DEVELOPMENT_WORKFLOW.md in wrong directory (root DEVELOPMENT_WORKFLOW.md)
    wrong_workflow = temp_repo / "DEVELOPMENT_WORKFLOW.md"
    wrong_workflow.write_text("# Wrong Workflow\n", encoding="utf-8")

    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_b: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_b)
    assert any(
        "has invalid authority link '../../../DEVELOPMENT_WORKFLOW.md'" in f
        and "link does not resolve to the canonical file inside the repository" in f
        for f in failures_b
    )


def test_orchestration_authority_links_missing_canonical_target_or_directory_fails(temp_repo):
    # Subcase 1: Canonical target missing (unlinked)
    (temp_repo / "PROJECT_STANDARDS.md").unlink()
    failures_missing: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_missing)
    assert any(
        "requires canonical target 'PROJECT_STANDARDS.md': canonical target must be a file inside the repository" in f
        for f in failures_missing
    )

    # Subcase 2: Canonical target replaced by a directory
    (temp_repo / "PROJECT_STANDARDS.md").mkdir()
    failures_dir: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_dir)
    assert any(
        "requires canonical target 'PROJECT_STANDARDS.md': canonical target must be a file inside the repository" in f
        for f in failures_dir
    )

    # Subcase 3: Canonical DEVELOPMENT_WORKFLOW.md replaced by a directory
    (temp_repo / "PROJECT_STANDARDS.md").rmdir()
    (temp_repo / "PROJECT_STANDARDS.md").write_text("# Standards\n", encoding="utf-8")
    (temp_repo / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").unlink()
    (temp_repo / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").mkdir()
    failures_workflow_dir: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_workflow_dir)
    assert any(
        "requires canonical target 'docs/engineering/DEVELOPMENT_WORKFLOW.md': canonical target must be a file inside the repository" in f
        for f in failures_workflow_dir
    )


def test_orchestration_authority_links_outside_repo_target_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Subcase 1: Path traversing above repository root
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../../PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_outside: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_outside)
    assert any(
        "has invalid authority link '../../../../PROJECT_STANDARDS.md'" in f
        and "link does not resolve to the canonical file inside the repository" in f
        for f in failures_outside
    )

    # Subcase 2: Link with external scheme (https://)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](https://example.com/PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_url: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_url)
    assert any(
        "has invalid authority link 'https://example.com/PROJECT_STANDARDS.md'" in f
        and "expected a local file link" in f
        for f in failures_url
    )

    # Subcase 3: Link with query parameter
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md?v=1) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    failures_query: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_query)
    assert any(
        "has invalid authority link '../../../PROJECT_STANDARDS.md?v=1'" in f
        and "expected a local file link" in f
        for f in failures_query
    )


def test_orchestration_authority_links_valid_plus_conflicting_duplicate_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n"
        "Conflicting reference: [PROJECT_STANDARDS.md](../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )

    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert any(
        "has invalid authority link '../../PROJECT_STANDARDS.md'" in f
        and "expected 'PROJECT_STANDARDS.md'" in f
        for f in failures
    )

    code, linter_failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("has invalid authority link '../../PROJECT_STANDARDS.md'" in f for f in linter_failures)


def test_orchestration_authority_links_in_comments_fences_code_fail(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Subcase 1: Link only in HTML comment
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "<!-- [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md) -->\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n",
        encoding="utf-8",
    )
    failures_comment: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_comment)
    assert any(
        "is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures_comment
    )

    # Subcase 2: Link only in fenced code block (backticks)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "```markdown\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "```\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n",
        encoding="utf-8",
    )
    failures_fence_backticks: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_fence_backticks)
    assert any(
        "is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures_fence_backticks
    )

    # Subcase 3: Link only in fenced code block (tildes)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "~~~\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n"
        "~~~\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n",
        encoding="utf-8",
    )
    failures_fence_tildes: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_fence_tildes)
    assert any(
        "is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        for f in failures_fence_tildes
    )

    # Subcase 4: Link only in inline code ticks
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "`[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)`\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n",
        encoding="utf-8",
    )
    failures_inline_code: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_inline_code)
    assert any(
        "is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures_inline_code
    )


def test_orchestration_authority_links_run_linter_integration(temp_repo):
    # Integration test through run_linter with broken link
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )

    code, failures, skill_count = run_linter(temp_repo)
    assert code == 1
    assert skill_count == 2
    # Verify useful, descriptive failure message
    expected_failure_snippet = (
        "'.agents/skills/dentix-orchestration/SKILL.md' has invalid authority link "
        "'../../PROJECT_STANDARDS.md'; expected 'PROJECT_STANDARDS.md'"
    )
    assert any(expected_failure_snippet in f for f in failures)

    # Restore canonical link and verify clean run_linter pass
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md) "
        "and [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md).\n",
        encoding="utf-8",
    )
    code_pass, failures_pass, skill_count_pass = run_linter(temp_repo)
    assert code_pass == 0
    assert len(failures_pass) == 0
    assert skill_count_pass == 2


def test_orchestration_authority_links_indented_code_block_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Links only in a 4-space indented code block (both authority documents)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "    [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "    [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n",
        encoding="utf-8",
    )
    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert any(
        "'.agents/skills/dentix-orchestration/SKILL.md' is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures
    )
    assert any(
        "'.agents/skills/dentix-orchestration/SKILL.md' is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        for f in failures
    )

    code, linter_failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("is missing an inline authority link" in f for f in linter_failures)

    # Also test tab-indented code line
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "\t[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "\t[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n",
        encoding="utf-8",
    )
    failures_tab: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_tab)
    assert any("is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f for f in failures_tab)
    assert any("is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f for f in failures_tab)


def test_orchestration_authority_links_multiline_inline_code_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Multiline inline-code span with single backtick (both authority documents)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "`code start\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n"
        "code end`\n",
        encoding="utf-8",
    )
    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert any(
        "'.agents/skills/dentix-orchestration/SKILL.md' is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures
    )
    assert any(
        "'.agents/skills/dentix-orchestration/SKILL.md' is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        for f in failures
    )

    code, linter_failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("is missing an inline authority link" in f for f in linter_failures)

    # Multiline inline-code span with double backticks
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "``\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n"
        "``\n",
        encoding="utf-8",
    )
    failures_double: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_double)
    assert any("is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f for f in failures_double)
    assert any("is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f for f in failures_double)


def test_orchestration_authority_links_unterminated_comment_fails(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Unterminated HTML comment extending to end of document (both authority documents)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "<!-- Unterminated comment extending to EOF\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n",
        encoding="utf-8",
    )
    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert any(
        "'.agents/skills/dentix-orchestration/SKILL.md' is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f
        for f in failures
    )
    assert any(
        "'.agents/skills/dentix-orchestration/SKILL.md' is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f
        for f in failures
    )

    code, linter_failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("is missing an inline authority link" in f for f in linter_failures)


def test_orchestration_authority_links_positive_controls(temp_repo):
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Positive Control 1: Ordinary prose links after a closed HTML comment
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "<!-- Completed closed comment -->\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    f1: list[str] = []
    check_orchestration_authority_links(temp_repo, f1)
    assert len(f1) == 0

    # Positive Control 2: Ordinary prose links after a 4-space indented code block
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "    # Indented code block\n"
        "    git status\n"
        "\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    f2: list[str] = []
    check_orchestration_authority_links(temp_repo, f2)
    assert len(f2) == 0

    # Positive Control 3: Ordinary prose links after multiline inline code span with backtick/angle-bracket syntax
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "`multiline\n"
        "code span`\n"
        "Governed by [`PROJECT_STANDARDS.md`](<../../../PROJECT_STANDARDS.md>) and "
        "[`DEVELOPMENT_WORKFLOW.md`](<../../../docs/engineering/DEVELOPMENT_WORKFLOW.md>).\n",
        encoding="utf-8",
    )
    f3: list[str] = []
    check_orchestration_authority_links(temp_repo, f3)
    assert len(f3) == 0

    # Positive Control 4: Ordinary prose links appearing before trailing unclosed comment
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n"
        "<!-- unclosed trailing note\n",
        encoding="utf-8",
    )
    f4: list[str] = []
    check_orchestration_authority_links(temp_repo, f4)
    assert len(f4) == 0


def test_orchestration_authority_links_code_containing_comment_delimiters_passes(temp_repo):
    """Reviewer Finding 1: Code examples containing <!-- must not erase genuine prose links after them."""
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Case 1A: Closed code fence containing <!-- before genuine prose links
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "```html\n"
        "<!-- example comment inside closed code fence without close\n"
        "```\n\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    failures_fence: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_fence)
    assert len(failures_fence) == 0

    code_fence, linter_failures_fence, _ = run_linter(temp_repo)
    assert code_fence == 0
    assert len(linter_failures_fence) == 0

    # Case 1B: Indented code block containing <!-- before genuine prose links
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "    <!-- example comment in 4-space indented block\n\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    failures_indented: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_indented)
    assert len(failures_indented) == 0

    code_indented, linter_failures_indented, _ = run_linter(temp_repo)
    assert code_indented == 0
    assert len(linter_failures_indented) == 0

    # Case 1C: Single-line inline code containing <!-- before genuine prose links
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "Use `<!--` in templates.\n\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    failures_inline: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_inline)
    assert len(failures_inline) == 0

    code_inline, linter_failures_inline, _ = run_linter(temp_repo)
    assert code_inline == 0
    assert len(linter_failures_inline) == 0

    # Case 1D: Multiline inline code containing <!-- before genuine prose links
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "`multiline\n"
        "<!-- unclosed in code span\n"
        "code end`\n\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    failures_inline_multi: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_inline_multi)
    assert len(failures_inline_multi) == 0

    code_inline_multi, linter_failures_inline_multi, _ = run_linter(temp_repo)
    assert code_inline_multi == 0
    assert len(linter_failures_inline_multi) == 0


def test_orchestration_authority_links_unequal_backtick_counts_in_multiline_code_fails(temp_repo):
    """Reviewer Finding 2: Unequal backtick counts inside multiline code must not prematurely close code span."""
    orch_skill = temp_repo / ".agents" / "skills" / "dentix-orchestration" / "SKILL.md"

    # Case 2A: 1-tick opening with 2-ticks sequence inside code span (should FAIL finding prose links)
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "`start\n"
        "``\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n"
        "``\n"
        "end`\n",
        encoding="utf-8",
    )
    failures_1_2: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_1_2)
    assert any("is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f for f in failures_1_2)
    assert any("is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f for f in failures_1_2)

    code_1_2, linter_failures_1_2, _ = run_linter(temp_repo)
    assert code_1_2 == 1
    assert any("is missing an inline authority link" in f for f in linter_failures_1_2)

    # Case 2B: 2-ticks opening with 1-tick and 3-ticks sequences inside code span
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "``\n"
        "`single tick` and ```triple tick```\n"
        "[PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md)\n"
        "[DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)\n"
        "``\n",
        encoding="utf-8",
    )
    failures_2_13: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_2_13)
    assert any("is missing an inline authority link to 'PROJECT_STANDARDS.md'" in f for f in failures_2_13)
    assert any("is missing an inline authority link to 'docs/engineering/DEVELOPMENT_WORKFLOW.md'" in f for f in failures_2_13)

    # Case 2C: Positive control: multiline code with unequal ticks inside, followed by real prose links
    orch_skill.write_text(
        "---\nname: dentix-orchestration\ndescription: router\n---\n"
        "`start\n"
        "``\n"
        "example\n"
        "``\n"
        "end`\n\n"
        "Operates under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) "
        "and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md).\n",
        encoding="utf-8",
    )
    failures_pos: list[str] = []
    check_orchestration_authority_links(temp_repo, failures_pos)
    assert len(failures_pos) == 0

    code_pos, linter_failures_pos, _ = run_linter(temp_repo)
    assert code_pos == 0
    assert len(linter_failures_pos) == 0


@pytest.mark.parametrize("prefix,suffix", [
    ("<!-- Example ` -->\n", ""),
    ("<!-- Example ` -->\n", "\n<!-- Another ` -->"),
    ("<!--\n```\n-->\n", ""),
    ("Use `<!--` in templates.\n\n", ""),
    ("```html\n<!--\n```\n\n", ""),
])
def test_authority_links_preserve_source_order(temp_repo, prefix, suffix):
    source = temp_repo / ".agents/skills/dentix-orchestration/SKILL.md"
    links = (
        "[`PROJECT_STANDARDS.md`](../../../PROJECT_STANDARDS.md) and "
        "[`DEVELOPMENT_WORKFLOW.md`](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md)"
    )
    source.write_text(prefix + links + suffix, encoding="utf-8")
    failures: list[str] = []
    check_orchestration_authority_links(temp_repo, failures)
    assert failures == []
    code, integration_failures, _ = run_linter(temp_repo)
    assert code == 0, integration_failures
