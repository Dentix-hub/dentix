#!/usr/bin/env python3
"""
DENTIX Static Authority & Precedence Linter
===========================================
Deterministic, local-only validator enforcing DENTIX architectural authority,
the canonical nine-layer precedence hierarchy, single workflow authority,
bidirectional skill catalog matching, and classification standards.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

CANONICAL_HIERARCHY: list[tuple[int, str, list[str]]] = [
    (1, "Non-negotiable safety, tenant isolation, RBAC, data integrity, privacy, clinical integrity, and financial integrity", [
        r"safety",
        r"(?:tenant|isolation)",
        r"rbac",
        r"data\s+integrity",
        r"privacy",
        r"clinical\s+integrity",
        r"financial\s+integrity",
    ]),
    (2, "Explicit current user requirement or approved implementation plan within safety constraints", [
        r"(?:user\s+requirement|approved\s+(?:implementation\s+plan|product\s+decision))",
    ]),
    (3, "PROJECT_STANDARDS.md", [
        r"PROJECT_STANDARDS\.md",
    ]),
    (4, "docs/engineering/DEVELOPMENT_WORKFLOW.md", [
        r"(?:docs/engineering/)?DEVELOPMENT_WORKFLOW\.md",
    ]),
    (5, "AGENTS.md", [
        r"AGENTS\.md",
    ]),
    (6, "Active product / domain specifications", [
        r"active\s+product\s+(?:/\s*domain\s+)?specifications?",
    ]),
    (7, "Relevant .agents/skills/ instructions", [
        r"\.agents/skills/",
    ]),
    (8, "External skills as optional subordinate helpers", [
        r"external\s+skills?",
    ]),
    (9, "General engineering conventions", [
        r"general\s+engineering",
    ]),
]


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
        root / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md",
        root / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md",
    ]

    for path in canonical_files:
        if not path.exists():
            failures.append(f"Missing canonical authority file: {path.relative_to(root)}")


def check_skill_catalog_bidirectional(root: Path, failures: list[str]) -> int:
    skills_dir = root / ".agents" / "skills"
    readme_path = root / ".agents" / "README.md"

    if not skills_dir.exists():
        failures.append("Missing skills directory: '.agents/skills'")
        return 0

    all_skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and d.name.startswith("dentix-")]

    valid_disk_skills: set[str] = set()
    for d in all_skill_dirs:
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            failures.append(f"Skill directory '{d.relative_to(root)}' is missing required 'SKILL.md'.")
        else:
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
    active_spec_docs = [
        root / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md",
        root / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md",
    ]
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


def check_nine_layer_hierarchy(root: Path, failures: list[str]) -> None:
    authority_docs = [
        root / "AGENTS.md",
        root / ".agents" / "README.md",
        root / "docs" / "AI_AGENT_STACK.md",
    ]

    section_pattern = re.compile(
        r"##\s+(?:(?:\d+\.)?\s*)?(?:Instruction\s+Precedence|Source\s+Priority|Source-of-Truth\s+Hierarchy).*?(?=\n##|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    list_item_pattern = re.compile(r"^\s*([1-9])\.\s+(.*)$")

    for doc in authority_docs:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8")

        m_sec = section_pattern.search(content)
        if not m_sec:
            failures.append(
                f"'{doc.relative_to(root)}' is missing explicit authority hierarchy section "
                "('Instruction Precedence', 'Source Priority', or 'Source-of-Truth Hierarchy')."
            )
            continue

        sec_text = m_sec.group(0)
        lines = sec_text.splitlines()

        # Find 1..9 list sequence inside the authority section
        numbered_items: dict[int, str] = {}
        for line in lines:
            m = list_item_pattern.match(line)
            if m:
                num = int(m.group(1))
                text = m.group(2).strip()
                if 1 <= num <= 9:
                    if num in numbered_items:
                        failures.append(
                            f"'{doc.relative_to(root)}' contains duplicated hierarchy number {num} in authority section."
                        )
                    numbered_items[num] = text

        if len(numbered_items) != 9 or sorted(numbered_items.keys()) != list(range(1, 10)):
            failures.append(
                f"'{doc.relative_to(root)}' must contain an explicit sequential 1..9 authority hierarchy list. "
                f"Found {len(numbered_items)} items: {sorted(numbered_items.keys())}."
            )
            continue

        # Validate each layer matches canonical definition
        for layer_num, desc, patterns in CANONICAL_HIERARCHY:
            item_text = numbered_items[layer_num]
            all_match = all(re.search(pat, item_text, re.IGNORECASE) for pat in patterns)
            if not all_match:
                failures.append(
                    f"'{doc.relative_to(root)}' layer {layer_num} mismatch: expected '{desc}', found '{item_text}'."
                )

        # Check external skills rank strictly below native skills
        layer7_text = numbered_items.get(7, "")
        layer8_text = numbered_items.get(8, "")
        if "external" in layer7_text.lower() or "skills/" in layer8_text.lower():
            failures.append(
                f"'{doc.relative_to(root)}' incorrectly ranks External skills higher than DENTIX native skills."
            )

        # Reject claims that external skills are authorities
        if re.search(r"external\s+skills?.*?(?:override|supersede|authority\s+over)", content, re.IGNORECASE):
            failures.append(
                f"'{doc.relative_to(root)}' incorrectly attributes overriding authority to External skills."
            )


def check_historical_headers(root: Path, failures: list[str]) -> None:
    historical_files = [
        root / "docs" / "soul.md",
        root / "docs" / "tttt.md",
        root / "docs" / "engineering" / "DENTIX_WORKFLOW_V2_1_PHASE7_PILOT_EVIDENCE.md",
        root / "docs" / "engineering" / "ODONTOGRAM_VNEXT_TICKET_GRAPH.md",
        root / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md",
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
        (root / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md", "PRODUCT-SPEC"),
        (root / "docs" / "engineering" / "BRANCH_DISPOSITION_LEDGER.md", "ARCHITECTURE-REFERENCE"),
        (root / "docs" / "engineering" / "CLINICAL_CHART_DISPOSITION.md", "ARCHITECTURE-REFERENCE"),
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


def check_orchestration_authority_links(root: Path, failures: list[str]) -> None:
    """Check the skill's two explicit inline authority links, not semantic compliance."""
    root = root.resolve()
    source_rel = ".agents/skills/dentix-orchestration/SKILL.md"
    source = root / source_rel
    expected_paths = (
        "PROJECT_STANDARDS.md",
        "docs/engineering/DEVELOPMENT_WORKFLOW.md",
    )
    try:
        if not source.resolve().is_relative_to(root) or not source.is_file():
            raise ValueError("source must be a file inside the repository")
        content = source.read_text(encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        failures.append(
            f"'{source_rel}' cannot supply required authority links to "
            f"{list(expected_paths)}: {exc}."
        )
        return

    # Consume code and comments in source order: their contents cannot open
    # another context. This is only a filter for this document's inline links.
    inline_code_pattern = (
        r"(?<!`)(?P<ticks>`+)(?!`)(?:(?!\n\s*\n)[\s\S])*?"
        r"(?<!`)(?P=ticks)(?!`)"
    )
    context_pattern = re.compile(
        r"(?P<comment><!--[\s\S]*?(?:-->|\Z))"
        r"|(?P<fence>^ {0,3}(?P<marker>`{3,}|~{3,})[^\n]*$)"
        r"|(?P<indented>^(?: {4,}|\t)[^\n]*)"
        rf"|(?P<inline>{inline_code_pattern})",
        re.MULTILINE,
    )
    prose: list[str] = []
    cursor = 0
    while match := context_pattern.search(content, cursor):
        prose.append(content[cursor:match.start()])
        cursor = match.end()
        if match.group("inline") is not None:
            # Preserve backtick-wrapped link labels; the link matcher below
            # consumes standalone code spans without counting their contents.
            prose.append(match.group(0))
        else:
            prose.append("\n")
            if match.group("fence") is not None:
                marker = match.group("marker")
                closing = re.compile(
                    r"^ {0,3}" + re.escape(marker[0])
                    + "{" + str(len(marker)) + r",}[ \t]*$",
                    re.MULTILINE,
                ).search(content, cursor)
                cursor = closing.end() if closing else len(content)
    prose.append(content[cursor:])
    content = "".join(prose)

    for expected_rel in expected_paths:
        expected = root / expected_rel
        label = re.escape(expected.name)
        # Consume inline code before considering link-shaped text inside it.
        # Ensure closing delimiter has exact count of backticks via lookbehind and lookahead.
        link_pattern = (
            inline_code_pattern
            + rf"|(?<![!\\])\[`?{label}`?\]\((?P<destination>[^)\r\n]*)\)"
        )
        destinations = [
            match.group("destination") for match in re.finditer(link_pattern, content)
            if match.group("destination") is not None
        ]
        if not destinations:
            failures.append(
                f"'{source_rel}' is missing an inline authority link to '{expected_rel}'."
            )
        try:
            canonical = expected.resolve()
            if not canonical.is_relative_to(root) or not canonical.is_file():
                raise ValueError("canonical target must be a file inside the repository")
        except (OSError, ValueError, RuntimeError) as exc:
            failures.append(f"'{source_rel}' requires canonical target '{expected_rel}': {exc}.")
            continue

        for destination in destinations:
            try:
                target_text = destination.strip()
                if target_text.startswith("<") and target_text.endswith(">"):
                    target_text = target_text[1:-1]
                url = urlsplit(target_text)
                if url.scheme or url.netloc or url.query or not url.path:
                    raise ValueError("expected a local file link")
                linked = (source.parent / unquote(url.path)).resolve()
                if not linked.is_relative_to(root) or linked != canonical or not linked.is_file():
                    raise ValueError("link does not resolve to the canonical file inside the repository")
            except (OSError, ValueError, RuntimeError) as exc:
                failures.append(
                    f"'{source_rel}' has invalid authority link '{destination}'; "
                    f"expected '{expected_rel}': {exc}."
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
    check_nine_layer_hierarchy(root, failures)
    check_historical_headers(root, failures)
    check_document_classifications(root, failures)
    check_external_skills_governance(root, failures)
    check_orchestration_authority_links(root, failures)

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
    print(f"  - Skill catalog and filesystem match bidirectionally ({skill_count} native skills detected)")
    print("  - DEVELOPMENT_WORKFLOW.md is authoritative across all entrypoints")
    print("  - Nine-layer authority hierarchy strictly verified in canonical order (1..9)")
    print("  - No obsolete .agent/ paths in active authorities")
    print("  - No retired agent-ci-signal references")
    print("  - No hardcoded coverage values in native skills or AI stack docs")
    print("  - Historical documents have required archive headers")
    print("  - Document classifications verified (RUNTIME-AI, ARCHITECTURE-REFERENCE, PRODUCT-SPEC)")
    print("  - External skills strictly subordinate to DENTIX standards")
    print("  - External skill lock schema, verifier, and pre-Movement-2 gate verified")
    print("  - Orchestration authority links resolve to canonical repository files (link integrity only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
