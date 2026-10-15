"""
Canonical Clinical Catalog and Taxonomy (Phase G2).

Defines code-level canonical clinical codes, taxonomies, allowed anatomical targets,
and validation rules for DENTIX Clinical VNext.

All visual codes maintain exact 1:1 parity with frozen frontend contracts:
- `frontend/src/features/clinical-chart/domain/clinicalVisualCodes.js`
- `frontend/src/features/clinical-chart/domain/clinicalChartProjection.js`

Invariants:
- Zero aliases (no alternate names, synonyms, or short forms).
- PROS_DENTURE is backend catalog-only with renderer_supported=False; not projected
  to frontend before G6.
- Allowed target kinds are strictly: tooth, surface, root, canal.
- Treatment work-item lifecycle is strictly: proposed, planned, active, completed, cancelled.
  (Historical "existing" is visual phase/provenance, never a writable treatment status).
- Minimal procedure taxonomy:
    restorative / direct
    endodontic / root-canal
    prosthodontic / fixed, removable
    implantology / fixture, prosthetic
    oral-surgery / extraction
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Sequence


# ---------------------------------------------------------------------------
# G2-M03: Tooth Lifecycle Codes (Exact parity with frontend TOOTH_LIFECYCLE_CODES)
# ---------------------------------------------------------------------------

class ToothLifecycleCode(StrEnum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    EXTRACTED = "EXTRACTED"
    IMPACTED = "IMPACTED"
    UNERUPTED = "UNERUPTED"


CANONICAL_TOOTH_LIFECYCLE_CODES: tuple[str, ...] = tuple(c.value for c in ToothLifecycleCode)


# ---------------------------------------------------------------------------
# G2-M02: Finding Codes (Exact parity with frontend FINDING_CODES)
# ---------------------------------------------------------------------------

class FindingCode(StrEnum):
    CARIES = "CARIES"
    FRACTURE = "FRACTURE"
    PAIN = "PAIN"


CANONICAL_FINDING_CODES: tuple[str, ...] = tuple(c.value for c in FindingCode)


# ---------------------------------------------------------------------------
# G2-M01: Canonical Procedure Codes
# 7 frozen renderer procedures + 1 backend catalog-only procedure (PROS_DENTURE)
# ---------------------------------------------------------------------------

class ProcedureCode(StrEnum):
    REST_COMPOSITE = "REST_COMPOSITE"
    ENDO_RCT = "ENDO_RCT"
    PROS_CROWN = "PROS_CROWN"
    PROS_BRIDGE = "PROS_BRIDGE"
    IMPLANT_FIXTURE = "IMPLANT_FIXTURE"
    IMPLANT_CROWN = "IMPLANT_CROWN"
    SURG_EXTRACTION = "SURG_EXTRACTION"
    PROS_DENTURE = "PROS_DENTURE"


FROZEN_RENDERER_PROCEDURE_CODES: tuple[str, ...] = (
    ProcedureCode.REST_COMPOSITE.value,
    ProcedureCode.ENDO_RCT.value,
    ProcedureCode.PROS_CROWN.value,
    ProcedureCode.PROS_BRIDGE.value,
    ProcedureCode.IMPLANT_FIXTURE.value,
    ProcedureCode.IMPLANT_CROWN.value,
    ProcedureCode.SURG_EXTRACTION.value,
)

CANONICAL_PROCEDURE_CODES: tuple[str, ...] = tuple(c.value for c in ProcedureCode)


# ---------------------------------------------------------------------------
# G2-M04: Treatment Lifecycle Codes (Work-Item Lifecycle)
# Strictly: proposed, planned, active, completed, cancelled
# Historical "existing" is visual phase/provenance, NOT a writable treatment status.
# ---------------------------------------------------------------------------

class TreatmentLifecycleCode(StrEnum):
    PROPOSED = "proposed"
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


CANONICAL_TREATMENT_LIFECYCLE_CODES: tuple[str, ...] = tuple(c.value for c in TreatmentLifecycleCode)


# ---------------------------------------------------------------------------
# Target Kinds (Exact parity with PROJECTION_TARGET_KINDS)
# Exactly: tooth, surface, root, canal
# ---------------------------------------------------------------------------

class TargetKind(StrEnum):
    TOOTH = "tooth"
    SURFACE = "surface"
    ROOT = "root"
    CANAL = "canal"


ALLOWED_TARGET_KINDS: tuple[str, ...] = tuple(k.value for k in TargetKind)


# ---------------------------------------------------------------------------
# G2-M05 & G2-M06: Procedure Category & Subcategory Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProcedureCategory:
    code: str
    display_name: str
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("Category code must be a non-empty string")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("Category display_name must be a non-empty string")


@dataclass(frozen=True)
class ProcedureSubcategory:
    code: str
    category_code: str
    display_name: str
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("Subcategory code must be a non-empty string")
        if not isinstance(self.category_code, str) or not self.category_code.strip():
            raise ValueError("Subcategory category_code must be a non-empty string")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("Subcategory display_name must be a non-empty string")


# Canonical categories
_PROCEDURE_CATEGORIES: dict[str, ProcedureCategory] = {
    "restorative": ProcedureCategory(
        code="restorative",
        display_name="Restorative Dentistry",
        description="Direct and indirect tooth restoration procedures",
    ),
    "endodontic": ProcedureCategory(
        code="endodontic",
        display_name="Endodontics",
        description="Pulpal therapy and root canal treatments",
    ),
    "prosthodontic": ProcedureCategory(
        code="prosthodontic",
        display_name="Prosthodontics",
        description="Fixed and removable prosthetic tooth replacement",
    ),
    "implantology": ProcedureCategory(
        code="implantology",
        display_name="Implantology",
        description="Dental implant fixtures and implant-supported prosthetics",
    ),
    "oral-surgery": ProcedureCategory(
        code="oral-surgery",
        display_name="Oral Surgery",
        description="Surgical and non-surgical exodontia and oral surgical care",
    ),
}

PROCEDURE_CATEGORIES: MappingProxyType[str, ProcedureCategory] = MappingProxyType(_PROCEDURE_CATEGORIES)


# Canonical subcategories
_PROCEDURE_SUBCATEGORIES: dict[str, ProcedureSubcategory] = {
    "direct": ProcedureSubcategory(
        code="direct",
        category_code="restorative",
        display_name="Direct Restorations",
        description="Direct chairside restorations such as composite restorations",
    ),
    "root-canal": ProcedureSubcategory(
        code="root-canal",
        category_code="endodontic",
        display_name="Root Canal Therapy",
        description="Non-surgical and surgical root canal therapy",
    ),
    "fixed": ProcedureSubcategory(
        code="fixed",
        category_code="prosthodontic",
        display_name="Fixed Prosthodontics",
        description="Fixed crowns and bridges",
    ),
    "removable": ProcedureSubcategory(
        code="removable",
        category_code="prosthodontic",
        display_name="Removable Prosthodontics",
        description="Complete and partial removable dentures",
    ),
    "fixture": ProcedureSubcategory(
        code="fixture",
        category_code="implantology",
        display_name="Implant Fixtures",
        description="Endosseous implant surgical fixtures",
    ),
    "prosthetic": ProcedureSubcategory(
        code="prosthetic",
        category_code="implantology",
        display_name="Implant Prosthetics",
        description="Implant-supported crowns and superstructures",
    ),
    "extraction": ProcedureSubcategory(
        code="extraction",
        category_code="oral-surgery",
        display_name="Extractions",
        description="Simple and surgical tooth extractions",
    ),
}

PROCEDURE_SUBCATEGORIES: MappingProxyType[str, ProcedureSubcategory] = MappingProxyType(_PROCEDURE_SUBCATEGORIES)


# ---------------------------------------------------------------------------
# G2-M07: Core Procedure Definitions and Taxonomy Mappings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProcedureDefinition:
    code: str
    display_name: str
    category: str
    subcategory: str
    allowed_target_kinds: tuple[str, ...]
    allow_multiple_targets: bool = False
    renderer_supported: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        if self.code not in CANONICAL_PROCEDURE_CODES:
            raise ValueError(f"Unknown procedure code '{self.code}'")
        if self.category not in _PROCEDURE_CATEGORIES:
            raise ValueError(f"Unknown category '{self.category}' for procedure '{self.code}'")
        if self.subcategory not in _PROCEDURE_SUBCATEGORIES:
            raise ValueError(f"Unknown subcategory '{self.subcategory}' for procedure '{self.code}'")
        subcat = _PROCEDURE_SUBCATEGORIES[self.subcategory]
        if subcat.category_code != self.category:
            raise ValueError(
                f"Subcategory '{self.subcategory}' does not belong to category '{self.category}' "
                f"(expected '{subcat.category_code}')"
            )
        for target in self.allowed_target_kinds:
            if target not in ALLOWED_TARGET_KINDS:
                raise ValueError(f"Invalid target kind '{target}' in procedure '{self.code}'")


_PROCEDURE_DEFINITIONS: dict[str, ProcedureDefinition] = {
    ProcedureCode.REST_COMPOSITE.value: ProcedureDefinition(
        code=ProcedureCode.REST_COMPOSITE.value,
        display_name="Composite Restoration",
        category="restorative",
        subcategory="direct",
        allowed_target_kinds=(TargetKind.SURFACE.value,),
        allow_multiple_targets=False,
        renderer_supported=True,
        description="Direct composite resin restoration placed on specific tooth surfaces.",
    ),
    ProcedureCode.ENDO_RCT.value: ProcedureDefinition(
        code=ProcedureCode.ENDO_RCT.value,
        display_name="Root Canal Treatment",
        category="endodontic",
        subcategory="root-canal",
        allowed_target_kinds=(TargetKind.TOOTH.value, TargetKind.ROOT.value, TargetKind.CANAL.value),
        allow_multiple_targets=False,
        renderer_supported=True,
        description="Complete root canal treatment encompassing tooth, root, and canal anatomical targets.",
    ),
    ProcedureCode.PROS_CROWN.value: ProcedureDefinition(
        code=ProcedureCode.PROS_CROWN.value,
        display_name="Crown Restoration",
        category="prosthodontic",
        subcategory="fixed",
        allowed_target_kinds=(TargetKind.TOOTH.value,),
        allow_multiple_targets=False,
        renderer_supported=True,
        description="Fixed single extra-coronal crown restoration targeting an individual tooth.",
    ),
    ProcedureCode.PROS_BRIDGE.value: ProcedureDefinition(
        code=ProcedureCode.PROS_BRIDGE.value,
        display_name="Fixed Bridge",
        category="prosthodontic",
        subcategory="fixed",
        allowed_target_kinds=(TargetKind.TOOTH.value,),
        allow_multiple_targets=True,
        renderer_supported=True,
        description="Fixed multi-unit partial denture (bridge) spanning multiple tooth targets.",
    ),
    ProcedureCode.IMPLANT_FIXTURE.value: ProcedureDefinition(
        code=ProcedureCode.IMPLANT_FIXTURE.value,
        display_name="Implant Fixture",
        category="implantology",
        subcategory="fixture",
        allowed_target_kinds=(TargetKind.TOOTH.value, TargetKind.ROOT.value),
        allow_multiple_targets=False,
        renderer_supported=True,
        description="Endosseous dental implant fixture placed in tooth/root anatomical site.",
    ),
    ProcedureCode.IMPLANT_CROWN.value: ProcedureDefinition(
        code=ProcedureCode.IMPLANT_CROWN.value,
        display_name="Implant Crown",
        category="implantology",
        subcategory="prosthetic",
        allowed_target_kinds=(TargetKind.TOOTH.value,),
        allow_multiple_targets=False,
        renderer_supported=True,
        description="Implant-supported prosthetic crown restoration targeting tooth position.",
    ),
    ProcedureCode.SURG_EXTRACTION.value: ProcedureDefinition(
        code=ProcedureCode.SURG_EXTRACTION.value,
        display_name="Surgical Extraction",
        category="oral-surgery",
        subcategory="extraction",
        allowed_target_kinds=(TargetKind.TOOTH.value,),
        allow_multiple_targets=False,
        renderer_supported=True,
        description="Surgical or non-surgical exodontia of a specific tooth.",
    ),
    ProcedureCode.PROS_DENTURE.value: ProcedureDefinition(
        code=ProcedureCode.PROS_DENTURE.value,
        display_name="Removable Denture",
        category="prosthodontic",
        subcategory="removable",
        allowed_target_kinds=(TargetKind.TOOTH.value,),
        allow_multiple_targets=True,
        renderer_supported=False,
        description="Removable partial or complete denture spanning multiple teeth (backend catalog-only; non-renderer).",
    ),
}

PROCEDURE_DEFINITIONS: MappingProxyType[str, ProcedureDefinition] = MappingProxyType(_PROCEDURE_DEFINITIONS)


# ---------------------------------------------------------------------------
# G2-M08: Finding Definitions and Target Mappings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FindingDefinition:
    code: str
    display_name: str
    allowed_target_kinds: tuple[str, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if self.code not in CANONICAL_FINDING_CODES:
            raise ValueError(f"Unknown finding code '{self.code}'")
        for target in self.allowed_target_kinds:
            if target not in ALLOWED_TARGET_KINDS:
                raise ValueError(f"Invalid target kind '{target}' in finding '{self.code}'")


_FINDING_DEFINITIONS: dict[str, FindingDefinition] = {
    FindingCode.CARIES.value: FindingDefinition(
        code=FindingCode.CARIES.value,
        display_name="Dental Caries",
        allowed_target_kinds=(TargetKind.TOOTH.value, TargetKind.SURFACE.value),
        description="Dental caries lesion localized to a tooth or specific surface(s).",
    ),
    FindingCode.FRACTURE.value: FindingDefinition(
        code=FindingCode.FRACTURE.value,
        display_name="Tooth Fracture",
        allowed_target_kinds=(TargetKind.TOOTH.value, TargetKind.SURFACE.value),
        description="Structural fracture involving crown tooth structure or specific surfaces.",
    ),
    FindingCode.PAIN.value: FindingDefinition(
        code=FindingCode.PAIN.value,
        display_name="Dental Pain / Odontalgia",
        allowed_target_kinds=(TargetKind.TOOTH.value, TargetKind.ROOT.value, TargetKind.CANAL.value),
        description="Symptomatic dental pain or sensitivity localized to tooth, root, or canal.",
    ),
}

FINDING_DEFINITIONS: MappingProxyType[str, FindingDefinition] = MappingProxyType(_FINDING_DEFINITIONS)


# ---------------------------------------------------------------------------
# Catalog Accessors and Validation Helpers
# ---------------------------------------------------------------------------

def get_procedure(code: str) -> ProcedureDefinition:
    """Retrieve procedure definition by code. Raises KeyError if not found."""
    if code not in _PROCEDURE_DEFINITIONS:
        raise KeyError(f"Unknown procedure code '{code}'. Canonical codes: {CANONICAL_PROCEDURE_CODES}")
    return _PROCEDURE_DEFINITIONS[code]


def get_finding(code: str) -> FindingDefinition:
    """Retrieve finding definition by code. Raises KeyError if not found."""
    if code not in _FINDING_DEFINITIONS:
        raise KeyError(f"Unknown finding code '{code}'. Canonical codes: {CANONICAL_FINDING_CODES}")
    return _FINDING_DEFINITIONS[code]


def get_category(code: str) -> ProcedureCategory:
    """Retrieve category definition by code. Raises KeyError if not found."""
    if code not in _PROCEDURE_CATEGORIES:
        raise KeyError(f"Unknown category code '{code}'. Canonical categories: {tuple(_PROCEDURE_CATEGORIES.keys())}")
    return _PROCEDURE_CATEGORIES[code]


def get_subcategory(code: str) -> ProcedureSubcategory:
    """Retrieve subcategory definition by code. Raises KeyError if not found."""
    if code not in _PROCEDURE_SUBCATEGORIES:
        raise KeyError(
            f"Unknown subcategory code '{code}'. Canonical subcategories: {tuple(_PROCEDURE_SUBCATEGORIES.keys())}"
        )
    return _PROCEDURE_SUBCATEGORIES[code]


def list_procedures(renderer_only: bool = False) -> tuple[ProcedureDefinition, ...]:
    """List all canonical procedure definitions, optionally filtering for renderer-supported only."""
    if renderer_only:
        return tuple(p for p in _PROCEDURE_DEFINITIONS.values() if p.renderer_supported)
    return tuple(_PROCEDURE_DEFINITIONS.values())


def list_findings() -> tuple[FindingDefinition, ...]:
    """List all canonical finding definitions."""
    return tuple(_FINDING_DEFINITIONS.values())


def list_categories() -> tuple[ProcedureCategory, ...]:
    """List all procedure categories."""
    return tuple(_PROCEDURE_CATEGORIES.values())


def list_subcategories(category_code: str | None = None) -> tuple[ProcedureSubcategory, ...]:
    """List all procedure subcategories, optionally filtered by category."""
    if category_code is not None:
        return tuple(s for s in _PROCEDURE_SUBCATEGORIES.values() if s.category_code == category_code)
    return tuple(_PROCEDURE_SUBCATEGORIES.values())


def is_renderer_supported(code: str) -> bool:
    """Return True if procedure code is supported by the frozen frontend renderer."""
    proc = _PROCEDURE_DEFINITIONS.get(code)
    if proc is None:
        return False
    return proc.renderer_supported


def validate_target_kind(target_kind: str) -> str:
    """Validate that target_kind is in ALLOWED_TARGET_KINDS. Returns canonical string or raises ValueError."""
    if target_kind not in ALLOWED_TARGET_KINDS:
        raise ValueError(f"Invalid target kind '{target_kind}'. Allowed: {ALLOWED_TARGET_KINDS}")
    return target_kind


def validate_finding_targets(finding_code: str, target_kinds: Sequence[str]) -> tuple[str, ...]:
    """
    Validate that target_kinds are non-empty and legal for the given finding code.
    Returns normalized tuple of target kinds.
    """
    finding = get_finding(finding_code)
    if not target_kinds:
        raise ValueError(f"At least one target kind is required for finding '{finding_code}'")

    for kind in target_kinds:
        validate_target_kind(kind)
        if kind not in finding.allowed_target_kinds:
            raise ValueError(
                f"Finding '{finding_code}' does not support target kind '{kind}'. "
                f"Allowed target kinds: {finding.allowed_target_kinds}"
            )
    return tuple(target_kinds)


def validate_procedure_targets(
    procedure_code: str,
    target_kinds: Sequence[str],
    target_count: int | None = None,
) -> tuple[str, ...]:
    """
    Validate that target_kinds are non-empty, legal for the procedure code,
    and respect multi-target constraints.
    Returns normalized tuple of target kinds.
    """
    procedure = get_procedure(procedure_code)
    if not target_kinds:
        raise ValueError(f"At least one target kind is required for procedure '{procedure_code}'")

    for kind in target_kinds:
        validate_target_kind(kind)
        if kind not in procedure.allowed_target_kinds:
            raise ValueError(
                f"Procedure '{procedure_code}' does not support target kind '{kind}'. "
                f"Allowed target kinds: {procedure.allowed_target_kinds}"
            )

    tooth_count = target_kinds.count(TargetKind.TOOTH.value)
    has_multiple_teeth = tooth_count > 1
    has_explicit_multi_targets = target_count is not None and target_count > 1

    if (has_explicit_multi_targets or has_multiple_teeth) and not procedure.allow_multiple_targets:
        count = target_count if target_count is not None else tooth_count
        raise ValueError(
            f"Procedure '{procedure_code}' does not allow multiple targets (received {count}). "
            f"Only {procedure.allowed_target_kinds} single targets are permitted."
        )

    return tuple(target_kinds)


def validate_treatment_status(status: str) -> str:
    """
    Validate that status is a canonical treatment work-item lifecycle code.
    Explicitly rejects 'existing' as it is a projection visual phase / provenance indicator,
    not a writable treatment status.
    """
    if status == "existing":
        raise ValueError(
            "'existing' is a projection visual phase / provenance indicator, "
            "not a writable treatment work-item status. "
            f"Allowed statuses: {CANONICAL_TREATMENT_LIFECYCLE_CODES}"
        )
    if status not in CANONICAL_TREATMENT_LIFECYCLE_CODES:
        raise ValueError(
            f"Invalid treatment status '{status}'. "
            f"Allowed statuses: {CANONICAL_TREATMENT_LIFECYCLE_CODES}"
        )
    return status


def validate_tooth_lifecycle(code: str) -> str:
    """Validate that code is a canonical tooth lifecycle code."""
    if code not in CANONICAL_TOOTH_LIFECYCLE_CODES:
        raise ValueError(
            f"Invalid tooth lifecycle code '{code}'. "
            f"Allowed codes: {CANONICAL_TOOTH_LIFECYCLE_CODES}"
        )
    return code
