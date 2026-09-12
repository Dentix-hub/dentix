"""
Tests for DENTIX Clinical VNext Phase G3: Deterministic Legacy Mapping Engine.
Verifies G3-M01 through G3-M13:

- G3-M01: Scaffold & Exports (all DTOs, allowlists, functions exported; immutability enforced).
- G3-M02: Treatment Procedure Mapping (exact allowlist only; rejections for substring/fuzzy/arbitrary phrases).
- G3-M03: Treatment Status Mapping (exact: Done->completed, Pending->planned, In Progress->active; unknowns ambiguous).
- G3-M04: Tooth Notation Mapping (FDI priority, Universal 1..32 table, Palmer full-string grammar, invalid ambiguous, no anatomy guessing).
- G3-M05: Treatment to Work Item Draft (ownership, procedure, status, target deterministic; verbatim carried text; decimal safety).
- G3-M06: Treatment to Event Draft (append-oriented event draft, payload frozen, occurred_at/doctor_id preserved).
- G3-M07: ToothStatus Mapping (exact allowlist for lifecycle/finding/procedure; raw condition preserved; unknown ambiguous).
- G3-M08: TreatmentSession Mapping (requires verified parent Treatment; notes preserved; never parse steps).
- G3-M09: Verbatim Free-Text & No Parsing (sessions/notes treated as opaque string; never parse).
- G3-M10: Exact Singleton Lab Link Rejection Matrix (strictly Link:LabOrder:<id>; missing/multiple/malformed/cross-tenant rejected).
- G3-M11: Exact Duplicates vs Near Duplicates (exact duplicates marked ambiguous, never merged/dropped; near duplicates unflagged).
- G3-M12: Idempotency & Deterministic Keys (repeated calls identical; SHA-256 stable versioned keys across tenants/sources).
- G3-M13: Tenant Isolation & Nullable Tenant (null tenant inherits verified patient ownership; mismatches rejected; no cross-tenant leakage).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
import pytest

from backend.clinical.legacy_mapping import canonical_json_dumps, to_canonical_tagged
from backend.clinical import (
    LEGACY_PROCEDURE_ALLOWLIST,
    LEGACY_STATUS_ALLOWLIST,
    TOOTH_STATUS_FINDING_ALLOWLIST,
    TOOTH_STATUS_LIFECYCLE_ALLOWLIST,
    TOOTH_STATUS_PROCEDURE_ALLOWLIST,
    UNIVERSAL_TO_FDI_TABLE,
    LegacyCareSessionDraft,
    LegacyEventDraft,
    LegacyEventTargetDraft,
    LegacyLabLinkDraft,
    LegacyMappingBatchResult,
    LegacyMappingIssue,
    LegacyWorkItemDraft,
    LegacyWorkItemTargetDraft,
    VerifiedPatientContext,
    compute_care_session_canonical_fingerprint,
    compute_event_canonical_fingerprint,
    compute_lab_link_canonical_fingerprint,
    compute_work_item_canonical_fingerprint,
    deep_freeze,
    generate_stable_mapping_key,
    map_legacy_clinical_batch,
    map_legacy_procedure,
    map_legacy_status,
    map_legacy_tooth_notation,
    map_legacy_tooth_status,
    map_legacy_tooth_status_condition,
    map_legacy_treatment,
    map_legacy_treatment_session,
    mark_ambiguous_duplicates,
    parse_exact_lab_link_token,
    resolve_exact_lab_link,
)
from backend.clinical.catalog import (
    FindingCode,
    ProcedureCode,
    ToothLifecycleCode,
    TreatmentLifecycleCode,
)
from backend.models.clinical import (
    LabOrder,
    ToothStatus,
    Treatment,
    TreatmentSession,
)
from backend.models.clinical_core import FDI_TOOTH_KEYS


# Helper for snapshotting ORM attributes to verify immutability
def snapshot_orm(obj: object, attrs: tuple[str, ...]) -> dict[str, object]:
    return {attr: getattr(obj, attr, None) for attr in attrs}


# ===========================================================================
# G3-M01: Scaffold and Exports
# ===========================================================================

def test_g3_m01_exports_and_immutability():
    """Verify all G3 exports are present on backend.clinical and DTOs are deeply frozen."""
    context = VerifiedPatientContext(patient_id=10, tenant_id=1)
    assert context.patient_id == 10
    assert context.tenant_id == 1

    with pytest.raises((FrozenInstanceError, TypeError)):
        context.patient_id = 20  # type: ignore

    with pytest.raises(ValueError, match="positive integer"):
        VerifiedPatientContext(patient_id=0, tenant_id=1)

    target = LegacyWorkItemTargetDraft(tenant_id=1, target_kind="tooth", tooth_key="14")
    with pytest.raises((FrozenInstanceError, TypeError)):
        target.tooth_key = "15"  # type: ignore

    issue = LegacyMappingIssue(
        code="TEST",
        message="Test issue",
        source_kind="treatment",
        source_id=1,
    )
    with pytest.raises((FrozenInstanceError, TypeError)):
        issue.code = "MODIFIED"  # type: ignore


# ===========================================================================
# G3-M02: Exact Treatment Procedure Mapping
# ===========================================================================

def test_g3_m02_procedure_mapping_exact_allowlist():
    """Verify exact procedure mapping and strict rejection of fuzzy/substring/arbitrary matches."""
    # Canonical matches
    code, issue = map_legacy_procedure("REST_COMPOSITE")
    assert code == ProcedureCode.REST_COMPOSITE.value
    assert issue is None

    code, issue = map_legacy_procedure("Composite Filling")
    assert code == ProcedureCode.REST_COMPOSITE.value
    assert issue is None

    code, issue = map_legacy_procedure("Root Canal")
    assert code == ProcedureCode.ENDO_RCT.value
    assert issue is None

    code, issue = map_legacy_procedure("Crown")
    assert code == ProcedureCode.PROS_CROWN.value
    assert issue is None

    code, issue = map_legacy_procedure("Simple Extraction")
    assert code == ProcedureCode.SURG_EXTRACTION.value
    assert issue is None

    code, issue = map_legacy_procedure("Fixed Bridge")
    assert code == ProcedureCode.PROS_BRIDGE.value
    assert issue is None

    # Seed arabic literals
    code, issue = map_legacy_procedure("حشو كومبوزيت -- Composite Filling Class I")
    assert code == ProcedureCode.REST_COMPOSITE.value
    assert issue is None

    code, issue = map_legacy_procedure("تاج بورسلين – Porcelain Crown")
    assert code == ProcedureCode.PROS_CROWN.value
    assert issue is None

    # Rejections: Arbitrary phrases, substring matches, case-folded, untrimmed
    rejections = [
        "Old Filling",
        "Legacy crown",
        "Filling A",
        "Filling B",
        "filling",
        "composite filling",
        "  Composite Filling  ",
        "Root Canal Therapy",
        "Crown Prep",
        "Unknown Procedure",
        "",
    ]
    for raw in rejections:
        c, iss = map_legacy_procedure(raw)
        assert c is None
        assert iss is not None
        assert iss.is_ambiguity is True
        assert iss.raw_value == raw


# ===========================================================================
# G3-M03: Exact Treatment Status Mapping
# ===========================================================================

def test_g3_m03_status_mapping_exact():
    """Verify exact status mapping: Done->completed, Pending->planned, In Progress->active."""
    assert map_legacy_status("Done") == (TreatmentLifecycleCode.COMPLETED.value, None)
    assert map_legacy_status("Pending") == (TreatmentLifecycleCode.PLANNED.value, None)
    assert map_legacy_status("In Progress") == (TreatmentLifecycleCode.ACTIVE.value, None)

    # Lowercase or unknown forms must be rejected as ambiguous
    invalid_statuses = ["done", "DONE", "pending", "in progress", "in_progress", "Draft", "Cancelled", "Deleted"]
    for s in invalid_statuses:
        code, iss = map_legacy_status(s)
        assert code is None
        assert iss is not None
        assert iss.is_ambiguity is True
        assert iss.raw_value == s


def test_g3_m03_canonical_forms_rejected_as_ambiguous():
    """Verify that already-canonical lifecycle forms are rejected as ambiguous with raw value preserved."""
    canonical_forms = ["completed", "planned", "active", "proposed", "cancelled"]
    for form in canonical_forms:
        code, iss = map_legacy_status(form)
        assert code is None
        assert iss is not None
        assert iss.is_ambiguity is True
        assert iss.code == "UNKNOWN_STATUS_CODE"
        assert iss.raw_value == form


# ===========================================================================
# G3-M04: Tooth Notation Mapping
# ===========================================================================

def test_g3_m04_tooth_notation_fdi_priority_universal_palmer():
    """Verify FDI priority, Universal 1..32 table, Palmer full-string grammar, and invalid handling."""
    # 1. FDI Priority (values valid in FDI must resolve to FDI)
    assert map_legacy_tooth_notation("11") == ("11", None)
    assert map_legacy_tooth_notation(11) == ("11", None)
    assert map_legacy_tooth_notation(18) == ("18", None)
    assert map_legacy_tooth_notation(46) == ("46", None)
    assert map_legacy_tooth_notation(55) == ("55", None)
    assert map_legacy_tooth_notation(85) == ("85", None)

    # 2. Universal 1..32 via table for values not in FDI
    # Universal 1 is FDI 18 (1 is not in FDI_TOOTH_KEYS)
    assert map_legacy_tooth_notation(1) == ("18", None)
    assert map_legacy_tooth_notation("1") == ("18", None)
    assert map_legacy_tooth_notation(9) == ("21", None)
    assert map_legacy_tooth_notation(19) == ("36", None)
    assert map_legacy_tooth_notation(30) == ("46", None)

    # 3. Palmer full-string quadrant + position grammar
    assert map_legacy_tooth_notation("UR1") == ("11", None)
    assert map_legacy_tooth_notation("UR 1") == ("11", None)
    assert map_legacy_tooth_notation("UL8") == ("28", None)
    assert map_legacy_tooth_notation("LL3") == ("33", None)
    assert map_legacy_tooth_notation("LR5") == ("45", None)
    assert map_legacy_tooth_notation("UR A") == ("51", None)
    assert map_legacy_tooth_notation("URA") == ("51", None)
    assert map_legacy_tooth_notation("UL E") == ("65", None)
    assert map_legacy_tooth_notation("LR E") == ("85", None)

    # 4. Invalid / Substring / Free-text rejections
    invalid_teeth = [
        "Upper right tooth 3",
        "tooth 14",
        "UR 9",
        "LL 0",
        "LR F",
        "99",
        "-5",
        "abc",
    ]
    for raw in invalid_teeth:
        tooth, iss = map_legacy_tooth_notation(raw)
        assert tooth is None
        assert iss is not None
        assert iss.is_ambiguity is True


# ===========================================================================
# G3-M05 & M06: Treatment to Work Item and Event Drafts
# ===========================================================================

def test_g3_m05_and_m06_treatment_mapping_and_immutability():
    """Verify Treatment mapping into WorkItem and Event drafts without mutating source ORM row."""
    treatment = Treatment(
        id=501,
        patient_id=42,
        tenant_id=1,
        tooth_number=16,
        procedure="Composite Filling",
        status="Done",
        diagnosis="Caries on occlusal",
        cost=Decimal("250.00"),
        discount=Decimal("25.00"),
        date=datetime(2026, 4, 15, 10, 30, tzinfo=timezone.utc),
        doctor_id=7,
        notes="Regular patient check",
        sessions="2 sessions completed",
        complications="None",
    )

    # Snapshot attributes to verify source row immutability
    monitored_attrs = (
        "id", "patient_id", "tenant_id", "tooth_number", "procedure",
        "status", "diagnosis", "cost", "discount", "notes", "sessions", "complications"
    )
    before_snapshot = snapshot_orm(treatment, monitored_attrs)

    context = VerifiedPatientContext(patient_id=42, tenant_id=1)
    wi_draft, ev_draft, issues = map_legacy_treatment(treatment, context)

    # Verify source row was not mutated
    after_snapshot = snapshot_orm(treatment, monitored_attrs)
    assert before_snapshot == after_snapshot

    assert len(issues) == 0
    assert wi_draft is not None
    assert ev_draft is not None

    # Work Item Draft verification
    assert wi_draft.tenant_id == 1
    assert wi_draft.patient_id == 42
    assert wi_draft.code == ProcedureCode.REST_COMPOSITE.value
    assert wi_draft.status == TreatmentLifecycleCode.COMPLETED.value
    assert wi_draft.targets[0].tooth_key == "16"
    assert wi_draft.targets[0].target_kind == "tooth"
    assert wi_draft.cost == Decimal("250.00")
    assert wi_draft.discount == Decimal("25.00")
    assert wi_draft.diagnosis == "Caries on occlusal"
    assert wi_draft.notes == "Regular patient check"
    assert wi_draft.sessions == "2 sessions completed"
    assert wi_draft.complications == "None"
    assert wi_draft.created_by_user_id == 7
    assert wi_draft.source_kind == "treatment"
    assert wi_draft.source_id == 501
    assert wi_draft.stable_key.startswith("k_v1_")

    # Event Draft verification
    assert ev_draft.tenant_id == 1
    assert ev_draft.patient_id == 42
    assert ev_draft.event_type == "procedure_recorded"
    assert ev_draft.actor_user_id == 7
    assert ev_draft.occurred_at == datetime(2026, 4, 15, 10, 30, tzinfo=timezone.utc)
    assert ev_draft.targets[0].tooth_key == "16"
    assert ev_draft.payload["procedure"] == ProcedureCode.REST_COMPOSITE.value
    assert ev_draft.payload["status"] == TreatmentLifecycleCode.COMPLETED.value
    assert ev_draft.source_id == 501


# ===========================================================================
# G3-M07: ToothStatus Condition Mapping
# ===========================================================================

def test_g3_m07_tooth_status_mapping():
    """Verify ToothStatus mapping to lifecycle, finding, and procedure events."""
    context = VerifiedPatientContext(patient_id=42, tenant_id=1)

    # 1. Lifecycle: Healthy -> PRESENT
    ts1 = ToothStatus(id=1, patient_id=42, tenant_id=1, tooth_number=11, condition="Healthy")
    ev1, issues1 = map_legacy_tooth_status(ts1, context)
    assert len(issues1) == 0
    assert ev1 is not None
    assert ev1.event_type == "tooth_lifecycle_changed"
    assert ev1.payload["canonical_code"] == ToothLifecycleCode.PRESENT.value
    assert ev1.targets[0].tooth_key == "11"

    # 2. Lifecycle: Missing -> MISSING
    ts2 = ToothStatus(id=2, patient_id=42, tenant_id=1, tooth_number=18, condition="Missing")
    ev2, issues2 = map_legacy_tooth_status(ts2, context)
    assert ev2.event_type == "tooth_lifecycle_changed"
    assert ev2.payload["canonical_code"] == ToothLifecycleCode.MISSING.value

    # 3. Finding: Caries -> CARIES
    ts3 = ToothStatus(id=3, patient_id=42, tenant_id=1, tooth_number=21, condition="Caries")
    ev3, issues3 = map_legacy_tooth_status(ts3, context)
    assert ev3.event_type == "finding_recorded"
    assert ev3.payload["canonical_code"] == FindingCode.CARIES.value

    # 4. Finding: Pain -> PAIN
    ts4 = ToothStatus(id=4, patient_id=42, tenant_id=1, tooth_number=36, condition="Pain")
    ev4, issues4 = map_legacy_tooth_status(ts4, context)
    assert ev4.event_type == "finding_recorded"
    assert ev4.payload["canonical_code"] == FindingCode.PAIN.value

    # 5. Procedure: RootCanal -> ENDO_RCT
    ts5 = ToothStatus(id=5, patient_id=42, tenant_id=1, tooth_number=46, condition="RootCanal")
    ev5, issues5 = map_legacy_tooth_status(ts5, context)
    assert ev5.event_type == "procedure_recorded"
    assert ev5.payload["canonical_code"] == ProcedureCode.ENDO_RCT.value

    # 6. Unknown condition -> Ambiguity issue
    ts_unk = ToothStatus(id=6, patient_id=42, tenant_id=1, tooth_number=14, condition="Discolored")
    ev_unk, issues_unk = map_legacy_tooth_status(ts_unk, context)
    assert ev_unk is None
    assert len(issues_unk) == 1
    assert issues_unk[0].is_ambiguity is True
    assert issues_unk[0].code == "UNKNOWN_TOOTH_STATUS_CONDITION"


# ===========================================================================
# G3-M08 & M09: TreatmentSession Mapping and Verbatim Preservation
# ===========================================================================

def test_g3_m08_and_m09_treatment_session_mapping_and_verbatim_opaque():
    """Verify TreatmentSession mapping requires verified parent Treatment, preserving notes verbatim."""
    context = VerifiedPatientContext(patient_id=10, tenant_id=2)

    parent_t = Treatment(id=200, patient_id=10, tenant_id=2, tooth_number=11, procedure="Root Canal", status="Done")
    session = TreatmentSession(
        id=701,
        treatment_id=200,
        tenant_id=2,
        notes="Session 1: Instrumentation up to file #25. Canal irrigated with NaOCl. Step: 1, Observation: dried.",
        session_date=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
    )

    cs_draft, issues = map_legacy_treatment_session(session, context, parent_t)
    assert len(issues) == 0
    assert cs_draft is not None
    assert cs_draft.parent_treatment_id == 200
    assert cs_draft.tenant_id == 2
    assert cs_draft.patient_id == 10
    # Verbatim preservation: steps are NOT parsed into objects
    assert "Instrumentation up to file #25" in cs_draft.notes

    # Missing parent treatment produces issue
    cs_missing, issues_missing = map_legacy_treatment_session(session, context, None)
    assert cs_missing is None
    assert issues_missing[0].code == "MISSING_PARENT_TREATMENT"

    # Mismatched parent treatment ID
    parent_other = Treatment(id=201, patient_id=10, tenant_id=2)
    cs_mismatch, issues_mismatch = map_legacy_treatment_session(session, context, parent_other)
    assert cs_mismatch is None
    assert issues_mismatch[0].code == "PARENT_TREATMENT_ID_MISMATCH"


# ===========================================================================
# G3-M10: Exact Singleton Lab Link Rejection Matrix
# ===========================================================================

def test_g3_m10_exact_singleton_lab_link_rejection_matrix():
    """Test comprehensive rejection matrix for exact singleton lab link."""
    context = VerifiedPatientContext(patient_id=5, tenant_id=1)

    # 1. Valid exact singleton
    t_valid = Treatment(id=1, patient_id=5, tenant_id=1, notes="Link:LabOrder:101")
    lo_valid = LabOrder(id=101, patient_id=5, tenant_id=1)
    link, issue = resolve_exact_lab_link(t_valid, [lo_valid], context)
    assert issue is None
    assert link is not None
    assert link.treatment_id == 1
    assert link.lab_order_id == 101
    assert link.link_token == "Link:LabOrder:101"

    # 2. Lab order not found
    link_nf, issue_nf = resolve_exact_lab_link(t_valid, [], context)
    assert link_nf is None
    assert issue_nf.code == "LAB_ORDER_NOT_FOUND"

    # 3. Multiple matching lab orders (ambiguous)
    lo_dup1 = LabOrder(id=101, patient_id=5, tenant_id=1)
    lo_dup2 = LabOrder(id=101, patient_id=5, tenant_id=1)
    link_dup, issue_dup = resolve_exact_lab_link(t_valid, [lo_dup1, lo_dup2], context)
    assert link_dup is None
    assert issue_dup.code == "AMBIGUOUS_MULTIPLE_LAB_ORDERS"

    # 4. Malformed lab link notes
    malformed_notes = [
        "Link:LabOrder:0",
        "Link:LabOrder:-10",
        "Link:LabOrder:abc",
        " Link:LabOrder:101",
        "Link:LabOrder:101 ",
        "prefix Link:LabOrder:101",
        "Link:LabOrder:101 and some extra text",
    ]
    for mf in malformed_notes:
        t_mf = Treatment(id=2, patient_id=5, tenant_id=1, notes=mf)
        link_mf, issue_mf = resolve_exact_lab_link(t_mf, [lo_valid], context)
        assert link_mf is None
        assert issue_mf.code == "MALFORMED_LAB_LINK_NOTE"

    # 5. Cross-tenant rejection
    lo_cross_tenant = LabOrder(id=101, patient_id=5, tenant_id=2)
    link_ct, issue_ct = resolve_exact_lab_link(t_valid, [lo_cross_tenant], context)
    assert link_ct is None
    assert issue_ct.code == "CROSS_TENANT_LAB_LINK_REJECTED"

    # 6. Cross-patient rejection
    lo_cross_patient = LabOrder(id=101, patient_id=999, tenant_id=1)
    link_cp, issue_cp = resolve_exact_lab_link(t_valid, [lo_cross_patient], context)
    assert link_cp is None
    assert issue_cp.code == "CROSS_PATIENT_LAB_LINK_REJECTED"

    # 7. Unrelated notes without lab link token produce no link and no error
    t_unrelated = Treatment(id=3, patient_id=5, tenant_id=1, notes="Routine composite filling placed.")
    link_unrelated, issue_unrelated = resolve_exact_lab_link(t_unrelated, [lo_valid], context)
    assert link_unrelated is None
    assert issue_unrelated is None


# ===========================================================================
# G3-M11: Exact Duplicates vs Near Duplicates
# ===========================================================================

def test_g3_m11_exact_duplicates_marked_ambiguous_and_near_duplicates_unflagged():
    """Verify exact duplicates are marked ambiguous without merging/dropping; near duplicates stay separate."""
    context = VerifiedPatientContext(patient_id=1, tenant_id=1)

    t1 = Treatment(
        id=101, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", cost=Decimal("100.00"),
        discount=Decimal("0.00"), diagnosis="Caries", notes="Same note"
    )
    t2_exact_dup = Treatment(
        id=102, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", cost=Decimal("100.00"),
        discount=Decimal("0.00"), diagnosis="Caries", notes="Same note"
    )
    t3_near_dup = Treatment(
        id=103, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", cost=Decimal("150.00"),  # Different cost!
        discount=Decimal("0.00"), diagnosis="Caries", notes="Different note"
    )

    batch_result = map_legacy_clinical_batch(
        verified_patient=context,
        treatments=[t1, t2_exact_dup, t3_near_dup],
    )

    # Exactly 3 work item drafts exist (none were merged or dropped!)
    assert len(batch_result.work_items) == 3

    # Exact duplicates must be flagged is_ambiguous_duplicate=True
    dup_items = [w for w in batch_result.work_items if w.source_id in (101, 102)]
    assert len(dup_items) == 2
    assert all(w.is_ambiguous_duplicate for w in dup_items)

    # Near duplicate must NOT be flagged as ambiguous duplicate
    near_items = [w for w in batch_result.work_items if w.source_id == 103]
    assert len(near_items) == 1
    assert near_items[0].is_ambiguous_duplicate is False

    # Ambiguities list must contain exact duplicate issues
    dup_issues = [a for a in batch_result.ambiguities if a.code == "EXACT_DUPLICATE_RECORD"]
    assert len(dup_issues) >= 2


# ===========================================================================
# G3-M12: Idempotency and Stable Versioned Keys
# ===========================================================================

def test_g3_m12_idempotency_and_stable_key_determinism():
    """Verify repeated mapping calls yield identical results and stable versioned SHA-256 keys."""
    context = VerifiedPatientContext(patient_id=1, tenant_id=1)
    t = Treatment(
        id=200, patient_id=1, tenant_id=1, tooth_number=11,
        procedure="Root Canal", status="Done", cost=Decimal("500.00"),
    )

    res1 = map_legacy_clinical_batch(context, treatments=[t])
    res2 = map_legacy_clinical_batch(context, treatments=[t])

    # Work item drafts must have identical stable keys and contents
    assert len(res1.work_items) == 1
    assert res1.work_items[0].stable_key == res2.work_items[0].stable_key
    assert res1.work_items[0].code == res2.work_items[0].code

    # Distinct tenants must generate distinct stable keys (no collisions)
    key_t1 = generate_stable_mapping_key("wi", "treatment", 1, tenant_id=1, patient_id=1, identity_payload="proc=A")
    key_t2 = generate_stable_mapping_key("wi", "treatment", 1, tenant_id=2, patient_id=1, identity_payload="proc=A")
    assert key_t1 != key_t2

    # Distinct source kinds must generate distinct stable keys
    key_src_t = generate_stable_mapping_key("wi", "treatment", 1, tenant_id=1, patient_id=1, identity_payload="proc=A")
    key_src_ts = generate_stable_mapping_key("wi", "tooth_status", 1, tenant_id=1, patient_id=1, identity_payload="proc=A")
    assert key_src_t != key_src_ts


# ===========================================================================
# G3-M13: Tenant Isolation, Nullable Tenant, and Cross-Tenant Prevention
# ===========================================================================

def test_g3_m13_tenant_isolation_and_nullable_tenant_inheritance():
    """Verify nullable tenant inheritance and strict rejection of tenant/patient mismatches."""
    context = VerifiedPatientContext(patient_id=1, tenant_id=10)

    # 1. Null row tenant_id inherits verified tenant ownership
    t_null_tenant = Treatment(
        id=301, patient_id=1, tenant_id=None, tooth_number=11,
        procedure="Composite Filling", status="Done"
    )
    wi_null, ev_null, issues_null = map_legacy_treatment(t_null_tenant, context)
    assert len(issues_null) == 0
    assert wi_null is not None
    assert wi_null.tenant_id == 10
    assert ev_null.tenant_id == 10

    # 2. Tenant mismatch rejected (row tenant 99 != verified tenant 10)
    t_mismatch = Treatment(
        id=302, patient_id=1, tenant_id=99, tooth_number=11,
        procedure="Composite Filling", status="Done"
    )
    wi_mis, ev_mis, issues_mis = map_legacy_treatment(t_mismatch, context)
    assert wi_mis is None
    assert ev_mis is None
    assert any(iss.code == "TENANT_MISMATCH" for iss in issues_mis)

    # 3. Patient mismatch rejected (row patient 999 != verified patient 1)
    t_patient_mis = Treatment(
        id=303, patient_id=999, tenant_id=10, tooth_number=11,
        procedure="Composite Filling", status="Done"
    )
    wi_pmis, ev_pmis, issues_pmis = map_legacy_treatment(t_patient_mis, context)
    assert wi_pmis is None
    assert ev_pmis is None
    assert any(iss.code == "PATIENT_OWNERSHIP_MISMATCH" for iss in issues_pmis)

    # 4. ToothStatus tenant mismatch rejected
    ts_mismatch = ToothStatus(id=401, patient_id=1, tenant_id=99, tooth_number=11, condition="Healthy")
    ev_ts, issues_ts = map_legacy_tooth_status(ts_mismatch, context)
    assert ev_ts is None
    assert any(iss.code == "TENANT_MISMATCH" for iss in issues_ts)


def test_g3_m10_treatment_ownership_in_lab_link():
    """Verify direct treatment patient and tenant ownership checks in resolve_exact_lab_link (direct and batch)."""
    context = VerifiedPatientContext(patient_id=1, tenant_id=10)
    lo_valid = LabOrder(id=100, patient_id=1, tenant_id=10)

    # 1. Direct resolve_exact_lab_link rejects treatment with mismatched patient_id
    t_wrong_patient = Treatment(
        id=1, patient_id=99, tenant_id=10, tooth_number=14,
        procedure="Composite Filling", status="Done", notes="Link:LabOrder:100"
    )
    link_p, iss_p = resolve_exact_lab_link(t_wrong_patient, [lo_valid], context)
    assert link_p is None
    assert iss_p is not None
    assert iss_p.code == "PATIENT_OWNERSHIP_MISMATCH"
    assert iss_p.is_ambiguity is False

    # 2. Direct resolve_exact_lab_link rejects treatment with mismatched tenant_id
    t_wrong_tenant = Treatment(
        id=2, patient_id=1, tenant_id=99, tooth_number=14,
        procedure="Composite Filling", status="Done", notes="Link:LabOrder:100"
    )
    link_t, iss_t = resolve_exact_lab_link(t_wrong_tenant, [lo_valid], context)
    assert link_t is None
    assert iss_t is not None
    assert iss_t.code == "TENANT_MISMATCH"
    assert iss_t.is_ambiguity is False

    # 3. Direct resolve_exact_lab_link permits treatment with tenant_id=None when patient_id matches (inheriting verified tenant)
    t_null_tenant = Treatment(
        id=3, patient_id=1, tenant_id=None, tooth_number=14,
        procedure="Composite Filling", status="Done", notes="Link:LabOrder:100"
    )
    link_null, iss_null = resolve_exact_lab_link(t_null_tenant, [lo_valid], context)
    assert iss_null is None
    assert link_null is not None
    assert link_null.treatment_id == 3
    assert link_null.lab_order_id == 100
    assert link_null.tenant_id == 10

    # 4. Batch mapping regression: cross-patient and cross-tenant treatments never yield lab_links
    batch_result = map_legacy_clinical_batch(
        treatments=[t_wrong_patient, t_wrong_tenant],
        tooth_statuses=[],
        treatment_sessions=[],
        lab_orders=[lo_valid],
        verified_patient=context,
    )
    assert len(batch_result.lab_links) == 0
    assert any(iss.code == "PATIENT_OWNERSHIP_MISMATCH" for iss in batch_result.issues)
    assert any(iss.code == "TENANT_MISMATCH" for iss in batch_result.issues)


def test_g3_m11_exact_content_fingerprint_doctor_and_raw_strings():
    """Verify work item fingerprints differentiate doctor and raw strings, and duplicate events preserve payload."""
    context = VerifiedPatientContext(patient_id=1, tenant_id=1)

    # 1. Different doctor_id produces distinct work-item fingerprints and no duplicate marking
    t_doc1 = Treatment(
        id=1, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", doctor_id=10
    )
    t_doc2 = Treatment(
        id=2, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", doctor_id=20
    )
    wi1, _, _ = map_legacy_treatment(t_doc1, context)
    wi2, _, _ = map_legacy_treatment(t_doc2, context)
    assert wi1 is not None and wi2 is not None
    assert compute_work_item_canonical_fingerprint(wi1) != compute_work_item_canonical_fingerprint(wi2)
    marked_wis, _ = mark_ambiguous_duplicates([wi1, wi2], compute_work_item_canonical_fingerprint)
    assert not marked_wis[0].is_ambiguous_duplicate
    assert not marked_wis[1].is_ambiguous_duplicate

    # 2. Different raw procedure strings produce distinct fingerprints and no duplicate marking
    t_raw1 = Treatment(
        id=3, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", doctor_id=10
    )
    t_raw2 = Treatment(
        id=4, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="حشو كومبوزيت -- Composite Filling Class I", status="Done", doctor_id=10
    )
    wi_raw1, _, _ = map_legacy_treatment(t_raw1, context)
    wi_raw2, _, _ = map_legacy_treatment(t_raw2, context)
    assert wi_raw1 is not None and wi_raw2 is not None
    assert compute_work_item_canonical_fingerprint(wi_raw1) != compute_work_item_canonical_fingerprint(wi_raw2)
    marked_raws, _ = mark_ambiguous_duplicates([wi_raw1, wi_raw2], compute_work_item_canonical_fingerprint)
    assert not marked_raws[0].is_ambiguous_duplicate
    assert not marked_raws[1].is_ambiguous_duplicate

    # 3. Identical rows with different source IDs yield duplicate ambiguity for both work-item and event,
    # while draft.payload itself preserves the exact legacy_treatment_id.
    t_dup_a = Treatment(
        id=101, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", doctor_id=10, notes="Identical note"
    )
    t_dup_b = Treatment(
        id=102, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", doctor_id=10, notes="Identical note"
    )
    wi_a, ev_a, _ = map_legacy_treatment(t_dup_a, context)
    wi_b, ev_b, _ = map_legacy_treatment(t_dup_b, context)
    assert wi_a is not None and wi_b is not None
    assert ev_a is not None and ev_b is not None

    marked_wi, _ = mark_ambiguous_duplicates([wi_a, wi_b], compute_work_item_canonical_fingerprint)
    assert marked_wi[0].is_ambiguous_duplicate is True
    assert marked_wi[1].is_ambiguous_duplicate is True

    marked_ev, _ = mark_ambiguous_duplicates([ev_a, ev_b], compute_event_canonical_fingerprint)
    assert marked_ev[0].is_ambiguous_duplicate is True
    assert marked_ev[1].is_ambiguous_duplicate is True

    # Payload unchanged and retains exact legacy ID
    assert marked_ev[0].payload["legacy_treatment_id"] == 101
    assert marked_ev[1].payload["legacy_treatment_id"] == 102


def test_g3_deep_immutability_and_nested_mutation():
    """Verify deep immutability at DTO boundaries and protection against nested object mutation."""
    # 1. Test deep_freeze with nested collections
    orig_data = {
        "str": "val",
        "nested_dict": {"k": "v"},
        "nested_list": [1, [2, 3]],
        "nested_set": {"a", "b"},
    }
    frozen = deep_freeze(orig_data)
    assert isinstance(frozen, MappingProxyType)
    assert isinstance(frozen["nested_dict"], MappingProxyType)
    assert isinstance(frozen["nested_list"], tuple)
    assert isinstance(frozen["nested_list"][1], tuple)
    assert isinstance(frozen["nested_set"], frozenset)

    # 2. Test LegacyMappingIssue.details deep immutability
    raw_details = {
        "reason": "bad_code",
        "nested": {"level": 1},
        "tags": ["alpha", "beta"],
    }
    issue = LegacyMappingIssue(
        code="TEST_ISSUE",
        message="Test issue message",
        source_kind="treatment",
        source_id=1,
        details=raw_details,
    )
    # Mutating raw_details should not affect issue.details
    raw_details["nested"]["level"] = 999
    raw_details["tags"].append("gamma")
    assert issue.details["nested"]["level"] == 1
    assert issue.details["tags"] == ("alpha", "beta")

    with pytest.raises(TypeError):
        issue.details["reason"] = "mutated"  # type: ignore

    with pytest.raises(TypeError):
        issue.details["nested"]["level"] = 2  # type: ignore

    # 3. Test LegacyEventDraft.payload deep immutability
    raw_payload = {
        "action": "completed",
        "details": {"items": [{"name": "item1"}, {"name": "item2"}]},
    }
    ev = LegacyEventDraft(
        stable_key="test_event_key",
        tenant_id=1,
        patient_id=1,
        event_type="treatment_completed",
        occurred_at=None,
        actor_user_id=10,
        payload=raw_payload,
        notes="note",
        targets=(),
        source_kind="treatment",
        source_id=1,
    )
    # Modifying raw_payload dict should not mutate ev.payload
    raw_payload["action"] = "reopened"
    raw_payload["details"]["items"].append({"name": "item3"})
    assert ev.payload["action"] == "completed"
    assert len(ev.payload["details"]["items"]) == 2
    assert isinstance(ev.payload["details"]["items"], tuple)
    assert isinstance(ev.payload["details"]["items"][0], MappingProxyType)

    with pytest.raises(TypeError):
        ev.payload["action"] = "mutated"  # type: ignore

    with pytest.raises(TypeError):
        ev.payload["details"]["items"][0]["name"] = "mutated"  # type: ignore


def test_g3_m11_collision_safe_canonical_fingerprints():
    """Verify delimiter collision resistance across work items, care sessions, and lab links."""
    context = VerifiedPatientContext(patient_id=1, tenant_id=1)

    # 1. WorkItem delimiter collision: free text containing '|' or '=' must not collide with other field boundaries
    t_col1 = Treatment(
        id=1, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", notes="Tooth|sessions=2", sessions=None
    )
    t_col2 = Treatment(
        id=2, patient_id=1, tenant_id=1, tooth_number=14,
        procedure="Composite Filling", status="Done", notes="Tooth", sessions="2"
    )
    wi1, _, _ = map_legacy_treatment(t_col1, context)
    wi2, _, _ = map_legacy_treatment(t_col2, context)
    assert wi1 is not None and wi2 is not None

    fp_wi1 = compute_work_item_canonical_fingerprint(wi1)
    fp_wi2 = compute_work_item_canonical_fingerprint(wi2)
    assert fp_wi1 != fp_wi2

    marked_wis, _ = mark_ambiguous_duplicates([wi1, wi2], compute_work_item_canonical_fingerprint)
    assert not marked_wis[0].is_ambiguous_duplicate
    assert not marked_wis[1].is_ambiguous_duplicate

    # 2. CareSession delimiter collision: notes containing delimiter tokens
    cs1 = LegacyCareSessionDraft(
        stable_key="cs_k1", tenant_id=1, patient_id=1,
        parent_treatment_id=10, session_date=None, notes="Exam|parent_treatment_id=99", source_id=1
    )
    cs2 = LegacyCareSessionDraft(
        stable_key="cs_k2", tenant_id=1, patient_id=1,
        parent_treatment_id=99, session_date=None, notes="Exam", source_id=2
    )
    assert compute_care_session_canonical_fingerprint(cs1) != compute_care_session_canonical_fingerprint(cs2)

    # 3. LabLink delimiter collision: link_token containing delimiter tokens
    ll1 = LegacyLabLinkDraft(
        stable_key="ll_k1", tenant_id=1, patient_id=1,
        treatment_id=10, lab_order_id=5, link_token="Link:LabOrder:5|patient_id=99"
    )
    ll2 = LegacyLabLinkDraft(
        stable_key="ll_k2", tenant_id=1, patient_id=99,
        treatment_id=10, lab_order_id=5, link_token="Link:LabOrder:5"
    )
    assert compute_lab_link_canonical_fingerprint(ll1) != compute_lab_link_canonical_fingerprint(ll2)


def test_g3_m11_type_tagged_canonicalization():
    """Verify explicit type tags prevent collisions across Decimal, strings, ints, dates, and collections."""
    from datetime import date

    # 1. Decimal vs string vs int vs bool
    assert canonical_json_dumps(Decimal("1")) != canonical_json_dumps("1")
    assert canonical_json_dumps(Decimal("1")) != canonical_json_dumps(1)
    assert canonical_json_dumps(1) != canonical_json_dumps("1")
    assert canonical_json_dumps(True) != canonical_json_dumps(1)
    assert canonical_json_dumps(False) != canonical_json_dumps(0)

    # 2. datetime vs date vs string
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    d = date(2026, 1, 1)
    assert canonical_json_dumps(dt) != canonical_json_dumps(dt.isoformat())
    assert canonical_json_dumps(d) != canonical_json_dumps(d.isoformat())
    assert canonical_json_dumps(dt) != canonical_json_dumps(d)

    # 3. Mapping keys retain type
    assert canonical_json_dumps({1: "val"}) != canonical_json_dumps({"1": "val"})

    # 4. list vs tuple, set vs frozenset are distinguishable
    assert canonical_json_dumps([1, 2]) != canonical_json_dumps((1, 2))
    assert canonical_json_dumps({1, 2}) != canonical_json_dumps(frozenset({1, 2}))

    # 5. Unordered collection sorting
    assert canonical_json_dumps({2, 1}) == canonical_json_dumps({1, 2})
    assert canonical_json_dumps(frozenset({2, 1})) == canonical_json_dumps(frozenset({1, 2}))
    assert canonical_json_dumps({"b": 2, "a": 1}) == canonical_json_dumps({"a": 1, "b": 2})

    # 6. Unsupported types raise TypeError
    class UnsupportedCustomClass:
        pass

    with pytest.raises(TypeError, match="Unsupported type"):
        canonical_json_dumps(UnsupportedCustomClass())


def test_g3_m11_event_fingerprint_with_nested_frozen_and_types():
    """Verify compute_event_canonical_fingerprint handles nested MappingProxyType, tuples, frozensets, Decimals, datetimes."""
    payload = {
        "amounts": (Decimal("10.50"), Decimal("20.00")),
        "meta": {"created": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)},
        "tags": frozenset({"urgent", "review"}),
    }
    ev1 = LegacyEventDraft(
        stable_key="ev1",
        tenant_id=1,
        patient_id=1,
        event_type="procedure_recorded",
        occurred_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        actor_user_id=10,
        payload=payload,
        notes="sample note",
        targets=(),
        source_kind="treatment",
        source_id=101,
    )
    ev2 = LegacyEventDraft(
        stable_key="ev2",
        tenant_id=1,
        patient_id=1,
        event_type="procedure_recorded",
        occurred_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        actor_user_id=10,
        payload=payload,
        notes="sample note",
        targets=(),
        source_kind="treatment",
        source_id=102,
    )
    # Different legacy IDs in payload are filtered out; identical content produces identical fingerprints
    fp1 = compute_event_canonical_fingerprint(ev1)
    fp2 = compute_event_canonical_fingerprint(ev2)
    assert fp1 == fp2

    # Different Decimal produces distinct fingerprint
    ev3 = LegacyEventDraft(
        stable_key="ev3",
        tenant_id=1,
        patient_id=1,
        event_type="procedure_recorded",
        occurred_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        actor_user_id=10,
        payload={
            "amounts": (Decimal("10.51"), Decimal("20.00")),
            "meta": {"created": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)},
            "tags": frozenset({"urgent", "review"}),
        },
        notes="sample note",
        targets=(),
        source_kind="treatment",
        source_id=103,
    )
    assert compute_event_canonical_fingerprint(ev1) != compute_event_canonical_fingerprint(ev3)
