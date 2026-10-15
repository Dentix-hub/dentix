"""
DENTIX Clinical VNext — Deterministic Legacy Mapping Engine (Phase G3: G3-M01..M13).

Pure code-level mapper translating legacy clinical records:
- Treatment (models.Treatment) -> ClinicalWorkItem draft, ClinicalEvent draft
- ToothStatus (models.ToothStatus) -> Tooth Lifecycle / Finding / Procedure event draft
- TreatmentSession (models.TreatmentSession) -> CareSession draft
- LabOrder (models.LabOrder) -> ClinicalAttachmentLink / LabLink draft

Strict Invariants:
1. Exact immutable procedure allowlist only. No fuzzy/substring/case-fold/trim matching.
2. Exact status only: Done->completed, Pending->planned, In Progress->active.
3. Exact valid FDI from FDI_TOOTH_KEYS has priority. Then Universal 1..32 via table; Palmer via full-string grammar.
4. Treatment -> work-item and event drafts only when ownership, procedure, status, and target are deterministic.
5. ToothStatus uses small exact allowlists for justified G2 codes.
6. TreatmentSession -> care-session draft only via explicit verified parent Treatment ownership.
7. Only lab link: entire Treatment.notes exactly 'Link:LabOrder:<id>'. Resolve exactly one matching LabOrder.
8. Exact duplicates marked ambiguous; never merge/drop/delete. Near duplicates separate/unflagged.
9. Nullable tenant inheritance only from verified patient ownership. Tenant mismatch rejected.
10. Versioned stable keys via canonical serialization + hashlib SHA-256.
11. Frozen, deeply immutable DTOs preserving Decimal, datetime, and text verbatim.
12. Zero database dependencies, zero mutation of source ORM rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from backend.clinical.catalog import (
    FindingCode,
    ProcedureCode,
    ToothLifecycleCode,
    TreatmentLifecycleCode,
)
from backend.models.clinical_core import FDI_TOOTH_KEYS


def deep_freeze(val: Any) -> Any:
    """
    Recursively freeze any value into deeply immutable types:
    - Mapping / dict -> MappingProxyType wrapping a new dict where all values are deeply frozen (shallow copy before proxy)
    - set / frozenset -> frozenset of deeply frozen items (deterministic frozenset handling)
    - Sequence (list, tuple) except (str, bytes) -> tuple of deeply frozen items
    - Primitives, Decimal, datetime, date, None -> unchanged
    """
    if isinstance(val, Mapping):
        return MappingProxyType({k: deep_freeze(v) for k, v in val.items()})
    if isinstance(val, (set, frozenset)):
        return frozenset(deep_freeze(item) for item in val)
    if isinstance(val, (list, tuple)) and not isinstance(val, (str, bytes)):
        return tuple(deep_freeze(item) for item in val)
    return val


def to_canonical_tagged(obj: Any) -> Any:
    """
    Recursively convert any value into an unambiguous, type-tagged canonical representation:
    - Primitives retain explicit type tags (@t: null, bool, int, float, str, bytes).
    - Decimal is tagged @t: decimal so it never equals str or int.
    - datetime and date are tagged @t: datetime and @t: date.
    - list and tuple are distinguishable (@t: list vs @t: tuple).
    - set and frozenset are distinguishable (@t: set vs @t: frozenset) and sorted by canonical JSON representation.
    - Mapping entries retain exact key types (stored as {"k": tagged_k, "v": tagged_v}) and are sorted by canonical JSON of key.
    - Any unsupported type strictly raises TypeError (no generic fallback to str(obj)).
    """
    if obj is None:
        return {"@t": "null", "@v": None}
    if isinstance(obj, bool):
        return {"@t": "bool", "@v": obj}
    if isinstance(obj, int):
        return {"@t": "int", "@v": obj}
    if isinstance(obj, float):
        return {"@t": "float", "@v": repr(obj)}
    if isinstance(obj, Decimal):
        return {"@t": "decimal", "@v": str(obj)}
    if isinstance(obj, str):
        return {"@t": "str", "@v": obj}
    if isinstance(obj, bytes):
        return {"@t": "bytes", "@v": obj.hex()}
    if isinstance(obj, datetime):
        return {"@t": "datetime", "@v": obj.isoformat()}
    if isinstance(obj, date):
        return {"@t": "date", "@v": obj.isoformat()}
    if isinstance(obj, list):
        return {"@t": "list", "@v": [to_canonical_tagged(x) for x in obj]}
    if isinstance(obj, tuple):
        return {"@t": "tuple", "@v": [to_canonical_tagged(x) for x in obj]}
    if isinstance(obj, set):
        items = [to_canonical_tagged(x) for x in obj]
        sorted_items = sorted(
            items,
            key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        return {"@t": "set", "@v": sorted_items}
    if isinstance(obj, frozenset):
        items = [to_canonical_tagged(x) for x in obj]
        sorted_items = sorted(
            items,
            key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        return {"@t": "frozenset", "@v": sorted_items}
    if isinstance(obj, Mapping):
        entries = [
            {"k": to_canonical_tagged(k), "v": to_canonical_tagged(v)}
            for k, v in obj.items()
        ]
        sorted_entries = sorted(
            entries,
            key=lambda e: json.dumps(e["k"], sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        return {"@t": "mapping", "@v": sorted_entries}
    raise TypeError(f"Unsupported type for canonical serialization: {type(obj).__name__}")


def canonical_json_dumps(obj: Any) -> str:
    """
    Produce collision-safe, deterministic canonical JSON serialization:
    - Recursively processes values into type-tagged canonical representations.
    - Type-safe tags ensure Decimal(1) != '1' != 1, datetime/date != strings, bool != int.
    - Mapping entries and unordered collections (set, frozenset) are sorted by fully canonical serialized tagged form.
    - Uses minimal separators (',', ':') without whitespace and ensure_ascii=False.
    - Raises TypeError for unsupported types.
    """
    tagged = to_canonical_tagged(obj)
    return json.dumps(tagged, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ===========================================================================
# G3-M01: Data Transfer Objects (DTOs), Issues, and Ownership Context
# ===========================================================================

@dataclass(frozen=True)
class VerifiedPatientContext:
    """Verified patient and tenant ownership context."""
    patient_id: int
    tenant_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.patient_id, int) or self.patient_id <= 0:
            raise ValueError(f"patient_id must be a positive integer, got {self.patient_id!r}")
        if not isinstance(self.tenant_id, int) or self.tenant_id <= 0:
            raise ValueError(f"tenant_id must be a positive integer, got {self.tenant_id!r}")


@dataclass(frozen=True)
class LegacyMappingIssue:
    """Immutable diagnostic or ambiguity record."""
    code: str
    message: str
    source_kind: str
    source_id: int | None
    is_ambiguity: bool = False
    raw_value: str | None = None
    details: MappingProxyType[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", deep_freeze(self.details))


@dataclass(frozen=True)
class LegacyWorkItemTargetDraft:
    """Target anatomical shape for a mapped work item draft."""
    tenant_id: int
    target_kind: str
    tooth_key: str
    surface_code: str | None = None
    root_id: str | None = None
    canal_id: str | None = None


@dataclass(frozen=True)
class LegacyWorkItemDraft:
    """Draft representing a mapped ClinicalWorkItem."""
    stable_key: str
    tenant_id: int
    patient_id: int
    kind: str  # 'procedure' or 'finding'
    code: str
    status: str
    notes: str | None
    created_by_user_id: int | None
    targets: tuple[LegacyWorkItemTargetDraft, ...]
    source_kind: str
    source_id: int
    raw_procedure: str | None = None
    raw_status: str | None = None
    diagnosis: str | None = None
    cost: Decimal | None = None
    discount: Decimal | None = None
    sessions: str | None = None
    complications: str | None = None
    is_ambiguous_duplicate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", tuple(self.targets))


@dataclass(frozen=True)
class LegacyEventTargetDraft:
    """Target anatomical shape for a mapped clinical event draft."""
    tenant_id: int
    target_kind: str
    tooth_key: str
    surface_code: str | None = None
    root_id: str | None = None
    canal_id: str | None = None


@dataclass(frozen=True)
class LegacyEventDraft:
    """Draft representing an append-oriented ClinicalEvent."""
    stable_key: str
    tenant_id: int
    patient_id: int
    event_type: str
    occurred_at: datetime | None
    actor_user_id: int | None
    payload: MappingProxyType[str, Any]
    notes: str | None
    targets: tuple[LegacyEventTargetDraft, ...]
    source_kind: str
    source_id: int
    is_ambiguous_duplicate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", deep_freeze(self.payload))
        object.__setattr__(self, "targets", tuple(self.targets))


@dataclass(frozen=True)
class LegacyCareSessionDraft:
    """Draft representing a mapped CareSession."""
    stable_key: str
    tenant_id: int
    patient_id: int
    parent_treatment_id: int
    session_date: datetime | None
    notes: str | None
    source_id: int
    is_ambiguous_duplicate: bool = False


@dataclass(frozen=True)
class LegacyLabLinkDraft:
    """Draft representing a verified singleton lab link."""
    stable_key: str
    tenant_id: int
    patient_id: int
    treatment_id: int
    lab_order_id: int
    link_token: str
    is_ambiguous_duplicate: bool = False


@dataclass(frozen=True)
class LegacyMappingBatchResult:
    """Complete result of mapping a set of legacy clinical records."""
    work_items: tuple[LegacyWorkItemDraft, ...]
    events: tuple[LegacyEventDraft, ...]
    care_sessions: tuple[LegacyCareSessionDraft, ...]
    lab_links: tuple[LegacyLabLinkDraft, ...]
    issues: tuple[LegacyMappingIssue, ...]
    ambiguities: tuple[LegacyMappingIssue, ...]


# ===========================================================================
# G3-M02: Exact Procedure Allowlist
# ===========================================================================

# Exact string matches only. No fuzzy/substring/case-fold/trim matching.
_RAW_PROCEDURE_ALLOWLIST: dict[str, str] = {
    # Exact canonical codes
    ProcedureCode.REST_COMPOSITE.value: ProcedureCode.REST_COMPOSITE.value,
    ProcedureCode.ENDO_RCT.value: ProcedureCode.ENDO_RCT.value,
    ProcedureCode.PROS_CROWN.value: ProcedureCode.PROS_CROWN.value,
    ProcedureCode.PROS_BRIDGE.value: ProcedureCode.PROS_BRIDGE.value,
    ProcedureCode.IMPLANT_FIXTURE.value: ProcedureCode.IMPLANT_FIXTURE.value,
    ProcedureCode.IMPLANT_CROWN.value: ProcedureCode.IMPLANT_CROWN.value,
    ProcedureCode.SURG_EXTRACTION.value: ProcedureCode.SURG_EXTRACTION.value,
    ProcedureCode.PROS_DENTURE.value: ProcedureCode.PROS_DENTURE.value,
    # Standard English exact forms
    "Composite Filling": ProcedureCode.REST_COMPOSITE.value,
    "Root Canal": ProcedureCode.ENDO_RCT.value,
    "Root Canal Treatment": ProcedureCode.ENDO_RCT.value,
    "Crown": ProcedureCode.PROS_CROWN.value,
    "Fixed Bridge": ProcedureCode.PROS_BRIDGE.value,
    "Simple Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "Surgical Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "Denture": ProcedureCode.PROS_DENTURE.value,
    # Standard Seed procedures (exact literals from seed_procedures.py)
    "حشو كومبوزيت -- Composite Filling Class I": ProcedureCode.REST_COMPOSITE.value,
    "حشو كومبوزيت -- Composite Filling Class II": ProcedureCode.REST_COMPOSITE.value,
    "حشو كومبوزيت -- Composite Filling Class III": ProcedureCode.REST_COMPOSITE.value,
    "حشو كومبوزيت -- Composite Filling Class IV": ProcedureCode.REST_COMPOSITE.value,
    "حشو كومبوزيت -- Composite Filling Class V": ProcedureCode.REST_COMPOSITE.value,
    "حشو عصب – Root Canal Treatment": ProcedureCode.ENDO_RCT.value,
    "إعادة حشو عصب – Retreatment Root Canal": ProcedureCode.ENDO_RCT.value,
    "خلع عادي – Simple Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "خلع جراحي – Surgical Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "خلع ضرس عقل – Wisdom Tooth Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "خلع ضرس عقل مطمور جزئي – Partially Impacted Wisdom Tooth Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "خلع ضرس عقل مطمور كلي – Fully Impacted Wisdom Tooth Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "خلع سن لبني – Primary Tooth Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "خلع بقايا جذور – Root Remnants Extraction": ProcedureCode.SURG_EXTRACTION.value,
    "تاج بورسلين – Porcelain Crown": ProcedureCode.PROS_CROWN.value,
    "تاج زيركون – Zirconia Crown": ProcedureCode.PROS_CROWN.value,
    "تاج -- E-max Crown": ProcedureCode.PROS_CROWN.value,
    "تاج معدن – Metal Crown": ProcedureCode.PROS_CROWN.value,
    "تاج مؤقت – Temporary Crown": ProcedureCode.PROS_CROWN.value,
    "جسر ثابت – Fixed Bridge": ProcedureCode.PROS_BRIDGE.value,
    "طقم كامل أكريليك – Complete Acrylic Denture": ProcedureCode.PROS_DENTURE.value,
    "طقم جزئي أكريليك – Partial Acrylic Denture": ProcedureCode.PROS_DENTURE.value,
    "طقم جزئي معدني – Partial Metal Denture": ProcedureCode.PROS_DENTURE.value,
    "طقم مرن – Flexible Denture": ProcedureCode.PROS_DENTURE.value,
}

LEGACY_PROCEDURE_ALLOWLIST: MappingProxyType[str, str] = MappingProxyType(_RAW_PROCEDURE_ALLOWLIST)


def map_legacy_procedure(raw_procedure: Any) -> tuple[str | None, LegacyMappingIssue | None]:
    """
    Map legacy procedure verbatim to canonical ProcedureCode.
    Exact allowlist match only. No fuzzy/substring/case-fold/trim matching.
    """
    if raw_procedure is None or not isinstance(raw_procedure, str):
        return None, LegacyMappingIssue(
            code="INVALID_PROCEDURE_TYPE",
            message=f"Procedure must be a string, got {type(raw_procedure).__name__}",
            source_kind="treatment",
            source_id=None,
            is_ambiguity=True,
            raw_value=str(raw_procedure) if raw_procedure is not None else None,
        )

    canonical = LEGACY_PROCEDURE_ALLOWLIST.get(raw_procedure)
    if canonical is None:
        return None, LegacyMappingIssue(
            code="UNKNOWN_PROCEDURE_CODE",
            message=f"Unknown legacy procedure: '{raw_procedure}'. Exact allowlist match required.",
            source_kind="treatment",
            source_id=None,
            is_ambiguity=True,
            raw_value=raw_procedure,
        )

    return canonical, None


# ===========================================================================
# G3-M03: Exact Status Allowlist
# ===========================================================================

# Exact status only: Done->completed, Pending->planned, In Progress->active.
_RAW_STATUS_ALLOWLIST: dict[str, str] = {
    "Done": TreatmentLifecycleCode.COMPLETED.value,
    "Pending": TreatmentLifecycleCode.PLANNED.value,
    "In Progress": TreatmentLifecycleCode.ACTIVE.value,
}

LEGACY_STATUS_ALLOWLIST: MappingProxyType[str, str] = MappingProxyType(_RAW_STATUS_ALLOWLIST)


def map_legacy_status(raw_status: Any) -> tuple[str | None, LegacyMappingIssue | None]:
    """
    Map legacy status verbatim to canonical TreatmentLifecycleCode.
    Exact match only: Done->completed, Pending->planned, In Progress->active.
    """
    if raw_status is None or not isinstance(raw_status, str):
        return None, LegacyMappingIssue(
            code="INVALID_STATUS_TYPE",
            message=f"Status must be a string, got {type(raw_status).__name__}",
            source_kind="treatment",
            source_id=None,
            is_ambiguity=True,
            raw_value=str(raw_status) if raw_status is not None else None,
        )

    canonical = LEGACY_STATUS_ALLOWLIST.get(raw_status)
    if canonical is None:
        return None, LegacyMappingIssue(
            code="UNKNOWN_STATUS_CODE",
            message=f"Unknown legacy status: '{raw_status}'. Exact allowlist match required.",
            source_kind="treatment",
            source_id=None,
            is_ambiguity=True,
            raw_value=raw_status,
        )

    return canonical, None


# ===========================================================================
# G3-M04: Tooth Notation Mapping (FDI priority -> Universal 1..32 -> Palmer grammar)
# ===========================================================================

# Universal Numbering System 1..32 -> FDI Key (exact standard table)
_UNIVERSAL_TO_FDI: dict[int, str] = {
    1: "18", 2: "17", 3: "16", 4: "15", 5: "14", 6: "13", 7: "12", 8: "11",
    9: "21", 10: "22", 11: "23", 12: "24", 13: "25", 14: "26", 15: "27", 16: "28",
    17: "38", 18: "37", 19: "36", 20: "35", 21: "34", 22: "33", 23: "32", 24: "31",
    25: "41", 26: "42", 27: "43", 28: "44", 29: "45", 30: "46", 31: "47", 32: "48",
}
UNIVERSAL_TO_FDI_TABLE: MappingProxyType[int, str] = MappingProxyType(_UNIVERSAL_TO_FDI)

# Palmer quadrant + position grammar: strictly full-string matching
# Quadrants: UR (quad 1/5), UL (quad 2/6), LL (quad 3/7), LR (quad 4/8)
# Positions: 1..8 (permanent) or A..E (primary)
_PALMER_REGEX = re.compile(r"^(UR|UL|LL|LR)\s?([1-8]|[A-E])$")

_PALMER_PERMANENT_BASE: dict[str, int] = {
    "UR": 10,
    "UL": 20,
    "LL": 30,
    "LR": 40,
}

_PALMER_PRIMARY_MAP: dict[str, dict[str, str]] = {
    "UR": {"A": "51", "B": "52", "C": "53", "D": "54", "E": "55"},
    "UL": {"A": "61", "B": "62", "C": "63", "D": "64", "E": "65"},
    "LL": {"A": "71", "B": "72", "C": "73", "D": "74", "E": "75"},
    "LR": {"A": "81", "B": "82", "C": "83", "D": "84", "E": "85"},
}


def map_legacy_tooth_notation(raw_tooth: Any) -> tuple[str | None, LegacyMappingIssue | None]:
    """
    Deterministically map a legacy tooth identifier to a canonical 2-digit FDI tooth key.
    Precedence:
      1. Exact valid FDI from FDI_TOOTH_KEYS has priority.
      2. Then Universal 1..32 via explicit standard table.
      3. Palmer notation via explicit full-string quadrant+position grammar/table.
    Preserves raw representation verbatim; invalid inputs produce an ambiguity issue.
    Never infers surfaces, roots, or canals.
    """
    if raw_tooth is None:
        return None, LegacyMappingIssue(
            code="MISSING_TOOTH_TARGET",
            message="Tooth number is None; cannot deterministically resolve anatomical target.",
            source_kind="treatment",
            source_id=None,
            is_ambiguity=True,
            raw_value=None,
        )

    raw_str = str(raw_tooth)

    # 1. Exact valid FDI from FDI_TOOTH_KEYS has priority
    if raw_str in FDI_TOOTH_KEYS:
        return raw_str, None

    # If raw_tooth is int or digit string: check if it matches Universal 1..32
    if isinstance(raw_tooth, int) and 1 <= raw_tooth <= 32:
        return _UNIVERSAL_TO_FDI[raw_tooth], None

    if raw_str.isdigit():
        val = int(raw_str)
        if 1 <= val <= 32:
            return _UNIVERSAL_TO_FDI[val], None

    # 2. Palmer full-string quadrant+position grammar
    match = _PALMER_REGEX.match(raw_str)
    if match:
        quad, pos = match.groups()
        if pos in "12345678":
            fdi_key = str(_PALMER_PERMANENT_BASE[quad] + int(pos))
            if fdi_key in FDI_TOOTH_KEYS:
                return fdi_key, None
        elif pos in _PALMER_PRIMARY_MAP.get(quad, {}):
            return _PALMER_PRIMARY_MAP[quad][pos], None

    return None, LegacyMappingIssue(
        code="INVALID_TOOTH_NOTATION",
        message=f"Cannot resolve tooth notation: '{raw_str}'. Not a valid FDI key, Universal 1..32, or Palmer grammar.",
        source_kind="treatment",
        source_id=None,
        is_ambiguity=True,
        raw_value=raw_str,
    )


# ===========================================================================
# G3-M07: ToothStatus Condition Allowlist
# ===========================================================================

# ToothStatus uses small exact allowlists for justified G2 codes.
_TOOTH_STATUS_LIFECYCLE_MAP: dict[str, str] = {
    "PRESENT": ToothLifecycleCode.PRESENT.value,
    "Healthy": ToothLifecycleCode.PRESENT.value,
    "MISSING": ToothLifecycleCode.MISSING.value,
    "Missing": ToothLifecycleCode.MISSING.value,
    "EXTRACTED": ToothLifecycleCode.EXTRACTED.value,
    "Extracted": ToothLifecycleCode.EXTRACTED.value,
    "IMPACTED": ToothLifecycleCode.IMPACTED.value,
    "Impacted": ToothLifecycleCode.IMPACTED.value,
    "UNERUPTED": ToothLifecycleCode.UNERUPTED.value,
    "Unerupted": ToothLifecycleCode.UNERUPTED.value,
}

_TOOTH_STATUS_FINDING_MAP: dict[str, str] = {
    "CARIES": FindingCode.CARIES.value,
    "Caries": FindingCode.CARIES.value,
    "Decayed": FindingCode.CARIES.value,
    "FRACTURE": FindingCode.FRACTURE.value,
    "Fracture": FindingCode.FRACTURE.value,
    "PAIN": FindingCode.PAIN.value,
    "Pain": FindingCode.PAIN.value,
}

_TOOTH_STATUS_PROCEDURE_MAP: dict[str, str] = {
    "REST_COMPOSITE": ProcedureCode.REST_COMPOSITE.value,
    "Filled": ProcedureCode.REST_COMPOSITE.value,
    "Composite": ProcedureCode.REST_COMPOSITE.value,
    "ENDO_RCT": ProcedureCode.ENDO_RCT.value,
    "RootCanal": ProcedureCode.ENDO_RCT.value,
    "PROS_CROWN": ProcedureCode.PROS_CROWN.value,
    "Crown": ProcedureCode.PROS_CROWN.value,
    "SURG_EXTRACTION": ProcedureCode.SURG_EXTRACTION.value,
}

TOOTH_STATUS_LIFECYCLE_ALLOWLIST: MappingProxyType[str, str] = MappingProxyType(_TOOTH_STATUS_LIFECYCLE_MAP)
TOOTH_STATUS_FINDING_ALLOWLIST: MappingProxyType[str, str] = MappingProxyType(_TOOTH_STATUS_FINDING_MAP)
TOOTH_STATUS_PROCEDURE_ALLOWLIST: MappingProxyType[str, str] = MappingProxyType(_TOOTH_STATUS_PROCEDURE_MAP)


@dataclass(frozen=True)
class ToothStatusMappingClassification:
    """Classification outcome of mapping ToothStatus.condition."""
    kind: str  # 'lifecycle', 'finding', or 'procedure'
    canonical_code: str
    event_type: str


def map_legacy_tooth_status_condition(
    raw_condition: Any,
) -> tuple[ToothStatusMappingClassification | None, LegacyMappingIssue | None]:
    """
    Map legacy ToothStatus.condition verbatim to a canonical G2 lifecycle, finding, or procedure code.
    Small exact allowlist only. Unknown condition produces an ambiguity.
    """
    if raw_condition is None or not isinstance(raw_condition, str):
        return None, LegacyMappingIssue(
            code="INVALID_TOOTH_STATUS_CONDITION_TYPE",
            message=f"Condition must be a string, got {type(raw_condition).__name__}",
            source_kind="tooth_status",
            source_id=None,
            is_ambiguity=True,
            raw_value=str(raw_condition) if raw_condition is not None else None,
        )

    if raw_condition in _TOOTH_STATUS_LIFECYCLE_MAP:
        code = _TOOTH_STATUS_LIFECYCLE_MAP[raw_condition]
        return ToothStatusMappingClassification(
            kind="lifecycle",
            canonical_code=code,
            event_type="tooth_lifecycle_changed",
        ), None

    if raw_condition in _TOOTH_STATUS_FINDING_MAP:
        code = _TOOTH_STATUS_FINDING_MAP[raw_condition]
        return ToothStatusMappingClassification(
            kind="finding",
            canonical_code=code,
            event_type="finding_recorded",
        ), None

    if raw_condition in _TOOTH_STATUS_PROCEDURE_MAP:
        code = _TOOTH_STATUS_PROCEDURE_MAP[raw_condition]
        return ToothStatusMappingClassification(
            kind="procedure",
            canonical_code=code,
            event_type="procedure_recorded",
        ), None

    return None, LegacyMappingIssue(
        code="UNKNOWN_TOOTH_STATUS_CONDITION",
        message=f"Unknown legacy tooth status condition: '{raw_condition}'. Exact allowlist match required.",
        source_kind="tooth_status",
        source_id=None,
        is_ambiguity=True,
        raw_value=raw_condition,
    )


# ===========================================================================
# G3-M10: Exact Singleton Lab Link Pattern
# ===========================================================================

# Only lab link: entire Treatment.notes exactly 'Link:LabOrder:<id>', positive ASCII decimal.
_LAB_LINK_EXACT_REGEX = re.compile(r"^Link:LabOrder:([1-9][0-9]*)$")


def parse_exact_lab_link_token(raw_notes: str | None) -> tuple[int | None, LegacyMappingIssue | None]:
    """
    Extract exact singleton LabOrder ID from Treatment.notes.
    Strictly: ^Link:LabOrder:([1-9][0-9]*)$ with positive ASCII decimal.
    No whitespace, prefixes, suffixes, or free text allowed.
    """
    if raw_notes is None:
        return None, None

    # Check if notes contain any lab link prefix at all
    if "Link:LabOrder:" not in raw_notes:
        return None, None

    match = _LAB_LINK_EXACT_REGEX.match(raw_notes)
    if not match:
        return None, LegacyMappingIssue(
            code="MALFORMED_LAB_LINK_NOTE",
            message=f"Treatment notes contain malformed lab link token: '{raw_notes}'. Must match exact format 'Link:LabOrder:<id>' with positive ASCII integer.",
            source_kind="treatment",
            source_id=None,
            is_ambiguity=True,
            raw_value=raw_notes,
        )

    return int(match.group(1)), None


# ===========================================================================
# G3-M10: Stable Versioned Key Generation (Cross-Process Hashlib SHA-256)
# ===========================================================================

def generate_stable_mapping_key(
    draft_kind: str,
    source_kind: str,
    source_id: int,
    tenant_id: int,
    patient_id: int,
    identity_payload: str,
    version: int = 1,
) -> str:
    """
    Generate stable, deterministic cross-process key via versioned canonical serialization and SHA-256.
    Ensures distinct tenants and source kinds cannot collide.
    """
    canonical_tokens = [
        f"v={version}",
        f"draft_kind={draft_kind}",
        f"source_kind={source_kind}",
        f"source_id={source_id}",
        f"tenant_id={tenant_id}",
        f"patient_id={patient_id}",
        f"identity={identity_payload}",
    ]
    canonical_string = "|".join(canonical_tokens)
    digest = hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()
    return f"k_v{version}_{digest[:32]}"


# ===========================================================================
# Core Mapping Functions: Treatment, ToothStatus, TreatmentSession, LabLink
# ===========================================================================

def map_legacy_treatment(
    treatment: Any,
    verified_patient: VerifiedPatientContext,
) -> tuple[LegacyWorkItemDraft | None, LegacyEventDraft | None, tuple[LegacyMappingIssue, ...]]:
    """
    Map a legacy Treatment ORM row to LegacyWorkItemDraft and LegacyEventDraft.
    Adheres strictly to Rules 1, 2, 3, 4, 8, 9, 10, 11.
    Never mutates the source treatment row.
    """
    issues: list[LegacyMappingIssue] = []

    t_id = getattr(treatment, "id", None)
    t_patient_id = getattr(treatment, "patient_id", None)
    t_tenant_id = getattr(treatment, "tenant_id", None)
    t_procedure = getattr(treatment, "procedure", None)
    t_status = getattr(treatment, "status", None)
    t_tooth_number = getattr(treatment, "tooth_number", None)
    t_diagnosis = getattr(treatment, "diagnosis", None)
    t_cost = getattr(treatment, "cost", None)
    t_discount = getattr(treatment, "discount", None)
    t_sessions = getattr(treatment, "sessions", None)
    t_complications = getattr(treatment, "complications", None)
    t_notes = getattr(treatment, "notes", None)
    t_date = getattr(treatment, "date", None)
    t_doctor_id = getattr(treatment, "doctor_id", None)

    # 1. Ownership & Tenant Isolation (Rule 9)
    if t_patient_id != verified_patient.patient_id:
        issues.append(
            LegacyMappingIssue(
                code="PATIENT_OWNERSHIP_MISMATCH",
                message=f"Treatment patient_id ({t_patient_id}) does not match verified patient ({verified_patient.patient_id}).",
                source_kind="treatment",
                source_id=t_id,
                is_ambiguity=False,
                raw_value=str(t_patient_id),
            )
        )
        return None, None, tuple(issues)

    effective_tenant_id: int
    if t_tenant_id is not None:
        if t_tenant_id != verified_patient.tenant_id:
            issues.append(
                LegacyMappingIssue(
                    code="TENANT_MISMATCH",
                    message=f"Treatment tenant_id ({t_tenant_id}) does not match verified tenant ({verified_patient.tenant_id}). Cross-tenant resolution rejected.",
                    source_kind="treatment",
                    source_id=t_id,
                    is_ambiguity=False,
                    raw_value=str(t_tenant_id),
                )
            )
            return None, None, tuple(issues)
        effective_tenant_id = t_tenant_id
    else:
        # Null row tenant inherits explicit verified patient ownership only
        effective_tenant_id = verified_patient.tenant_id

    # 2. Procedure Mapping (Rule 1)
    canonical_procedure, proc_issue = map_legacy_procedure(t_procedure)
    if proc_issue:
        issues.append(
            LegacyMappingIssue(
                code=proc_issue.code,
                message=proc_issue.message,
                source_kind="treatment",
                source_id=t_id,
                is_ambiguity=proc_issue.is_ambiguity,
                raw_value=proc_issue.raw_value,
            )
        )

    # 3. Status Mapping (Rule 2)
    canonical_status, status_issue = map_legacy_status(t_status)
    if status_issue:
        issues.append(
            LegacyMappingIssue(
                code=status_issue.code,
                message=status_issue.message,
                source_kind="treatment",
                source_id=t_id,
                is_ambiguity=status_issue.is_ambiguity,
                raw_value=status_issue.raw_value,
            )
        )

    # 4. Target Mapping (Rule 3)
    canonical_tooth_key, tooth_issue = map_legacy_tooth_notation(t_tooth_number)
    if tooth_issue:
        issues.append(
            LegacyMappingIssue(
                code=tooth_issue.code,
                message=tooth_issue.message,
                source_kind="treatment",
                source_id=t_id,
                is_ambiguity=tooth_issue.is_ambiguity,
                raw_value=tooth_issue.raw_value,
            )
        )

    # Treatment -> work-item and event drafts only when ownership, procedure, status, and target are deterministic
    if (
        canonical_procedure is None
        or canonical_status is None
        or canonical_tooth_key is None
    ):
        return None, None, tuple(issues)

    # Convert cost / discount to Decimal if present, preserving without lossy float conversion
    cost_dec: Decimal | None = None
    if t_cost is not None:
        cost_dec = Decimal(str(t_cost))
    discount_dec: Decimal | None = None
    if t_discount is not None:
        discount_dec = Decimal(str(t_discount))

    # Construct stable versioned key
    work_item_identity = f"proc={canonical_procedure}:tooth={canonical_tooth_key}"
    work_item_key = generate_stable_mapping_key(
        draft_kind="clinical_work_item",
        source_kind="treatment",
        source_id=t_id if t_id is not None else 0,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        identity_payload=work_item_identity,
    )

    event_identity = f"proc={canonical_procedure}:tooth={canonical_tooth_key}:status={canonical_status}"
    event_key = generate_stable_mapping_key(
        draft_kind="clinical_event",
        source_kind="treatment",
        source_id=t_id if t_id is not None else 0,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        identity_payload=event_identity,
    )

    wi_target = LegacyWorkItemTargetDraft(
        tenant_id=effective_tenant_id,
        target_kind="tooth",
        tooth_key=canonical_tooth_key,
        surface_code=None,
        root_id=None,
        canal_id=None,
    )

    ev_target = LegacyEventTargetDraft(
        tenant_id=effective_tenant_id,
        target_kind="tooth",
        tooth_key=canonical_tooth_key,
        surface_code=None,
        root_id=None,
        canal_id=None,
    )

    # Verbatim notes and free-text preservation (Rule 4, 9)
    work_item_draft = LegacyWorkItemDraft(
        stable_key=work_item_key,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        kind="procedure",
        code=canonical_procedure,
        status=canonical_status,
        notes=t_notes,
        created_by_user_id=t_doctor_id,
        targets=(wi_target,),
        source_kind="treatment",
        source_id=t_id if t_id is not None else 0,
        raw_procedure=t_procedure,
        raw_status=t_status,
        diagnosis=t_diagnosis,
        cost=cost_dec,
        discount=discount_dec,
        sessions=t_sessions,
        complications=t_complications,
    )

    # Event payload (frozen mapping, preserving raw and canonical properties)
    event_payload_dict: dict[str, Any] = {
        "legacy_treatment_id": t_id,
        "procedure": canonical_procedure,
        "status": canonical_status,
        "raw_procedure": t_procedure,
        "raw_status": t_status,
        "diagnosis": t_diagnosis,
        "cost": str(cost_dec) if cost_dec is not None else None,
        "discount": str(discount_dec) if discount_dec is not None else None,
        "sessions": t_sessions,
        "complications": t_complications,
    }
    event_payload = MappingProxyType(event_payload_dict)

    event_draft = LegacyEventDraft(
        stable_key=event_key,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        event_type="procedure_recorded",
        occurred_at=t_date,
        actor_user_id=t_doctor_id,
        payload=event_payload,
        notes=t_notes,
        targets=(ev_target,),
        source_kind="treatment",
        source_id=t_id if t_id is not None else 0,
    )

    return work_item_draft, event_draft, tuple(issues)


def map_legacy_tooth_status(
    tooth_status: Any,
    verified_patient: VerifiedPatientContext,
) -> tuple[LegacyEventDraft | None, tuple[LegacyMappingIssue, ...]]:
    """
    Map a legacy ToothStatus ORM row to a canonical ClinicalEvent draft.
    Adheres strictly to Rules 3, 5, 8, 9, 10, 11.
    Never mutates the source tooth_status row.
    """
    issues: list[LegacyMappingIssue] = []

    ts_id = getattr(tooth_status, "id", None)
    ts_patient_id = getattr(tooth_status, "patient_id", None)
    ts_tenant_id = getattr(tooth_status, "tenant_id", None)
    ts_tooth_number = getattr(tooth_status, "tooth_number", None)
    ts_condition = getattr(tooth_status, "condition", None)
    ts_notes = getattr(tooth_status, "notes", None)

    # 1. Ownership & Tenant Isolation (Rule 9)
    if ts_patient_id != verified_patient.patient_id:
        issues.append(
            LegacyMappingIssue(
                code="PATIENT_OWNERSHIP_MISMATCH",
                message=f"ToothStatus patient_id ({ts_patient_id}) does not match verified patient ({verified_patient.patient_id}).",
                source_kind="tooth_status",
                source_id=ts_id,
                is_ambiguity=False,
                raw_value=str(ts_patient_id),
            )
        )
        return None, tuple(issues)

    if ts_tenant_id is not None and ts_tenant_id != verified_patient.tenant_id:
        issues.append(
            LegacyMappingIssue(
                code="TENANT_MISMATCH",
                message=f"ToothStatus tenant_id ({ts_tenant_id}) does not match verified tenant ({verified_patient.tenant_id}). Cross-tenant resolution rejected.",
                source_kind="tooth_status",
                source_id=ts_id,
                is_ambiguity=False,
                raw_value=str(ts_tenant_id),
            )
        )
        return None, tuple(issues)

    effective_tenant_id = verified_patient.tenant_id if ts_tenant_id is None else ts_tenant_id

    # 2. Target mapping (Rule 3)
    canonical_tooth_key, tooth_issue = map_legacy_tooth_notation(ts_tooth_number)
    if tooth_issue:
        issues.append(
            LegacyMappingIssue(
                code=tooth_issue.code,
                message=tooth_issue.message,
                source_kind="tooth_status",
                source_id=ts_id,
                is_ambiguity=tooth_issue.is_ambiguity,
                raw_value=tooth_issue.raw_value,
            )
        )

    # 3. Condition mapping (Rule 5)
    classification, cond_issue = map_legacy_tooth_status_condition(ts_condition)
    if cond_issue:
        issues.append(
            LegacyMappingIssue(
                code=cond_issue.code,
                message=cond_issue.message,
                source_kind="tooth_status",
                source_id=ts_id,
                is_ambiguity=cond_issue.is_ambiguity,
                raw_value=cond_issue.raw_value,
            )
        )

    if canonical_tooth_key is None or classification is None:
        return None, tuple(issues)

    # Stable versioned key
    event_identity = f"kind={classification.kind}:code={classification.canonical_code}:tooth={canonical_tooth_key}"
    event_key = generate_stable_mapping_key(
        draft_kind="clinical_event",
        source_kind="tooth_status",
        source_id=ts_id if ts_id is not None else 0,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        identity_payload=event_identity,
    )

    ev_target = LegacyEventTargetDraft(
        tenant_id=effective_tenant_id,
        target_kind="tooth",
        tooth_key=canonical_tooth_key,
        surface_code=None,
        root_id=None,
        canal_id=None,
    )

    event_payload = MappingProxyType({
        "legacy_tooth_status_id": ts_id,
        "kind": classification.kind,
        "canonical_code": classification.canonical_code,
        "raw_condition": ts_condition,
        "tooth_key": canonical_tooth_key,
    })

    event_draft = LegacyEventDraft(
        stable_key=event_key,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        event_type=classification.event_type,
        occurred_at=None,
        actor_user_id=None,
        payload=event_payload,
        notes=ts_notes,
        targets=(ev_target,),
        source_kind="tooth_status",
        source_id=ts_id if ts_id is not None else 0,
    )

    return event_draft, tuple(issues)


def map_legacy_treatment_session(
    session: Any,
    verified_patient: VerifiedPatientContext,
    parent_treatment: Any | None,
) -> tuple[LegacyCareSessionDraft | None, tuple[LegacyMappingIssue, ...]]:
    """
    Map a legacy TreatmentSession ORM row to a CareSession draft.
    Requires explicit verified parent Treatment ownership (Rule 6, 9).
    Never parses steps/observations; notes are preserved verbatim.
    """
    issues: list[LegacyMappingIssue] = []

    s_id = getattr(session, "id", None)
    s_treatment_id = getattr(session, "treatment_id", None)
    s_tenant_id = getattr(session, "tenant_id", None)
    s_notes = getattr(session, "notes", None)
    s_date = getattr(session, "session_date", None)

    if parent_treatment is None:
        issues.append(
            LegacyMappingIssue(
                code="MISSING_PARENT_TREATMENT",
                message=f"TreatmentSession {s_id} references treatment_id {s_treatment_id} which was not supplied or not found.",
                source_kind="treatment_session",
                source_id=s_id,
                is_ambiguity=False,
                raw_value=str(s_treatment_id),
            )
        )
        return None, tuple(issues)

    p_id = getattr(parent_treatment, "id", None)
    p_patient_id = getattr(parent_treatment, "patient_id", None)
    p_tenant_id = getattr(parent_treatment, "tenant_id", None)

    if s_treatment_id != p_id:
        issues.append(
            LegacyMappingIssue(
                code="PARENT_TREATMENT_ID_MISMATCH",
                message=f"TreatmentSession treatment_id ({s_treatment_id}) does not match supplied parent treatment id ({p_id}).",
                source_kind="treatment_session",
                source_id=s_id,
                is_ambiguity=False,
                raw_value=str(s_treatment_id),
            )
        )
        return None, tuple(issues)

    if p_patient_id != verified_patient.patient_id:
        issues.append(
            LegacyMappingIssue(
                code="PATIENT_OWNERSHIP_MISMATCH",
                message=f"Parent treatment patient_id ({p_patient_id}) does not match verified patient ({verified_patient.patient_id}).",
                source_kind="treatment_session",
                source_id=s_id,
                is_ambiguity=False,
                raw_value=str(p_patient_id),
            )
        )
        return None, tuple(issues)

    # Effective tenant verification
    if p_tenant_id is not None and p_tenant_id != verified_patient.tenant_id:
        issues.append(
            LegacyMappingIssue(
                code="TENANT_MISMATCH",
                message=f"Parent treatment tenant_id ({p_tenant_id}) does not match verified tenant ({verified_patient.tenant_id}).",
                source_kind="treatment_session",
                source_id=s_id,
                is_ambiguity=False,
                raw_value=str(p_tenant_id),
            )
        )
        return None, tuple(issues)

    if s_tenant_id is not None and s_tenant_id != verified_patient.tenant_id:
        issues.append(
            LegacyMappingIssue(
                code="TENANT_MISMATCH",
                message=f"TreatmentSession tenant_id ({s_tenant_id}) does not match verified tenant ({verified_patient.tenant_id}).",
                source_kind="treatment_session",
                source_id=s_id,
                is_ambiguity=False,
                raw_value=str(s_tenant_id),
            )
        )
        return None, tuple(issues)

    effective_tenant_id = verified_patient.tenant_id

    # Stable versioned key
    care_session_identity = f"parent={p_id}:date={s_date.isoformat() if s_date else 'none'}"
    care_session_key = generate_stable_mapping_key(
        draft_kind="care_session",
        source_kind="treatment_session",
        source_id=s_id if s_id is not None else 0,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        identity_payload=care_session_identity,
    )

    care_session_draft = LegacyCareSessionDraft(
        stable_key=care_session_key,
        tenant_id=effective_tenant_id,
        patient_id=verified_patient.patient_id,
        parent_treatment_id=p_id,
        session_date=s_date,
        notes=s_notes,
        source_id=s_id if s_id is not None else 0,
    )

    return care_session_draft, tuple(issues)


def resolve_exact_lab_link(
    treatment: Any,
    supplied_lab_orders: Sequence[Any],
    verified_patient: VerifiedPatientContext,
) -> tuple[LegacyLabLinkDraft | None, LegacyMappingIssue | None]:
    """
    Resolve exact singleton lab link between a Treatment and supplied LabOrders.
    Adheres strictly to Rule 7 & 9:
    - Direct treatment patient and tenant ownership verification.
    - Nullable treatment tenant inherits verified patient ownership only when patient matches.
    - Entire Treatment.notes must be exactly 'Link:LabOrder:<id>', positive ASCII decimal.
    - Resolves exactly one supplied LabOrder with matching id, verified tenant, and verified patient.
    - Missing/multiple/malformed/cross-tenant/cross-patient => issue, no link draft.
    - Never uses tooth/date/laboratory_id/work_type.
    """
    t_id = getattr(treatment, "id", None)
    t_patient_id = getattr(treatment, "patient_id", None)
    t_tenant_id = getattr(treatment, "tenant_id", None)
    t_notes = getattr(treatment, "notes", None)

    # 1. Direct Treatment ownership & tenant verification
    if t_patient_id != verified_patient.patient_id:
        return None, LegacyMappingIssue(
            code="PATIENT_OWNERSHIP_MISMATCH",
            message=f"Treatment patient_id ({t_patient_id}) does not match verified patient ({verified_patient.patient_id}).",
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=False,
            raw_value=str(t_patient_id),
        )

    if t_tenant_id is not None and t_tenant_id != verified_patient.tenant_id:
        return None, LegacyMappingIssue(
            code="TENANT_MISMATCH",
            message=f"Treatment tenant_id ({t_tenant_id}) does not match verified tenant ({verified_patient.tenant_id}). Cross-tenant resolution rejected.",
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=False,
            raw_value=str(t_tenant_id),
        )

    lab_order_id, issue = parse_exact_lab_link_token(t_notes)
    if issue:
        return None, LegacyMappingIssue(
            code=issue.code,
            message=issue.message,
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=issue.is_ambiguity,
            raw_value=issue.raw_value,
        )

    if lab_order_id is None:
        return None, None

    # Filter supplied lab orders with matching ID
    matching_orders = [lo for lo in supplied_lab_orders if getattr(lo, "id", None) == lab_order_id]

    if not matching_orders:
        return None, LegacyMappingIssue(
            code="LAB_ORDER_NOT_FOUND",
            message=f"Treatment {t_id} references LabOrder {lab_order_id}, but no supplied LabOrder matches that ID.",
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=True,
            raw_value=str(lab_order_id),
        )

    if len(matching_orders) > 1:
        return None, LegacyMappingIssue(
            code="AMBIGUOUS_MULTIPLE_LAB_ORDERS",
            message=f"Treatment {t_id} references LabOrder {lab_order_id}, but multiple ({len(matching_orders)}) matching orders were supplied.",
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=True,
            raw_value=str(lab_order_id),
        )

    matched_order = matching_orders[0]
    lo_tenant = getattr(matched_order, "tenant_id", None)
    lo_patient = getattr(matched_order, "patient_id", None)

    # Verify tenant ownership
    if lo_tenant is not None and lo_tenant != verified_patient.tenant_id:
        return None, LegacyMappingIssue(
            code="CROSS_TENANT_LAB_LINK_REJECTED",
            message=f"Treatment {t_id} (tenant {verified_patient.tenant_id}) attempted to link LabOrder {lab_order_id} belonging to tenant {lo_tenant}.",
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=False,
            raw_value=str(lo_tenant),
        )

    # Verify patient ownership
    if lo_patient != verified_patient.patient_id:
        return None, LegacyMappingIssue(
            code="CROSS_PATIENT_LAB_LINK_REJECTED",
            message=f"Treatment {t_id} (patient {verified_patient.patient_id}) attempted to link LabOrder {lab_order_id} belonging to patient {lo_patient}.",
            source_kind="treatment",
            source_id=t_id,
            is_ambiguity=False,
            raw_value=str(lo_patient),
        )

    link_token = f"Link:LabOrder:{lab_order_id}"
    stable_key = generate_stable_mapping_key(
        draft_kind="clinical_lab_link",
        source_kind="treatment",
        source_id=t_id if t_id is not None else 0,
        tenant_id=verified_patient.tenant_id,
        patient_id=verified_patient.patient_id,
        identity_payload=f"lab_order_id={lab_order_id}",
    )

    lab_link_draft = LegacyLabLinkDraft(
        stable_key=stable_key,
        tenant_id=verified_patient.tenant_id,
        patient_id=verified_patient.patient_id,
        treatment_id=t_id if t_id is not None else 0,
        lab_order_id=lab_order_id,
        link_token=link_token,
    )

    return lab_link_draft, None


# ===========================================================================
# G3-M11: Exact Canonical Fingerprint & Duplicate Detection
# ===========================================================================

def compute_work_item_canonical_fingerprint(draft: LegacyWorkItemDraft) -> str:
    """
    Compute exact canonical fingerprint for a WorkItem draft.
    All meaningful mapped content must be identical for an exact duplicate,
    including created_by_user_id, raw_procedure, and raw_status,
    while excluding source identity (source_id, source_kind, stable_key, is_ambiguous_duplicate).
    Uses collision-safe canonical JSON serialization with explicit type tags.
    """
    targets_data = tuple(
        {
            "canal_id": t.canal_id,
            "root_id": t.root_id,
            "surface_code": t.surface_code,
            "target_kind": t.target_kind,
            "tenant_id": t.tenant_id,
            "tooth_key": t.tooth_key,
        }
        for t in draft.targets
    )
    data = {
        "code": draft.code,
        "complications": draft.complications,
        "cost": draft.cost,
        "created_by_user_id": draft.created_by_user_id,
        "diagnosis": draft.diagnosis,
        "discount": draft.discount,
        "kind": draft.kind,
        "notes": draft.notes,
        "patient_id": draft.patient_id,
        "raw_procedure": draft.raw_procedure,
        "raw_status": draft.raw_status,
        "sessions": draft.sessions,
        "status": draft.status,
        "targets": targets_data,
        "tenant_id": draft.tenant_id,
    }
    return canonical_json_dumps(data)


def compute_event_canonical_fingerprint(draft: LegacyEventDraft) -> str:
    """
    Compute exact canonical fingerprint for an Event draft.
    Ignores embedded legacy source-id payload keys when comparing content
    so identical rows with different source IDs are detected as duplicates,
    while preserving draft.payload itself unchanged.
    Uses collision-safe canonical JSON serialization supporting nested
    MappingProxyType, tuples, frozensets, Decimals, and datetimes.
    """
    filtered_payload = {
        k: v for k, v in draft.payload.items()
        if k not in ("legacy_treatment_id", "legacy_tooth_status_id", "source_id")
    }
    targets_data = tuple(
        {
            "canal_id": t.canal_id,
            "root_id": t.root_id,
            "surface_code": t.surface_code,
            "target_kind": t.target_kind,
            "tenant_id": t.tenant_id,
            "tooth_key": t.tooth_key,
        }
        for t in draft.targets
    )
    data = {
        "actor_user_id": draft.actor_user_id,
        "event_type": draft.event_type,
        "notes": draft.notes,
        "occurred_at": draft.occurred_at,
        "patient_id": draft.patient_id,
        "payload": filtered_payload,
        "targets": targets_data,
        "tenant_id": draft.tenant_id,
    }
    return canonical_json_dumps(data)


def compute_care_session_canonical_fingerprint(draft: LegacyCareSessionDraft) -> str:
    """
    Compute exact canonical fingerprint for a CareSession draft.
    Uses collision-safe canonical JSON serialization with explicit type tags.
    """
    data = {
        "notes": draft.notes,
        "parent_treatment_id": draft.parent_treatment_id,
        "patient_id": draft.patient_id,
        "session_date": draft.session_date,
        "tenant_id": draft.tenant_id,
    }
    return canonical_json_dumps(data)


def compute_lab_link_canonical_fingerprint(draft: LegacyLabLinkDraft) -> str:
    """
    Compute exact canonical fingerprint for a LabLink draft.
    Uses collision-safe canonical JSON serialization with explicit type tags.
    """
    data = {
        "lab_order_id": draft.lab_order_id,
        "link_token": draft.link_token,
        "patient_id": draft.patient_id,
        "tenant_id": draft.tenant_id,
        "treatment_id": draft.treatment_id,
    }
    return canonical_json_dumps(data)


def mark_ambiguous_duplicates(
    drafts: Sequence[Any],
    fingerprint_fn: Any,
) -> tuple[tuple[Any, ...], tuple[LegacyMappingIssue, ...]]:
    """
    Identify exact duplicates by complete canonical fingerprint.
    Mark ALL instances of exact duplicates as ambiguous duplicates.
    Never merge, drop, or delete any draft or source row.
    Near duplicates remain separate and unflagged.
    """
    fingerprint_counts: dict[str, int] = {}
    for d in drafts:
        fp = fingerprint_fn(d)
        fingerprint_counts[fp] = fingerprint_counts.get(fp, 0) + 1

    processed_drafts: list[Any] = []
    duplicate_issues: list[LegacyMappingIssue] = []

    for d in drafts:
        fp = fingerprint_fn(d)
        if fingerprint_counts[fp] > 1:
            # Mark duplicate draft
            updated_draft = type(d)(
                **{**d.__dict__, "is_ambiguous_duplicate": True}
            )
            processed_drafts.append(updated_draft)
            duplicate_issues.append(
                LegacyMappingIssue(
                    code="EXACT_DUPLICATE_RECORD",
                    message=f"Exact duplicate detected for {d.source_kind} id={getattr(d, 'source_id', getattr(d, 'treatment_id', None))}. Marked ambiguous; retained without merging or dropping.",
                    source_kind=getattr(d, "source_kind", "treatment"),
                    source_id=getattr(d, "source_id", getattr(d, "treatment_id", None)),
                    is_ambiguity=True,
                    details=MappingProxyType({"canonical_fingerprint": fp}),
                )
            )
        else:
            processed_drafts.append(d)

    return tuple(processed_drafts), tuple(duplicate_issues)


# ===========================================================================
# Batch Mapping Orchestration
# ===========================================================================

def map_legacy_clinical_batch(
    verified_patient: VerifiedPatientContext,
    treatments: Sequence[Any] = (),
    tooth_statuses: Sequence[Any] = (),
    treatment_sessions: Sequence[Any] = (),
    lab_orders: Sequence[Any] = (),
) -> LegacyMappingBatchResult:
    """
    Execute full deterministic legacy mapping batch for a verified patient.
    Pure code-level mapper:
    - Never mutates source ORM rows.
    - Yields deeply immutable frozen DTO drafts, issues, and ambiguities.
    - Deterministic ordering across all outputs.
    """
    raw_work_items: list[LegacyWorkItemDraft] = []
    raw_events: list[LegacyEventDraft] = []
    raw_care_sessions: list[LegacyCareSessionDraft] = []
    raw_lab_links: list[LegacyLabLinkDraft] = []
    all_issues: list[LegacyMappingIssue] = []
    all_ambiguities: list[LegacyMappingIssue] = []

    # Map Treatments
    treatments_by_id: dict[int, Any] = {}
    for t in treatments:
        t_id = getattr(t, "id", None)
        if t_id is not None:
            treatments_by_id[t_id] = t

        wi, ev, issues = map_legacy_treatment(t, verified_patient)
        for iss in issues:
            if iss.is_ambiguity:
                all_ambiguities.append(iss)
            else:
                all_issues.append(iss)

        if wi is not None:
            raw_work_items.append(wi)
        if ev is not None:
            raw_events.append(ev)

        # Check singleton lab link
        lab_link, link_issue = resolve_exact_lab_link(t, lab_orders, verified_patient)
        if link_issue:
            if not any(
                iss.code == link_issue.code and iss.source_id == link_issue.source_id
                for iss in all_issues + all_ambiguities
            ):
                if link_issue.is_ambiguity:
                    all_ambiguities.append(link_issue)
                else:
                    all_issues.append(link_issue)
        if lab_link is not None:
            raw_lab_links.append(lab_link)

    # Map ToothStatuses
    for ts in tooth_statuses:
        ev, issues = map_legacy_tooth_status(ts, verified_patient)
        for iss in issues:
            if iss.is_ambiguity:
                all_ambiguities.append(iss)
            else:
                all_issues.append(iss)
        if ev is not None:
            raw_events.append(ev)

    # Map TreatmentSessions
    for tsess in treatment_sessions:
        p_id = getattr(tsess, "treatment_id", None)
        parent = treatments_by_id.get(p_id)
        cs, issues = map_legacy_treatment_session(tsess, verified_patient, parent)
        for iss in issues:
            if iss.is_ambiguity:
                all_ambiguities.append(iss)
            else:
                all_issues.append(iss)
        if cs is not None:
            raw_care_sessions.append(cs)

    # Duplicate detection across drafts (Rule 8: Mark ambiguous, never drop/merge)
    final_work_items, wi_dup_issues = mark_ambiguous_duplicates(
        raw_work_items, compute_work_item_canonical_fingerprint
    )
    all_ambiguities.extend(wi_dup_issues)

    final_events, ev_dup_issues = mark_ambiguous_duplicates(
        raw_events, compute_event_canonical_fingerprint
    )
    all_ambiguities.extend(ev_dup_issues)

    final_care_sessions, cs_dup_issues = mark_ambiguous_duplicates(
        raw_care_sessions, compute_care_session_canonical_fingerprint
    )
    all_ambiguities.extend(cs_dup_issues)

    final_lab_links, ll_dup_issues = mark_ambiguous_duplicates(
        raw_lab_links, compute_lab_link_canonical_fingerprint
    )
    all_ambiguities.extend(ll_dup_issues)

    # Stable deterministic sort by stable_key
    sorted_work_items = tuple(sorted(final_work_items, key=lambda w: (w.stable_key, w.source_id)))
    sorted_events = tuple(sorted(final_events, key=lambda e: (e.stable_key, e.source_id)))
    sorted_care_sessions = tuple(sorted(final_care_sessions, key=lambda c: (c.stable_key, c.source_id)))
    sorted_lab_links = tuple(sorted(final_lab_links, key=lambda link: (link.stable_key, link.treatment_id)))

    # Stable sort for issues
    sorted_issues = tuple(sorted(all_issues, key=lambda i: (i.code, i.source_kind, i.source_id or 0)))
    sorted_ambiguities = tuple(sorted(all_ambiguities, key=lambda a: (a.code, a.source_kind, a.source_id or 0)))

    return LegacyMappingBatchResult(
        work_items=sorted_work_items,
        events=sorted_events,
        care_sessions=sorted_care_sessions,
        lab_links=sorted_lab_links,
        issues=sorted_issues,
        ambiguities=sorted_ambiguities,
    )
