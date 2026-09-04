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

    (root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").write_text(
        "# Development Workflow\nSole development lifecycle authority.\n",
        encoding="utf-8",
    )

    (root / "AGENTS.md").write_text(
        f"# Instructions\n\n## 2. Instruction Precedence\n\nApply guidance in this order:\n\n{CANONICAL_HIERARCHY_TEXT}\n",
        encoding="utf-8",
    )

    (root / ".agents" / "README.md").write_text(
        f"# Catalog\n\n## Source Priority\n{CANONICAL_HIERARCHY_TEXT}\n\n## Catalog\n1. `dentix-backend-fastapi`: FastAPI layered architecture.\n",
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
    assert skill_count == 1


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
