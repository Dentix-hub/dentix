#!/usr/bin/env python3
"""
DENTIX Static Authority & Precedence Linter
============================================
Deterministic, local-only validator enforcing DENTIX architectural authority,
single workflow authority, native skill catalog integrity, classification
standards, and retired skill reference detection.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# The exact set of approved native DENTIX skills.
APPROVED_NATIVE_SKILLS: frozenset[str] = frozenset({
    "dentix-security-tenancy-rbac",
    "dentix-database-migrations",
    "dentix-testing-verification",
    "dentix-code-review",
})

# Skills that have been retired and must not appear in ACTIVE documents.
RETIRED_SKILLS: frozenset[str] = frozenset({
    "dentix-orchestration",
    "dentix-plan-execution",
    "dentix-backend-fastapi",
    "dentix-frontend-react",
    "dentix-mobile-flutter",
    "dentix-systematic-debugging",
    "dentix-performance",
})


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return current.parent.parent.parent


def check_canonical_files_exist(root: Path, failures: list[str]) -> None:
    canonical_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
        root / ".agents" / "README.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    for path in canonical_files:
        if not path.exists():
            failures.append(f"Missing canonical authority file: {path.relative_to(root)}")


def check_exact_native_skill_set(root: Path, failures: list[str]) -> int:
    """Verify that exactly the approved native skills exist on disk."""
    skills_dir = root / ".agents" / "skills"

    if not skills_dir.exists():
        failures.append("Missing skills directory: '.agents/skills'")
        return 0

    all_skill_dirs = {d.name for d in skills_dir.iterdir() if d.is_dir() and d.name.startswith("dentix-")}

    # Check each has SKILL.md
    valid_disk_skills: set[str] = set()
    for d_name in all_skill_dirs:
        skill_md = skills_dir / d_name / "SKILL.md"
        if not skill_md.exists():
            failures.append(f"Skill directory '.agents/skills/{d_name}' is missing required 'SKILL.md'.")
        else:
            valid_disk_skills.add(d_name)

    # Exact match against approved set
    unexpected = valid_disk_skills - APPROVED_NATIVE_SKILLS
    if unexpected:
        failures.append(
            f"Unexpected native skill(s) on disk (not in approved set): {sorted(unexpected)}"
        )

    missing = APPROVED_NATIVE_SKILLS - valid_disk_skills
    if missing:
        failures.append(
            f"Missing approved native skill(s) from disk: {sorted(missing)}"
        )

    return len(valid_disk_skills)


def check_skill_catalog_bidirectional(root: Path, failures: list[str]) -> int:
    """Verify disk skills match the .agents/README.md catalog."""
    skills_dir = root / ".agents" / "skills"
    readme_path = root / ".agents" / "README.md"

    if not skills_dir.exists():
        failures.append("Missing skills directory: '.agents/skills'")
        return 0

    all_skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and d.name.startswith("dentix-")]

    valid_disk_skills: set[str] = set()
    for d in all_skill_dirs:
        skill_md = d / "SKILL.md"
        if skill_md.exists():
            valid_disk_skills.add(d.name)

    catalog_skills: set[str] = set()
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        catalog_skills = set(re.findall(r"`(dentix-[a-z0-9-]+)`", content))
    else:
        failures.append("Missing README catalog: '.agents/README.md'")

    disk_only = valid_disk_skills - catalog_skills
    if disk_only:
        failures.append(
            f"Skill(s) exists on disk but is not cataloged in '.agents/README.md': {sorted(disk_only)}"
        )

    catalog_only = catalog_skills - valid_disk_skills
    if catalog_only:
        failures.append(
            f"Skill(s) cataloged in '.agents/README.md' does not exist as a directory with 'SKILL.md' under '.agents/skills/': {sorted(catalog_only)}"
        )

    return len(valid_disk_skills)


def check_no_retired_skill_references(root: Path, failures: list[str]) -> None:
    """Verify that no ACTIVE document references retired skill names."""
    active_authority_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    for path in active_authority_files:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for retired_skill in RETIRED_SKILLS:
            if retired_skill in content:
                failures.append(
                    f"Active authority file '{path.relative_to(root)}' references retired skill '{retired_skill}'."
                )


def check_no_obsolete_agent_paths(root: Path, failures: list[str]) -> None:
    active_authority_files = [
        root / "PROJECT_STANDARDS.md",
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    pattern = re.compile(r"(?<!\w)\.agent/")

    for path in active_authority_files:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if pattern.search(content):
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
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    for doc in documents_requiring_workflow:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8")

        # Check for workflow reference (allow both full path and basename)
        has_workflow_ref = workflow_rel in content or "DEVELOPMENT_WORKFLOW.md" in content
        if not has_workflow_ref:
            failures.append(
                f"'{doc.relative_to(root)}' must reference '{workflow_rel}' as canonical development lifecycle authority."
            )

        # Reject if described as optional, subordinate, or secondary
        subordinate_pattern = re.compile(
            r"(?:DEVELOPMENT_WORKFLOW\.md.*?is\s+(?:optional|subordinate|secondary|non-authoritative)|"
            r"(?:optional|subordinate|secondary)\s+(?:authority\s+)?DEVELOPMENT_WORKFLOW\.md)",
            re.IGNORECASE,
        )
        if subordinate_pattern.search(content):
            failures.append(
                f"'{doc.relative_to(root)}' describes '{workflow_rel}' as optional or subordinate."
            )

    # Reject if any active document describes the legacy master plan as an active execution authority
    active_spec_docs: list[Path] = []
    product_dir = root / "docs" / "product"
    if product_dir.exists():
        spec_path = product_dir / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md"
        if spec_path.exists():
            active_spec_docs.append(spec_path)
        matrix_path = product_dir / "ODONTOGRAM_TRACEABILITY_MATRIX.md"
        if matrix_path.exists():
            active_spec_docs.append(matrix_path)

    legacy_authority_pattern = re.compile(
        r"(?:authoritative\s+master\s+plan|Source\s+Authority:\s*`?[^`\n]*MASTER_PLAN)",
        re.IGNORECASE,
    )
    for doc in documents_requiring_workflow + active_spec_docs:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8")
        if legacy_authority_pattern.search(content):
            failures.append(
                f"'{doc.relative_to(root)}' improperly describes legacy master plan as an active execution/source authority."
            )


def check_authority_pointers(root: Path, failures: list[str]) -> None:
    """Verify AGENTS.md references canonical authorities."""
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        return

    content = agents_md.read_text(encoding="utf-8")

    required_refs = [
        ("PROJECT_STANDARDS.md", "architecture authority"),
        ("DEVELOPMENT_WORKFLOW.md", "lifecycle authority"),
    ]

    for ref_name, purpose in required_refs:
        if ref_name not in content:
            failures.append(
                f"'AGENTS.md' is missing reference to '{ref_name}' ({purpose})."
            )


def check_historical_headers(root: Path, failures: list[str]) -> None:
    completed_v3_plan = root / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md"
    historical_files = [
        root / "docs" / "soul.md",
        root / "docs" / "tttt.md",
        root / "docs" / "engineering" / "DENTIX_WORKFLOW_V2_1_PHASE7_PILOT_EVIDENCE.md",
        root / "docs" / "engineering" / "ODONTOGRAM_VNEXT_TICKET_GRAPH.md",
        root / "docs" / "engineering" / "M3A_PILOT_B_ACCEPTANCE.md",
        root / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md",
        completed_v3_plan,
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

    if completed_v3_plan.exists():
        content = completed_v3_plan.read_text(encoding="utf-8")
        active_claim_pattern = re.compile(
            r"Status:.*READY FOR CONTROLLED EXECUTION|"
            r"This plan establishes one lean DENTIX development workflow",
            re.IGNORECASE,
        )
        if active_claim_pattern.search(content):
            failures.append(
                f"Completed plan '{completed_v3_plan.relative_to(root)}' still claims active workflow authority."
            )


def check_document_classifications(root: Path, failures: list[str]) -> None:
    expected_classifications: list[tuple[Path, str]] = [
        (root / "AGENTS.md", "ACTIVE"),
        (root / ".agents" / "README.md", "ACTIVE"),
        (root / "docs" / "AI_AGENT_STACK.md", "ACTIVE"),
        (root / "docs" / "engineering" / "DEVELOPMENT_WORKFLOW.md", "ACTIVE"),
        (root / "docs" / "AI_GOVERNANCE_RULES.md", "RUNTIME-AI"),
        (root / "docs" / "HERMES_AGENT_GUIDE.md", "ACTIVE"),
        (root / "docs" / "engineering" / "BRANCH_CLEANUP_INSTRUCTIONS.md", "ACTIVE"),
        (root / "docs" / "engineering" / "BRANCH_DISPOSITION_LEDGER.md", "ACTIVE"),
        (root / "docs" / "engineering" / "CLINICAL_CHART_DISPOSITION.md", "ACTIVE"),
        (root / "docs" / "soul.md", "HISTORICAL"),
        (root / "docs" / "tttt.md", "HISTORICAL"),
        (root / "docs" / "engineering" / "DENTIX_WORKFLOW_V2_1_PHASE7_PILOT_EVIDENCE.md", "HISTORICAL"),
        (root / "docs" / "engineering" / "ODONTOGRAM_VNEXT_TICKET_GRAPH.md", "HISTORICAL"),
        (root / "docs" / "engineering" / "M3A_PILOT_B_ACCEPTANCE.md", "HISTORICAL"),
        (root / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md", "HISTORICAL"),
        (root / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md", "HISTORICAL"),
    ]

    # Only check product specs if they exist (not required by agent governance)
    for product_spec, cls in [
        (root / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md", "PRODUCT-SPEC"),
        (root / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md", "PRODUCT-SPEC"),
    ]:
        if product_spec.exists():
            expected_classifications.append((product_spec, cls))

    canonical_classifications = {"ACTIVE", "PRODUCT-SPEC", "RUNTIME-AI", "HISTORICAL"}
    marker_pattern = re.compile(r"<!--\s*CLASSIFICATION:\s*([A-Z][A-Z-]*)\s*-->", re.IGNORECASE)

    for path, expected_cls in expected_classifications:
        if not path.exists():
            # Only fail for non-product-spec files
            if expected_cls not in ("PRODUCT-SPEC",):
                failures.append(f"Required classified document missing: '{path.relative_to(root)}'.")
            continue
        first_lines = "".join(path.read_text(encoding="utf-8").splitlines(keepends=True)[:15])
        marker = marker_pattern.search(first_lines)
        if marker is None:
            failures.append(
                f"Document '{path.relative_to(root)}' is missing canonical classification marker "
                f"'<!-- CLASSIFICATION: {expected_cls} -->' in its header."
            )
            continue

        actual_cls = marker.group(1).upper()
        if actual_cls not in canonical_classifications:
            failures.append(
                f"Document '{path.relative_to(root)}' uses unsupported classification '{actual_cls}'; "
                f"expected one of {sorted(canonical_classifications)}."
            )
        elif actual_cls != expected_cls:
            failures.append(
                f"Document '{path.relative_to(root)}' has classification '{actual_cls}', "
                f"expected '{expected_cls}'."
            )


def check_external_skills_governance(root: Path, failures: list[str]) -> None:
    """
    Enforce external skill provenance requirements:
    1. EXTERNAL_SKILLS_LOCK.json exists and strictly satisfies full lock schema requirements.
    2. verify_external_skills.py verifier exists and provides safe schema validation.
    3. Implementation plan enforces EXTERNAL_SKILL_PROVENANCE = PASS before Movement 2.
    """
    verifier_path = root / "scripts" / "verify_external_skills.py"
    if not verifier_path.exists():
        failures.append("Missing external skill provenance verifier: 'scripts/verify_external_skills.py'")

    lock_path = root / "docs" / "engineering" / "EXTERNAL_SKILLS_LOCK.json"
    if not lock_path.exists():
        failures.append("Missing external skills lock file: 'docs/engineering/EXTERNAL_SKILLS_LOCK.json'")
    else:
        try:
            lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
            if verifier_path.exists():
                import importlib.util
                mod_name = f"verify_external_skills_{abs(hash(str(verifier_path)))}"
                spec = importlib.util.spec_from_file_location(mod_name, verifier_path)
                if spec and spec.loader:
                    v_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(v_mod)
                    if hasattr(v_mod, "validate_lock_schema"):
                        v_mod.validate_lock_schema(lock_data, failures)
                    else:
                        failures.append(
                            "Verifier in 'scripts/verify_external_skills.py' is missing 'validate_lock_schema'."
                        )
                else:
                    failures.append("Failed to load schema validator from 'scripts/verify_external_skills.py'.")
        except json.JSONDecodeError as exc:
            failures.append(f"External skills lock file is malformed JSON: {exc}")
        except Exception as exc:
            failures.append(f"External skills lock validation error: {exc}")

    plan_path = root / "docs" / "DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md"
    if plan_path.exists():
        plan_content = plan_path.read_text(encoding="utf-8")
        if "EXTERNAL_SKILL_PROVENANCE = PASS" not in plan_content:
            failures.append(
                "Implementation plan allows Movement 2 without required pre-Movement-2 gate: 'EXTERNAL_SKILL_PROVENANCE = PASS'"
            )
        elif not re.search(
            r"Movement 2.*?(?:Prerequisite Gate|gate).*?EXTERNAL_SKILL_PROVENANCE\s*=\s*PASS|EXTERNAL_SKILL_PROVENANCE\s*=\s*PASS.*?Movement 2",
            plan_content,
            re.DOTALL | re.IGNORECASE,
        ):
            failures.append(
                "Implementation plan does not link Movement 2 prerequisite to 'EXTERNAL_SKILL_PROVENANCE = PASS'"
            )
    else:
        failures.append(
            "Missing implementation plan: 'docs/DENTIX_LEAN_LOCAL_FIRST_MULTI_AGENT_WORKFLOW_V3_FINAL_IMPLEMENTATION_PLAN.md'"
        )


def run_linter(root: Path | None = None) -> tuple[int, list[str], int]:
    if root is None:
        root = get_repo_root()

    failures: list[str] = []

    check_canonical_files_exist(root, failures)
    skill_count = check_exact_native_skill_set(root, failures)
    check_skill_catalog_bidirectional(root, failures)
    check_no_retired_skill_references(root, failures)
    check_authority_pointers(root, failures)
    check_no_obsolete_agent_paths(root, failures)
    check_no_retired_ci_signal(root, failures)
    check_no_hardcoded_coverage(root, failures)
    check_single_workflow_authority(root, failures)
    check_historical_headers(root, failures)
    check_document_classifications(root, failures)
    check_external_skills_governance(root, failures)

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

    print("\n[OK] All authority checks PASSED.")
    print("  - Canonical authority files verified")
    print(f"  - Exactly {skill_count} approved native skills verified")
    print("  - Skill catalog and filesystem match bidirectionally")
    print("  - No retired skill references in active authority documents")
    print("  - AGENTS.md references canonical authorities")
    print("  - DEVELOPMENT_WORKFLOW.md is authoritative across all entrypoints")
    print("  - No obsolete .agent/ paths in active authorities")
    print("  - No retired agent-ci-signal references")
    print("  - No hardcoded coverage values in native skills or AI stack docs")
    print("  - Historical documents have required archive headers")
    print("  - Document classifications verified (ACTIVE, PRODUCT-SPEC, RUNTIME-AI, HISTORICAL)")
    print("  - External skills strictly subordinate to DENTIX standards")
    print("  - External skill lock schema, verifier, and pre-Movement-2 gate verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
