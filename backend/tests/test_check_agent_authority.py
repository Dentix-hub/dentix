"""
Tests for DENTIX Static Authority Linter (.github/scripts/check_agent_authority.py)
==================================================================================
Validates deterministic detection of authority hierarchy, bidirectional skill
catalog integrity, coverage ownership, and classification rules.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Load check_agent_authority directly by path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LINTER_PATH = REPO_ROOT / ".github" / "scripts" / "check_agent_authority.py"

spec = importlib.util.spec_from_file_location("check_agent_authority", LINTER_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load linter module from {LINTER_PATH}")
linter_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linter_mod)
run_linter = linter_mod.run_linter


def create_valid_fixture(root: Path) -> None:
    """Create a minimal, valid DENTIX authority fixture in a temporary directory."""
    # Canonical files
    (root / "PROJECT_STANDARDS.md").write_text("# Project Standards\nArchitecture authority.\n", encoding="utf-8")

    (root / "docs" / "engineering").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "product").mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "skills" / "dentix-backend-fastapi").mkdir(parents=True, exist_ok=True)

    (root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md").write_text(
        "# Development Workflow\nSole development lifecycle authority.\n",
        encoding="utf-8",
    )

    (root / "AGENTS.md").write_text(
        "# Instructions\n"
        "1. Safety\n"
        "2. User Requirement\n"
        "3. PROJECT_STANDARDS.md\n"
        "4. docs/engineering/DEVELOPMENT_WORKFLOW.md\n"
        "5. AGENTS.md\n"
        "6. Product spec\n"
        "7. Relevant .agents/skills/\n"
        "8. External skills\n"
        "9. General\n",
        encoding="utf-8",
    )

    (root / ".agents" / "README.md").write_text(
        "# Catalog\n"
        "## Source Priority\n"
        "1. Safety\n"
        "2. User Requirement\n"
        "3. PROJECT_STANDARDS.md\n"
        "4. docs/engineering/DEVELOPMENT_WORKFLOW.md\n"
        "5. AGENTS.md\n"
        "6. Product spec\n"
        "7. Relevant .agents/skills/\n"
        "8. External skills\n"
        "## Catalog\n"
        "1. `dentix-backend-fastapi`: FastAPI layered architecture.\n",
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
        "# AI Stack\n"
        "## 3. Hierarchy\n"
        "1. Safety\n"
        "2. User Requirement\n"
        "3. PROJECT_STANDARDS.md\n"
        "4. docs/engineering/DEVELOPMENT_WORKFLOW.md\n"
        "5. AGENTS.md\n"
        "6. Product spec\n"
        "7. Relevant .agents/skills/\n"
        "8. External skills\n"
        "Coverage governed by active CI.\n",
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
    # Create directory that is NOT listed in .agents/README.md catalog
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
    # Add catalog entry in README that does NOT exist on disk
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


def test_external_skills_precedence_violation_fails(temp_repo):
    agents = temp_repo / "AGENTS.md"
    agents.write_text(
        "# Hierarchy\n"
        "1. External skills\n"
        "2. Relevant .agents/skills/\n",
        encoding="utf-8",
    )
    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("ranks External skills higher than DENTIX native skills" in f for f in failures)


def test_stale_missing_workflow_authority_in_ai_agent_stack_fails(temp_repo):
    stack_doc = temp_repo / "docs" / "AI_AGENT_STACK.md"
    stack_doc.write_text("# AI Agent Stack\nOmitting the workflow doc.\n", encoding="utf-8")

    code, failures, _ = run_linter(temp_repo)
    assert code == 1
    assert any("AI_AGENT_STACK.md" in f and "must explicitly reference" in f for f in failures)
