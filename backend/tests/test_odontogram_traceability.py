"""
Automated Deterministic Verification for Odontogram & Clinical VNext Traceability
=================================================================================
Validates requirement mapping against the historical master plan:
- docs/DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md
- docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md
- docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_PLAN_PATH = REPO_ROOT / "docs" / "DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md"
MATRIX_PATH = REPO_ROOT / "docs" / "product" / "ODONTOGRAM_TRACEABILITY_MATRIX.md"
PRODUCT_SPEC_PATH = REPO_ROOT / "docs" / "product" / "ODONTOGRAM_VNEXT_PRODUCT_SPEC.md"

EXPECTED_PHASE_TITLES = {
    "A0": "Baseline Revalidation and Freeze",
    "A1": "Final Chart Architecture Lock",
    "A2": "Frontend Chart Module Scaffold",
    "A3": "Anatomy Registry Foundation",
    "A4": "Crown Outline Integration",
    "A5": "Root Anatomy Definition",
    "A6": "Surface Geometry Foundation",
    "A7": "Renderer Contract",
    "A8": "Projection DTO for Demo Use",
    "A9": "Visual Rule Registry",
    "A10": "Root Layer Rendering",
    "A11": "Notation and Labels",
    "A12": "Demo Clinical Scenarios",
    "A13": "Multi-Instance and History Compare",
    "A14": "Basic UI Layer",
    "A15": "Mobile, RTL, and Accessibility",
    "A16": "Testing",
    "A17": "Evidence and Handoff Package",
    "G0": "Revalidation Before Full VNext",
    "G1": "Additive Clinical Core Schema",
    "G2": "Canonical Catalog, Taxonomy, and Workflow Templates",
    "G3": "Deterministic Legacy Mapping Engine",
    "G4": "Controlled Backfill",
    "G5": "Projection Layer and Real Chart Data",
    "G6": "Chart Integration to the Codex Renderer",
    "G7": "Command/API Layer",
    "G8": "Zero-Friction Charting UX",
    "G9": "First-Class Treatment Plans",
    "G10": "Sessions and Resume Engine",
    "G11": "Appointment Integration",
    "G12": "Lab Integration",
    "G13": "Inventory Integration",
    "G14": "Finance Integration and Parity",
    "G15": "Files and Clinical Context",
    "G16": "Rollout and Controlled Cutover",
    "R-M": "Review Micro-Tasks Per Gemini Phase",
}

EXPECTED_COUNTS = {
    "A0": 4, "A1": 4, "A2": 4, "A3": 5, "A4": 3, "A5": 6,
    "A6": 5, "A7": 4, "A8": 4, "A9": 5, "A10": 6, "A11": 3,
    "A12": 11, "A13": 4, "A14": 5, "A15": 8, "A16": 7, "A17": 7,
    "G0": 5, "G1": 18, "G2": 16, "G3": 13, "G4": 14, "G5": 10,
    "G6": 6, "G7": 16, "G8": 15, "G9": 14, "G10": 20, "G11": 12,
    "G12": 16, "G13": 11, "G14": 14, "G15": 9, "G16": 13, "R-M": 10,
}

VALID_CLASSIFICATIONS = {
    "ACTIVE_PRODUCT_REQUIREMENT",
    "ARCHITECTURE_CONSTRAINT",
    "HISTORICAL_EXECUTION_MECHANIC",
    "EVIDENCE_OR_HANDOFF_REQUIREMENT",
}

# Deterministic Expected Classifications Manifest
HISTORICAL_IDS = {
    "A0-M01", "A0-M02", "A0-M03", "A2-M04", "A17-M06", "A17-M07",
    "G0-M01", "G0-M02", "G0-M03", "G0-M04", "G0-M05",
}

ARCHITECTURE_IDS = {
    "A0-M04", "A1-M01", "A1-M02", "A1-M03", "A3-M05", "A4-M03", "A5-M06",
    "A7-M02", "A7-M04", "A10-M06", "A13-M03", "A14-M05", "G3-M08", "G3-M11",
    "G7-M15", "G7-M16", "G11-M08", "G12-M16", "G15-M01", "G16-M12", "G16-M13",
}

EVIDENCE_IDS = {
    "A16-M01", "A16-M02", "A16-M03", "A16-M04", "A16-M05", "A16-M06", "A16-M07",
    "A17-M01", "A17-M02", "A17-M03", "A17-M04", "A17-M05",
    "G1-M18", "G2-M16", "G3-M12", "G3-M13", "G4-M13", "G4-M14",
    "G5-M10", "G6-M06", "G9-M14", "G10-M20", "G11-M12", "G13-M11", "G14-M14",
    "G16-M11",
    "R-M01", "R-M02", "R-M03", "R-M04", "R-M05", "R-M06", "R-M07", "R-M08", "R-M09", "R-M10",
}


def get_expected_classification(item_id: str) -> str:
    if item_id in HISTORICAL_IDS:
        return "HISTORICAL_EXECUTION_MECHANIC"
    if item_id in ARCHITECTURE_IDS:
        return "ARCHITECTURE_CONSTRAINT"
    if item_id in EVIDENCE_IDS:
        return "EVIDENCE_OR_HANDOFF_REQUIREMENT"
    return "ACTIVE_PRODUCT_REQUIREMENT"


DESTINATIONS = {
    "ACTIVE_PRODUCT_REQUIREMENT": "docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md",
    "ARCHITECTURE_CONSTRAINT": "PROJECT_STANDARDS.md",
    "HISTORICAL_EXECUTION_MECHANIC": "docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md",
    "EVIDENCE_OR_HANDOFF_REQUIREMENT": "docs/engineering/DEVELOPMENT_WORKFLOW.md",
}


def parse_source_master_plan() -> dict[str, dict]:
    """Parse all source items and their exact acceptances from the historical master plan."""
    text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    phases: list[dict] = []
    current_phase: dict | None = None

    for i, line in enumerate(lines):
        m_p = re.match(r"^#\s+\d+\.\s+(?:Part\s+[I|V]+\s+)?(?:Phase\s+)?([AG]\d+|Review Micro-Tasks Per Gemini Phase)(?:(?:\s*[-—\u2013\u2014]\s*|\s+)(.*))?$", line)
        if m_p:
            pkey = "R-M" if "Review" in m_p.group(1) else m_p.group(1)
            ptitle = m_p.group(2).strip() if m_p.group(2) else m_p.group(1)
            current_phase = {"key": pkey, "title": ptitle, "line_num": i + 1, "raw_lines": []}
            phases.append(current_phase)
        elif current_phase:
            if line.startswith("# ") and any(c.isdigit() for c in line[:5]):
                current_phase = None
            else:
                current_phase["raw_lines"].append((i + 1, line))

    source_items: dict[str, dict] = {}
    for p in phases:
        pkey = p["key"]
        ptitle = p["title"]
        phase_display = f"{pkey} ({ptitle})" if pkey != "R-M" else "Review Micro-Tasks Per Gemini Phase"

        phase_acceptance = None
        for _, l in p["raw_lines"]:
            m_acc = re.match(r"^\s*\*\*Acceptance:?\*\*\s*(.*)$", l, re.IGNORECASE)
            if m_acc:
                phase_acceptance = m_acc.group(1).strip()

        phase_items: list[dict] = []
        for lnum, l in p["raw_lines"]:
            m_item = re.match(r"^##\s+(([AG]\d+-M\d+)|(R-M\d+))\s*[-—\u2013\u2014]\s*(.*)$", l)
            if m_item:
                item_id = m_item.group(1)
                item_title = m_item.group(4).strip()
                phase_items.append({
                    "id": item_id,
                    "phase_key": pkey,
                    "phase_title": ptitle,
                    "phase_display": phase_display,
                    "title": item_title,
                    "line_num": lnum,
                    "acceptance": None,
                })

        if pkey.startswith("A"):
            for it_idx, it in enumerate(phase_items):
                start_l = it["line_num"]
                end_l = phase_items[it_idx + 1]["line_num"] if it_idx + 1 < len(phase_items) else 999999
                for lnum, l in p["raw_lines"]:
                    if start_l <= lnum < end_l:
                        m_acc = re.match(r"^\s*\*\*Acceptance:?\*\*\s*(.*)$", l, re.IGNORECASE)
                        if m_acc:
                            it["acceptance"] = m_acc.group(1).strip()
        else:
            for it in phase_items:
                it["acceptance"] = f"Inherited phase acceptance: {phase_acceptance}"

        for it in phase_items:
            source_items[it["id"]] = it

    return source_items


def parse_source_phases() -> dict[str, dict]:
    """Parse phase-level definitions, micro-tasks, and acceptances from the master plan."""
    text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    phases: list[dict] = []
    current_phase: dict | None = None

    for i, line in enumerate(lines):
        m_p = re.match(r"^#\s+\d+\.\s+(?:Part\s+[I|V]+\s+)?(?:Phase\s+)?([AG]\d+|Review Micro-Tasks Per Gemini Phase)(?:(?:\s*[-—\u2013\u2014]\s*|\s+)(.*))?$", line)
        if m_p:
            pkey = "R-M" if "Review" in m_p.group(1) else m_p.group(1)
            ptitle = m_p.group(2).strip() if m_p.group(2) else m_p.group(1)
            current_phase = {"key": pkey, "title": ptitle, "line_num": i + 1, "raw_lines": []}
            phases.append(current_phase)
        elif current_phase:
            if line.startswith("# ") and any(c.isdigit() for c in line[:5]):
                current_phase = None
            else:
                current_phase["raw_lines"].append((i + 1, line))

    phase_dict: dict[str, dict] = {}
    for p in phases:
        pkey = p["key"]
        ptitle = p["title"]

        phase_acceptance = None
        for _, l in p["raw_lines"]:
            m_acc = re.match(r"^\s*\*\*Acceptance:?\*\*\s*(.*)$", l, re.IGNORECASE)
            if m_acc:
                phase_acceptance = m_acc.group(1).strip()
                break

        tasks: list[dict] = []
        for lnum, l in p["raw_lines"]:
            m_item = re.match(r"^##\s+(([AG]\d+-M\d+)|(R-M\d+))\s*[-—\u2013\u2014]\s*(.*)$", l)
            if m_item:
                tasks.append({"id": m_item.group(1), "title": m_item.group(4).strip()})

        phase_dict[pkey] = {
            "key": pkey,
            "title": ptitle,
            "tasks": tasks,
            "phase_acceptance": phase_acceptance,
        }

    return phase_dict


def parse_product_spec_phases() -> dict[str, dict]:
    """Parse phase rows from the Product Specification table."""
    text = PRODUCT_SPEC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    spec_phases: dict[str, dict] = {}
    in_table = False

    for line in lines:
        if line.startswith("| Phase | Source Phase Title |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("| **"):
            parts = [p.strip() for p in line.strip().split("|")[1:-1]]
            if len(parts) >= 4:
                phase_key = parts[0].replace("**", "").strip()
                phase_title = parts[1].strip()
                scope = parts[2].strip()
                acceptance = parts[3].strip()
                spec_phases[phase_key] = {
                    "key": phase_key,
                    "title": phase_title,
                    "scope": scope,
                    "acceptance": acceptance,
                }
        elif in_table and not line.startswith("|"):
            in_table = False

    return spec_phases


SPEC_CLASSIFICATION_NOTES = {
    "A0": "*Classification: Process setup (A0-M01..M03: Historical Mechanics; A0-M04: Architecture Constraint).* ",
    "A1": "*Classification: Architecture Constraints (A1-M01..M03) & Product Requirements (A1-M04).* ",
    "A16": "*Classification: Evidence & Handoff Requirements (A16-M01..M07).* ",
    "A17": "*Classification: Evidence Deliverables (A17-M01..M05) & Historical Mechanics (A17-M06..M07).* ",
    "G0": "*Classification: Historical Execution Mechanics (G0-M01..M05).* ",
}


def get_expected_phase_scope(phase: dict) -> str:
    prefix = SPEC_CLASSIFICATION_NOTES.get(phase["key"], "")
    tasks_repr = "; ".join(f"{t['id']}: {t['title']}" for t in phase["tasks"])
    return f"{prefix}{tasks_repr}"



def parse_matrix_table() -> list[dict]:
    """Parse all items from the comprehensive traceability matrix table."""
    text = MATRIX_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    matrix_items: list[dict] = []
    in_table = False

    for line in lines:
        if line.startswith("| Identifier | Source Phase |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("| `"):
            parts = [p.strip() for p in line.strip().split("|")[1:-1]]
            if len(parts) >= 7:
                item_id = parts[0].strip("`")
                source_phase = parts[1]
                title = parts[2]
                acceptance = parts[3]
                classification = parts[4].strip("`")
                destination = parts[5].strip("`")
                status = parts[6].strip("*")

                matrix_items.append({
                    "id": item_id,
                    "source_phase": source_phase,
                    "title": title,
                    "acceptance": acceptance,
                    "classification": classification,
                    "destination": destination,
                    "status": status,
                })
        elif in_table and not line.startswith("|"):
            in_table = False

    return matrix_items


def test_all_source_ids_accounted_for():
    source_items = parse_source_master_plan()
    matrix_items = parse_matrix_table()

    assert len(source_items) == 327, f"Expected 327 items in master plan, found {len(source_items)}"
    assert len(matrix_items) == 327, f"Expected 327 items in matrix, found {len(matrix_items)}"

    matrix_ids = {it["id"] for it in matrix_items}
    missing_ids = set(source_items.keys()) - matrix_ids
    assert not missing_ids, f"Traceability matrix is missing source IDs: {sorted(missing_ids)}"


def test_no_duplicate_ids_in_matrix():
    matrix_items = parse_matrix_table()
    ids = [it["id"] for it in matrix_items]
    duplicates = [item_id for item_id in ids if ids.count(item_id) > 1]
    assert not duplicates, f"Found duplicate IDs in traceability matrix: {set(duplicates)}"


def test_exact_id_ranges_and_counts_per_phase():
    matrix_items = parse_matrix_table()
    counts_by_phase: dict[str, int] = {}

    for it in matrix_items:
        prefix = it["id"].split("-")[0]
        if prefix == "R":
            phase_key = "R-M"
        else:
            phase_key = prefix

        counts_by_phase[phase_key] = counts_by_phase.get(phase_key, 0) + 1

    for phase_key, expected_count in EXPECTED_COUNTS.items():
        actual_count = counts_by_phase.get(phase_key, 0)
        assert actual_count == expected_count, (
            f"Phase {phase_key} count mismatch: expected {expected_count}, got {actual_count}"
        )


def test_r_m_independent_from_g16():
    """Verify R-M review protocol is strictly separated from G16 rollout."""
    matrix_items = parse_matrix_table()

    g16_items = [it for it in matrix_items if it["id"].startswith("G16-")]
    rm_items = [it for it in matrix_items if it["id"].startswith("R-M")]

    assert len(g16_items) == 13, f"Expected 13 G16 items, found {len(g16_items)}"
    assert len(rm_items) == 10, f"Expected 10 R-M items, found {len(rm_items)}"

    # G16 range ends at G16-M13
    assert g16_items[-1]["id"] == "G16-M13"
    # R-M range ends at R-M10
    assert rm_items[-1]["id"] == "R-M10"

    # No R-M item has G16 as its source phase
    for it in rm_items:
        assert "G16" not in it["source_phase"], f"R-M item {it['id']} incorrectly maps to G16: {it['source_phase']}"
        assert "Review Micro-Tasks" in it["source_phase"], f"R-M item {it['id']} missing review phase title: {it['source_phase']}"
        assert "controlled rollout succeeds" not in it["acceptance"], (
            f"R-M item {it['id']} incorrectly inherited G16 acceptance: {it['acceptance']}"
        )
        assert "review report committed" in it["acceptance"], (
            f"R-M item {it['id']} missing correct review acceptance: {it['acceptance']}"
        )


def test_phase_titles_match_source_master_plan():
    source_items = parse_source_master_plan()
    matrix_items = parse_matrix_table()

    # Confirmed correction phases
    assert EXPECTED_PHASE_TITLES["A0"] == "Baseline Revalidation and Freeze"
    assert EXPECTED_PHASE_TITLES["G10"] == "Sessions and Resume Engine"
    assert EXPECTED_PHASE_TITLES["G12"] == "Lab Integration"
    assert EXPECTED_PHASE_TITLES["G14"] == "Finance Integration and Parity"
    assert EXPECTED_PHASE_TITLES["G16"] == "Rollout and Controlled Cutover"
    assert EXPECTED_PHASE_TITLES["R-M"] == "Review Micro-Tasks Per Gemini Phase"

    for it in matrix_items:
        item_id = it["id"]
        source_it = source_items[item_id]
        phase_key = source_it["phase_key"]
        expected_title = EXPECTED_PHASE_TITLES[phase_key]
        assert expected_title in it["source_phase"], (
            f"Item {item_id} phase title mismatch: expected '{expected_title}' in '{it['source_phase']}'"
        )


def test_titles_and_acceptance_lossless_equality():
    """Verify lossless match between source master plan and matrix table for every ID."""
    source_items = parse_source_master_plan()
    matrix_items = parse_matrix_table()

    for it in matrix_items:
        iid = it["id"]
        src = source_items[iid]

        # 1. Exact Title Equality
        assert it["title"] == src["title"], (
            f"Title mismatch for {iid}: source='{src['title']}', matrix='{it['title']}'"
        )

        # 2. Acceptance Equality & No Empty Acceptance
        assert it["acceptance"], f"Unexplained empty acceptance for item {iid}"
        assert it["acceptance"] == src["acceptance"], (
            f"Acceptance mismatch for {iid}: expected='{src['acceptance']}', actual='{it['acceptance']}'"
        )


def test_classifications_match_deterministic_manifest():
    """Verify that every requirement's classification and destination match the deterministic manifest."""
    matrix_items = parse_matrix_table()

    for it in matrix_items:
        iid = it["id"]
        expected_cls = get_expected_classification(iid)
        actual_cls = it["classification"]

        assert actual_cls == expected_cls, (
            f"Classification mismatch for {iid}: expected '{expected_cls}', got '{actual_cls}'"
        )

        expected_dest = DESTINATIONS[expected_cls]
        actual_dest = it["destination"]
        assert actual_dest == expected_dest, (
            f"Destination mismatch for {iid}: expected '{expected_dest}', got '{actual_dest}'"
        )

    # Explicit checks from Finding 5
    assert get_expected_classification("G16-M10") == "ACTIVE_PRODUCT_REQUIREMENT"
    assert get_expected_classification("G16-M11") == "EVIDENCE_OR_HANDOFF_REQUIREMENT"
    assert get_expected_classification("G16-M12") == "ARCHITECTURE_CONSTRAINT"
    assert get_expected_classification("G16-M13") == "ARCHITECTURE_CONSTRAINT"
    for num in range(1, 11):
        rm_id = f"R-M{num:02d}"
        assert get_expected_classification(rm_id) == "EVIDENCE_OR_HANDOFF_REQUIREMENT"


def test_product_spec_phases_exact_positive_equality():
    """Verify deterministic positive equality between source master plan and product spec.

    Requires:
    - Exactly 35 phases (A0-A17, G0-G16); fails on missing, extra, or replaced phases.
    - Each phase title matches source master plan phase title.
    - Product spec phase scope strictly equals deterministic representation of exact source micro-task titles.
    - For G phases, exact phase-acceptance equality.
    - For A phases, exact reference to ODONTOGRAM_TRACEABILITY_MATRIX.md.
    """
    source_phases = parse_source_phases()
    spec_phases = parse_product_spec_phases()

    expected_phase_keys = [k for k in EXPECTED_PHASE_TITLES.keys() if k != "R-M"]
    assert len(expected_phase_keys) == 35

    assert set(spec_phases.keys()) == set(expected_phase_keys), (
        f"Phase mismatch between source and product spec: "
        f"missing={set(expected_phase_keys) - set(spec_phases.keys())}, "
        f"extra={set(spec_phases.keys()) - set(expected_phase_keys)}"
    )

    for pkey in expected_phase_keys:
        src = source_phases[pkey]
        spec = spec_phases[pkey]

        # 1. Title equality
        assert spec["title"] == src["title"], (
            f"Phase title mismatch for {pkey}: spec='{spec['title']}', source='{src['title']}'"
        )

        # 2. Scope equality (deterministic representation of exact source micro-task titles)
        expected_scope = get_expected_phase_scope(src)
        assert spec["scope"] == expected_scope, (
            f"Phase {pkey} scope divergence from source micro-task titles:\n"
            f"Expected: {expected_scope}\n"
            f"Actual:   {spec['scope']}"
        )

        # 3. Acceptance equality
        if pkey.startswith("A"):
            expected_acc = "Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md."
            assert spec["acceptance"] == expected_acc, (
                f"Phase {pkey} acceptance must refer to matrix: got '{spec['acceptance']}'"
            )
        else:
            assert src["phase_acceptance"], f"Source missing phase acceptance for {pkey}"
            assert spec["acceptance"] == src["phase_acceptance"], (
                f"Phase {pkey} acceptance mismatch: expected='{src['phase_acceptance']}', spec='{spec['acceptance']}'"
            )


def test_a_phases_individual_acceptance_verified_in_matrix():
    """Verify all individual A-phase acceptance criteria through the traceability matrix."""
    source_items = parse_source_master_plan()
    matrix_items = parse_matrix_table()

    matrix_by_id = {it["id"]: it for it in matrix_items}
    a_items = [it for it in source_items.values() if it["phase_key"].startswith("A")]

    for it in a_items:
        iid = it["id"]
        assert iid in matrix_by_id, f"A-phase item {iid} missing from traceability matrix"
        mat_it = matrix_by_id[iid]
        assert mat_it["acceptance"], f"A-phase item {iid} has empty acceptance in matrix"
        assert mat_it["acceptance"] == it["acceptance"], (
            f"A-phase item {iid} acceptance mismatch: source='{it['acceptance']}', matrix='{mat_it['acceptance']}'"
        )


def test_explicit_clinical_invariants_g11_m08_and_g13_m06():
    """Verify explicit clinical invariants G11-M08 and G13-M06 are enforced."""
    source_items = parse_source_master_plan()
    spec_text = PRODUCT_SPEC_PATH.read_text(encoding="utf-8")

    # Invariant G11-M08: No auto-booking
    assert "G11-M08" in source_items
    assert source_items["G11-M08"]["title"] == "Prevent auto-booking without user action"
    assert "G11-M08" in spec_text
    assert "auto-booking" in spec_text.lower() or "auto-book" in spec_text.lower()

    # Invariant G13-M06: Actual use point deduction (never at plan creation)
    assert "G13-M06" in source_items
    assert source_items["G13-M06"]["title"] == "Deduct at actual use point"
    assert "G13-M05" in source_items
    assert source_items["G13-M05"]["title"] == "Prevent stock deduction at plan creation"
    assert "G13-M06" in spec_text or "actual-use point" in spec_text.lower()


def test_deterministic_test_detects_mutations():
    """Regression test: prove deterministic equality detects all 4 historical mutations."""
    source_phases = parse_source_phases()

    # 1. Replacing implant/bridge with other fixtures in A12
    a12_mutated = dict(source_phases["A12"])
    a12_mutated_tasks = [
        t for t in a12_mutated["tasks"]
        if "implant" not in t["title"].lower() and "bridge" not in t["title"].lower()
    ]
    a12_mutated_tasks.append({"id": "A12-M09", "title": "Create planned extraction fixture"})
    a12_mutated_tasks.append({"id": "A12-M10", "title": "Create mixed pathology fixture"})
    a12_mutated["tasks"] = a12_mutated_tasks
    mutated_scope = get_expected_phase_scope(a12_mutated)
    assert mutated_scope != get_expected_phase_scope(source_phases["A12"])
    assert "implant" not in mutated_scope

    # 2. Upgrading future notation abstraction into current notation support in A11
    a11_mutated = dict(source_phases["A11"])
    a11_mutated["tasks"] = [
        {"id": "A11-M01", "title": "Support current notation display mode"},
        {"id": "A11-M02", "title": "Implement dual FDI/Universal notation and A-T primary lettering"},
        {"id": "A11-M03", "title": "Verify label placement after roots"},
    ]
    mutated_scope = get_expected_phase_scope(a11_mutated)
    assert mutated_scope != get_expected_phase_scope(source_phases["A11"])
    assert "dual FDI/Universal" in mutated_scope

    # 3. Classifying all premolars as single-root in A5
    a5_mutated = dict(source_phases["A5"])
    a5_mutated["tasks"] = [
        {"id": "A5-M01", "title": "Create root outline model"},
        {"id": "A5-M02", "title": "Add single-root anterior definitions (incisors, canines, premolars)"},
        {"id": "A5-M03", "title": "Add premolar root definitions"},
        {"id": "A5-M04", "title": "Add molar root definitions"},
        {"id": "A5-M05", "title": "Add primary tooth root definitions"},
        {"id": "A5-M06", "title": "Keep root style visually aligned"},
    ]
    mutated_scope = get_expected_phase_scope(a5_mutated)
    assert mutated_scope != get_expected_phase_scope(source_phases["A5"])

    # 4. Adding batch/lot to G13 or unsupported lab lifecycle to G12
    g13_mutated = dict(source_phases["G13"])
    g13_mutated["tasks"] = list(g13_mutated["tasks"]) + [
        {"id": "G13-M12", "title": "Add inventory batch and lot tracking"},
    ]
    mutated_scope = get_expected_phase_scope(g13_mutated)
    assert mutated_scope != get_expected_phase_scope(source_phases["G13"])

    g12_mutated = dict(source_phases["G12"])
    g12_mutated["tasks"] = list(g12_mutated["tasks"]) + [
        {"id": "G12-M17", "title": "Add lab dispatch, receipt, and return tracking"},
    ]
    mutated_scope = get_expected_phase_scope(g12_mutated)
    assert mutated_scope != get_expected_phase_scope(source_phases["G12"])


def test_product_spec_rejects_unsourced_semantics():
    """Verify that unsupported or invented clinical semantics are rejected from the product spec."""
    spec_text = PRODUCT_SPEC_PATH.read_text(encoding="utf-8")

    unsupported_phrases = [
        "periodontal measurement",
        "optimistic UI",
        "ETag",
        "impression date",
        "lab partner",
        "delivery tracking",
        "invoice draft",
        "insurance claim",
        "ledger immutability",
        "CBCT",
        "batch/lot",
        "lot tracking",
        "dispatch tracking",
        "receipt tracking",
    ]

    for phrase in unsupported_phrases:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        assert not pattern.search(spec_text), (
            f"Product spec contains unsupported/invented phrase: '{phrase}'"
        )


def test_product_spec_core_invariants_and_clarity():
    spec_text = PRODUCT_SPEC_PATH.read_text(encoding="utf-8")

    # Document classification
    assert "<!-- CLASSIFICATION: PRODUCT-SPEC -->" in spec_text or "Classification: PRODUCT-SPEC" in spec_text

    # Verified phase titles
    for phase_key, title in EXPECTED_PHASE_TITLES.items():
        if phase_key == "R-M":
            continue
        assert title in spec_text, f"Product spec missing phase title: '{title}' for phase {phase_key}"

    # Critical invariant: G11-M08 no-auto-booking
    assert "G11-M08" in spec_text
    assert "auto-booking" in spec_text.lower() or "auto-book" in spec_text.lower()

    # Inventory timing invariant
    assert "actual-use point" in spec_text.lower()
