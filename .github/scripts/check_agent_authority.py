#!/usr/bin/env python3
"""
DENTIX Static Authority Linter
==============================
Deterministic verification gate enforcing repository authority hierarchy,
bidirectional skill catalog integrity, coverage ownership, document classifications,
and deprecation boundaries.

This linter is deterministic and strictly local (zero network calls).
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


def check_canonical_files_exist(root: Path, failures: list[str]) -> None:
    required_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(f"Missing required canonical authority file: '{path.relative_to(root)}'.")


def check_skill_catalog_bidirectional(root: Path, failures: list[str]) -> int:
    skills_dir = root / ".agents" / "skills"
    readme_path = root / ".agents" / "README.md"

    if not skills_dir.exists():
        failures.append("Missing .agents/skills directory.")
        return 0

    if not readme_path.exists():
        failures.append("Missing .agents/README.md.")
        return 0

    readme_content = readme_path.read_text(encoding="utf-8")
    skill_folders = sorted([d.name for d in skills_dir.iterdir() if d.is_dir()])

    # Extract catalog skill names from README: lines like `1. `dentix-foo`: ...`
    catalog_skills = re.findall(r"`(dentix-[a-z0-9-]+)`", readme_content)
    catalog_skills_unique = sorted(set(catalog_skills))

    # Direction 1: Every skill directory must appear in the README catalog
    for skill_name in skill_folders:
        folder = skills_dir / skill_name
        skill_file = folder / "SKILL.md"
        if not skill_file.exists():
            failures.append(f"Skill directory '{skill_name}' is missing SKILL.md.")
            continue

        content = skill_file.read_text(encoding="utf-8")
        if not (content.startswith("---") and "name:" in content and "description:" in content):
            failures.append(f"Skill '{skill_name}/SKILL.md' missing required YAML frontmatter (name/description).")

        if skill_name not in catalog_skills_unique:
            failures.append(f"Skill directory '{skill_name}' exists on disk but is not cataloged in .agents/README.md.")

    # Direction 2: Every skill listed in the README catalog must exist on disk
    for catalog_name in catalog_skills_unique:
        if catalog_name not in skill_folders:
            failures.append(f"Catalog entry '{catalog_name}' in .agents/README.md does not exist as a directory under .agents/skills/.")

    return len(skill_folders)


def check_no_obsolete_agent_paths(root: Path, failures: list[str]) -> None:
    active_authority_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    obsolete_pattern = re.compile(r"(?<!\w)\.agent/")

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
        root / "docs" / "AI_AGENT_STACK.md",
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
    coverage_pattern = re.compile(r"\b\d{1,3}%")

    files_to_check: list[Path] = []
    if skills_dir.exists():
        files_to_check.extend(skills_dir.glob("*/SKILL.md"))
    files_to_check.append(root / "docs" / "AI_AGENT_STACK.md")
    files_to_check.append(root / "AGENTS.md")

    for file_path in files_to_check:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        matches = coverage_pattern.findall(content)
        if matches:
            failures.append(
                f"File '{file_path.relative_to(root)}' hard-codes coverage percentage {matches}. "
                "Coverage thresholds must defer to active CI configuration (.github/workflows/ci.yml)."
            )


def check_single_workflow_authority(root: Path, failures: list[str]) -> None:
    workflow_rel = "docs/engineering/DEVELOPMENT_WORKFLOW.md"
    workflow_doc = root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md"

    if not workflow_doc.exists():
        failures.append(f"Missing canonical development workflow: {workflow_rel}.")
        return

    documents_requiring_workflow = [
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    for doc in documents_requiring_workflow:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8")
        if workflow_rel not in content:
            failures.append(
                f"'{doc.relative_to(root)}' must explicitly reference '{workflow_rel}' as canonical development lifecycle authority."
            )


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


def check_document_classifications(root: Path, failures: list[str]) -> None:
    expected_classifications = [
        (root / "docs" / "AI_GOVERNANCE_RULES.md", "RUNTIME-AI"),
        (root / "docs" / "HERMES_AGENT_GUIDE.md", "ARCHITECTURE-REFERENCE"),
        (root / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md", "PRODUCT-SPEC"),
    ]

    for path, expected_cls in expected_classifications:
        if not path.exists():
            failures.append(f"Required classified document missing: '{path.relative_to(root)}'.")
            continue
        first_lines = "".join(path.read_text(encoding="utf-8").splitlines(keepends=True)[:15])
        if expected_cls.lower() not in first_lines.lower():
            failures.append(
                f"Document '{path.relative_to(root)}' is missing expected classification '{expected_cls}' in header."
            )


def check_external_skills_precedence(root: Path, failures: list[str]) -> None:
    authority_docs = [
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    for path in authority_docs:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        match_native = re.search(r"(\.agents/skills|Relevant \.agents/skills)", content, re.IGNORECASE)
        match_external = re.search(r"External skills", content, re.IGNORECASE)

        if match_native and match_external:
            if match_external.start() < match_native.start():
                failures.append(
                    f"'{path.relative_to(root)}' incorrectly ranks External skills higher than DENTIX native skills."
                )


def run_linter(root: Path | None = None) -> tuple[int, list[str], int]:
    if root is None:
        root = get_repo_root()

    failures: list[str] = []

    check_canonical_files_exist(root, failures)
    skill_count = check_skill_catalog_bidirectional(root, failures)
    check_no_obsolete_agent_paths(root, failures)
    check_no_retired_ci_signal(root, failures)
    check_no_hardcoded_coverage(root, failures)
    check_single_workflow_authority(root, failures)
    check_historical_headers(root, failures)
    check_document_classifications(root, failures)
    check_external_skills_precedence(root, failures)

    exit_code = 1 if failures else 0
    return exit_code, failures, skill_count


def main() -> int:
    root = get_repo_root()
    print(f"Running DENTIX Authority Linter against: {root}")

    exit_code, failures, skill_count = run_linter(root)

    if failures:
        print("\n::error::Authority Linter FAILED with the following violations:")
        for idx, failure in enumerate(failures, 1):
            print(f"  {idx}. {failure}")
        return 1

    print(f"\n[OK] All authority checks PASSED.")
    print(f"  - Canonical authority files verified")
    print(f"  - Skill catalog and filesystem match bidirectionally ({skill_count} native skills detected)")
    print(f"  - DEVELOPMENT_WORKFLOW.md is authoritative across all entrypoints")
    print(f"  - No obsolete .agent/ paths in active authorities")
    print(f"  - No retired agent-ci-signal references")
    print(f"  - No hardcoded coverage values in native skills or AI stack docs")
    print(f"  - Historical documents have required archive headers")
    print(f"  - Document classifications verified (RUNTIME-AI, ARCHITECTURE-REFERENCE, PRODUCT-SPEC)")
    print(f"  - External skills strictly subordinate to DENTIX standards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
