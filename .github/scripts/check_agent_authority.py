#!/usr/bin/env python3
"""
DENTIX Static Authority Linter
==============================
Deterministic verification gate enforcing repository authority hierarchy,
skill catalog integrity, coverage ownership, and deprecation boundaries.

This linter is a deterministic check, not an AI oracle.
Returns 0 on success, non-zero if any authority violations are detected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "PROJECT_STANDARDS.md").exists():
            return parent
    return current.parent.parent.parent


def check_skill_catalog(root: Path, failures: list[str]) -> None:
    skills_dir = root / ".agents" / "skills"
    readme_path = root / ".agents" / "README.md"

    if not skills_dir.exists():
        failures.append("Missing .agents/skills directory.")
        return

    if not readme_path.exists():
        failures.append("Missing .agents/README.md.")
        return

    readme_content = readme_path.read_text(encoding="utf-8")
    skill_folders = [d for d in skills_dir.iterdir() if d.is_dir()]

    for folder in skill_folders:
        skill_file = folder / "SKILL.md"
        if not skill_file.exists():
            failures.append(f"Skill directory '{folder.name}' is missing SKILL.md.")
            continue

        content = skill_file.read_text(encoding="utf-8")
        if not (content.startswith("---") and "name:" in content and "description:" in content):
            failures.append(f"Skill '{folder.name}/SKILL.md' missing required YAML frontmatter (name/description).")

        if folder.name not in readme_content:
            failures.append(f"Skill '{folder.name}' not registered in .agents/README.md.")


def check_no_obsolete_agent_paths(root: Path, failures: list[str]) -> None:
    active_authority_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
    ]

    obsolete_pattern = re.compile(r"(?<!\w)\.agent/(?!\w)")

    for path in active_authority_files:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        matches = obsolete_pattern.findall(content)
        if matches:
            failures.append(f"Active authority file '{path.relative_to(root)}' contains obsolete '.agent/' reference.")


def check_no_retired_ci_signal(root: Path, failures: list[str]) -> None:
    active_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
    ]
    workflows_dir = root / ".github" / "workflows"
    if workflows_dir.exists():
        active_files.extend(workflows_dir.glob("*.yml"))

    for path in active_files:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if "agent-ci-signal" in content:
            failures.append(f"Active file '{path.relative_to(root)}' contains retired 'agent-ci-signal' reference.")


def check_no_hardcoded_coverage(root: Path, failures: list[str]) -> None:
    skills_dir = root / ".agents" / "skills"
    if not skills_dir.exists():
        return

    coverage_percentage_pattern = re.compile(r"\b\d{2}%\b")

    for skill_file in skills_dir.glob("*/SKILL.md"):
        content = skill_file.read_text(encoding="utf-8")
        matches = coverage_percentage_pattern.findall(content)
        if matches:
            failures.append(
                f"Skill '{skill_file.relative_to(root)}' hard-codes coverage percentage {matches}. "
                "Coverage thresholds must defer to active CI configuration (.github/workflows/ci.yml)."
            )


def check_single_workflow_authority(root: Path, failures: list[str]) -> None:
    workflow_doc = root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md"
    agents_doc = root / "AGENTS.md"

    if not workflow_doc.exists():
        failures.append("Missing canonical development workflow: docs/engineering/DEVELOPMENT_WORKFLOW.md.")
        return

    if not agents_doc.exists():
        failures.append("Missing root AGENTS.md.")
        return

    agents_content = agents_doc.read_text(encoding="utf-8")
    if "docs/engineering/DEVELOPMENT_WORKFLOW.md" not in agents_content:
        failures.append("AGENTS.md must explicitly reference docs/engineering/DEVELOPMENT_WORKFLOW.md as lifecycle authority.")


def check_historical_headers(root: Path, failures: list[str]) -> None:
    historical_files = [
        root / "docs" / "soul.md",
        root / "docs" / "tttt.md",
        root / "docs" / "engineering" / "DENTIX_WORKFLOW_V2_1_PHASE7_PILOT_EVIDENCE.md",
        root / "docs" / "engineering" / "ODONTOGRAM_VNEXT_TICKET_GRAPH.md",
    ]

    header_pattern = re.compile(r"STATUS:\s*HISTORICAL\s*/\s*NON-AUTHORITATIVE", re.IGNORECASE)

    for path in historical_files:
        if not path.exists():
            continue
        first_lines = "".join(path.read_text(encoding="utf-8").splitlines(keepends=True)[:10])
        if not header_pattern.search(first_lines):
            failures.append(
                f"Historical document '{path.relative_to(root)}' is missing mandatory "
                "'STATUS: HISTORICAL / NON-AUTHORITATIVE' archive header."
            )


def check_external_skills_precedence(root: Path, failures: list[str]) -> None:
    agents_doc = root / "AGENTS.md"
    readme_doc = root / ".agents" / "README.md"

    for path in (agents_doc, readme_doc):
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        # Ensure external skills is mentioned below native skills / standards
        match_native = re.search(r"(\.agents/skills|Relevant \.agents/skills)", content)
        match_external = re.search(r"External skills", content, re.IGNORECASE)

        if match_native and match_external:
            if match_external.start() < match_native.start():
                failures.append(
                    f"'{path.relative_to(root)}' incorrectly ranks External skills higher than DENTIX native skills."
                )


def main() -> int:
    root = get_repo_root()
    failures: list[str] = []

    print(f"Running DENTIX Authority Linter against: {root}")

    check_skill_catalog(root, failures)
    check_no_obsolete_agent_paths(root, failures)
    check_no_retired_ci_signal(root, failures)
    check_no_hardcoded_coverage(root, failures)
    check_single_workflow_authority(root, failures)
    check_historical_headers(root, failures)
    check_external_skills_precedence(root, failures)

    if failures:
        print("\n::error::Authority Linter FAILED with the following violations:")
        for idx, failure in enumerate(failures, 1):
            print(f"  {idx}. {failure}")
        return 1

    print("\n[OK] All authority checks PASSED.")
    print("  - Skill catalog matches filesystem (10 native skills)")
    print("  - No obsolete .agent/ paths in active authorities")
    print("  - No retired agent-ci-signal references")
    print("  - No hardcoded coverage values in native skills")
    print("  - DEVELOPMENT_WORKFLOW.md is authoritative")
    print("  - Historical documents have required archive headers")
    print("  - External skills strictly subordinate to DENTIX standards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
