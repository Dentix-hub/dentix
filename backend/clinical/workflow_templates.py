"""
Immutable Versioned Workflow Blueprint Registry (Phase G2).

Defines code-level workflow templates and step blueprints for DENTIX Clinical VNext.

Provides six configurable documentation workflow templates (G2-M09 through G2-M14):
- ENDO_RCT: assessment, access, canal_measurement, clean_shape, obturate, restore
- PROS_CROWN: assessment, preparation, impression_scan, provisional, lab, fit_cement
- PROS_BRIDGE: assessment, abutment_preparation, impression_scan, provisional, lab, try_in, fit_cement
- REST_COMPOSITE: assessment, preparation, restore, finish_polish
- SURG_EXTRACTION: assessment, consent, procedure, post_op
- PROS_DENTURE: assessment, impression, jaw_relation, try_in, delivery, review

Invariants:
- Strictly documentation workflow guidance; never automatic diagnosis, mandatory clinical
  protocols, clinical thresholds, drug/dose suggestions, billing/pricing, lab charges,
  auto-booking, inventory deduction, or auto-completion.
- Template versioning invariants:
    1. Positive integer version (version > 0).
    2. Unique (template_code, version) composite key in registry.
    3. Exact version lookup: get_template(template_code, version).
    4. Deterministic latest lookup: get_latest_template(template_code).
    5. Immutable definitions and registry collections.
    6. Safe deep-copy JSON export and roundtrip reconstruction.
    7. Strict rejection of duplicate step codes, duplicate/non-deterministic step orders,
       mismatched metadata, and unknown procedure codes.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from backend.clinical.catalog import (
    CANONICAL_PROCEDURE_CODES,
    ProcedureCode,
)


# ---------------------------------------------------------------------------
# Workflow Step Definition (Immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowStepDefinition:
    step_code: str
    step_order: int
    title: str
    description: str = ""
    is_required: bool = False
    repeatable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.step_code, str) or not self.step_code.strip():
            raise ValueError("step_code must be a non-empty string")
        if type(self.step_order) is not int or self.step_order < 1:
            raise ValueError(f"step_order must be a positive integer >= 1 (got {self.step_order!r})")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(self.is_required, bool):
            raise ValueError(f"is_required must be a boolean (got {self.is_required!r})")
        if not isinstance(self.repeatable, bool):
            raise ValueError(f"repeatable must be a boolean (got {self.repeatable!r})")

    def to_dict(self) -> dict[str, Any]:
        """Safe deep-copy dictionary representation for JSON export."""
        return {
            "step_code": self.step_code,
            "step_order": self.step_order,
            "title": self.title,
            "description": self.description,
            "is_required": self.is_required,
            "repeatable": self.repeatable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowStepDefinition:
        """Construct a validated WorkflowStepDefinition from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict for step definition, got {type(data).__name__}")
        return cls(
            step_code=data.get("step_code", ""),
            step_order=data.get("step_order", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            is_required=data.get("is_required", False),
            repeatable=data.get("repeatable", False),
        )


# ---------------------------------------------------------------------------
# Workflow Template Definition (Immutable & Versioned)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowTemplateDefinition:
    template_code: str
    version: int
    title: str
    procedure_code: str
    steps: tuple[WorkflowStepDefinition, ...]
    description: str = ""
    is_active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.template_code, str) or not self.template_code.strip():
            raise ValueError("template_code must be a non-empty string")
        if type(self.version) is not int or self.version <= 0:
            raise ValueError(f"version must be a positive integer > 0 (got {self.version!r})")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if self.procedure_code not in CANONICAL_PROCEDURE_CODES:
            raise ValueError(
                f"procedure_code '{self.procedure_code}' is not a canonical procedure code. "
                f"Allowed: {CANONICAL_PROCEDURE_CODES}"
            )
        if self.template_code != self.procedure_code:
            raise ValueError(
                f"Mismatched metadata: template_code '{self.template_code}' must equal "
                f"procedure_code '{self.procedure_code}'"
            )
        if not isinstance(self.is_active, bool):
            raise ValueError(f"is_active must be a boolean (got {self.is_active!r})")

        # Convert steps to tuple to ensure immutability
        raw_steps = self.steps
        if not isinstance(raw_steps, (list, tuple)) or len(raw_steps) == 0:
            raise ValueError(f"Template '{self.template_code}' must contain at least one step")

        steps_tuple: tuple[WorkflowStepDefinition, ...] = tuple(raw_steps)
        object.__setattr__(self, "steps", steps_tuple)

        # Validate steps: types, uniqueness of code, uniqueness of order, sequential 1..N order
        seen_codes: set[str] = set()
        seen_orders: set[int] = set()
        for idx, step in enumerate(steps_tuple):
            if not isinstance(step, WorkflowStepDefinition):
                raise TypeError(f"Step at index {idx} in template '{self.template_code}' must be a WorkflowStepDefinition")
            if step.step_code in seen_codes:
                raise ValueError(f"Duplicate step_code '{step.step_code}' in template '{self.template_code}'")
            seen_codes.add(step.step_code)

            if step.step_order in seen_orders:
                raise ValueError(f"Duplicate step_order {step.step_order} in template '{self.template_code}'")
            seen_orders.add(step.step_order)

            expected_order = idx + 1
            if step.step_order != expected_order:
                raise ValueError(
                    f"Non-deterministic step ordering in template '{self.template_code}': "
                    f"step '{step.step_code}' at index {idx} has order {step.step_order}, expected {expected_order}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Safe deep-copy dictionary representation for JSON export."""
        return {
            "template_code": self.template_code,
            "version": self.version,
            "title": self.title,
            "procedure_code": self.procedure_code,
            "description": self.description,
            "is_active": self.is_active,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowTemplateDefinition:
        """Construct a validated WorkflowTemplateDefinition from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict for template definition, got {type(data).__name__}")
        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, (list, tuple)):
            raise TypeError("Expected list or tuple of steps in template data")
        steps = tuple(WorkflowStepDefinition.from_dict(s) for s in raw_steps)
        return cls(
            template_code=data.get("template_code", ""),
            version=data.get("version", 0),
            title=data.get("title", ""),
            procedure_code=data.get("procedure_code", ""),
            steps=steps,
            description=data.get("description", ""),
            is_active=data.get("is_active", True),
        )


# ---------------------------------------------------------------------------
# Canonical v1 Workflow Templates (G2-M09 through G2-M14)
# ---------------------------------------------------------------------------

# G2-M09: Endodontic Root Canal Therapy Template v1
ENDO_RCT_TEMPLATE_V1 = WorkflowTemplateDefinition(
    template_code=ProcedureCode.ENDO_RCT.value,
    version=1,
    title="Endodontic Root Canal Therapy Documentation Workflow",
    procedure_code=ProcedureCode.ENDO_RCT.value,
    description="Configurable chairside documentation workflow for non-surgical endodontic therapy.",
    is_active=True,
    steps=(
        WorkflowStepDefinition(
            step_code="assessment",
            step_order=1,
            title="Pre-Operative Assessment",
            description="Clinical evaluation, radiographic examination, and documentation of pulpal and periapical status.",
        ),
        WorkflowStepDefinition(
            step_code="access",
            step_order=2,
            title="Access Cavity Preparation",
            description="Dental dam isolation, coronal caries/restoration removal, and straight-line access preparation.",
        ),
        WorkflowStepDefinition(
            step_code="canal_measurement",
            step_order=3,
            title="Working Length Determination",
            description="Electronic apex locator determination and radiographic verification of canal working lengths.",
        ),
        WorkflowStepDefinition(
            step_code="clean_shape",
            step_order=4,
            title="Cleaning & Shaping",
            description="Biomechanical canal instrumentation, apical sizing, and antimicrobial irrigation protocol documentation.",
        ),
        WorkflowStepDefinition(
            step_code="obturate",
            step_order=5,
            title="Canal Obturation",
            description="Three-dimensional canal filling, sealer placement, and obturation verification documentation.",
        ),
        WorkflowStepDefinition(
            step_code="restore",
            step_order=6,
            title="Coronal Seal & Restoration",
            description="Placement of coronal barrier, provisional restoration, or definitive post-endodontic coronal seal.",
        ),
    ),
)

# G2-M10: Crown Restoration Template v1
PROS_CROWN_TEMPLATE_V1 = WorkflowTemplateDefinition(
    template_code=ProcedureCode.PROS_CROWN.value,
    version=1,
    title="Crown Restoration Documentation Workflow",
    procedure_code=ProcedureCode.PROS_CROWN.value,
    description="Configurable chairside documentation workflow for single extra-coronal crown restorations.",
    is_active=True,
    steps=(
        WorkflowStepDefinition(
            step_code="assessment",
            step_order=1,
            title="Clinical Assessment & Shade Selection",
            description="Evaluation of tooth restorability, ferrule, periodontal status, and baseline shade documentation.",
        ),
        WorkflowStepDefinition(
            step_code="preparation",
            step_order=2,
            title="Tooth Preparation",
            description="Axial reduction, occlusal clearance, margin design, and line angle refinement documentation.",
        ),
        WorkflowStepDefinition(
            step_code="impression_scan",
            step_order=3,
            title="Impression / Digital Intraoral Scan",
            description="Gingival retraction and elastomeric impression or digital intraoral scan of the preparation.",
        ),
        WorkflowStepDefinition(
            step_code="provisional",
            step_order=4,
            title="Provisional Crown Fabrication",
            description="Interim provisional crown fabrication, marginal adaptation, occlusal check, and temporary cementation.",
        ),
        WorkflowStepDefinition(
            step_code="lab",
            step_order=5,
            title="Lab Prescription & Dispatch",
            description="Prescription generation, material specification, shade instructions, and laboratory handoff.",
        ),
        WorkflowStepDefinition(
            step_code="fit_cement",
            step_order=6,
            title="Try-In & Definitive Cementation",
            description="Evaluation of seating, proximal contacts, marginal fit, aesthetics, occlusion, and definitive cementation.",
        ),
    ),
)

# G2-M11: Bridge Restoration Template v1
PROS_BRIDGE_TEMPLATE_V1 = WorkflowTemplateDefinition(
    template_code=ProcedureCode.PROS_BRIDGE.value,
    version=1,
    title="Fixed Partial Denture (Bridge) Documentation Workflow",
    procedure_code=ProcedureCode.PROS_BRIDGE.value,
    description="Configurable chairside documentation workflow for multi-unit fixed bridge prostheses.",
    is_active=True,
    steps=(
        WorkflowStepDefinition(
            step_code="assessment",
            step_order=1,
            title="Clinical Assessment & Span Analysis",
            description="Evaluation of abutment teeth, crown-to-root ratios, span length, and path of insertion analysis.",
        ),
        WorkflowStepDefinition(
            step_code="abutment_preparation",
            step_order=2,
            title="Abutment Preparation",
            description="Parallel axial preparation of multiple abutment teeth, margin definition, and occlusal reduction.",
        ),
        WorkflowStepDefinition(
            step_code="impression_scan",
            step_order=3,
            title="Impression / Digital Intraoral Scan",
            description="Full-arch elastomeric impression or intraoral scan capturing all abutments and edentulous spaces.",
        ),
        WorkflowStepDefinition(
            step_code="provisional",
            step_order=4,
            title="Provisional Bridge Placement",
            description="Multi-unit provisional bridge fabrication, pontic hygiene adaptation, and interim placement.",
        ),
        WorkflowStepDefinition(
            step_code="lab",
            step_order=5,
            title="Lab Prescription & Dispatch",
            description="Laboratory prescription detailing framework material, pontic contours, connector dimensions, and shade.",
        ),
        WorkflowStepDefinition(
            step_code="try_in",
            step_order=6,
            title="Framework / Substructure Try-In",
            description="Evaluation of framework seating, passive fit, tissue clearance, and aesthetic trial.",
        ),
        WorkflowStepDefinition(
            step_code="fit_cement",
            step_order=7,
            title="Definitive Cementation",
            description="Verification of marginal seating, proximal contacts, pontic tissue contact, occlusion, and cementation.",
        ),
    ),
)

# G2-M12: Composite Restoration Template v1
REST_COMPOSITE_TEMPLATE_V1 = WorkflowTemplateDefinition(
    template_code=ProcedureCode.REST_COMPOSITE.value,
    version=1,
    title="Direct Composite Restoration Documentation Workflow",
    procedure_code=ProcedureCode.REST_COMPOSITE.value,
    description="Configurable chairside documentation workflow for direct resin composite restorations.",
    is_active=True,
    steps=(
        WorkflowStepDefinition(
            step_code="assessment",
            step_order=1,
            title="Clinical Assessment & Shade Selection",
            description="Lesion/defect evaluation, preoperative occlusion assessment, and shade matching.",
        ),
        WorkflowStepDefinition(
            step_code="preparation",
            step_order=2,
            title="Cavity Preparation & Isolation",
            description="Selective caries removal, cavity preparation, dental dam/matrix isolation, and surface conditioning.",
        ),
        WorkflowStepDefinition(
            step_code="restore",
            step_order=3,
            title="Composite Layering & Polymerization",
            description="Adhesive application, incremental anatomical layering of composite, and controlled light curing.",
        ),
        WorkflowStepDefinition(
            step_code="finish_polish",
            step_order=4,
            title="Finishing & Polishing",
            description="Occlusal adjustment, margin finishing, surface polishing, and post-restorative verification.",
        ),
    ),
)

# G2-M13: Surgical Extraction Template v1
SURG_EXTRACTION_TEMPLATE_V1 = WorkflowTemplateDefinition(
    template_code=ProcedureCode.SURG_EXTRACTION.value,
    version=1,
    title="Surgical Extraction Documentation Workflow",
    procedure_code=ProcedureCode.SURG_EXTRACTION.value,
    description="Configurable chairside documentation workflow for surgical and complex exodontia.",
    is_active=True,
    steps=(
        WorkflowStepDefinition(
            step_code="assessment",
            step_order=1,
            title="Pre-Operative Assessment",
            description="Radiographic evaluation of root morphology, adjacent anatomy, medical risk review, and plan verification.",
        ),
        WorkflowStepDefinition(
            step_code="consent",
            step_order=2,
            title="Informed Consent",
            description="Discussion of procedural risks, post-operative expectations, alternatives, and documented patient consent.",
        ),
        WorkflowStepDefinition(
            step_code="procedure",
            step_order=3,
            title="Surgical Extraction",
            description="Mucoperiosteal flap reflection, bone removal/sectioning if indicated, luxation, delivery, and socket debridement.",
        ),
        WorkflowStepDefinition(
            step_code="post_op",
            step_order=4,
            title="Hemostasis & Post-Operative Care",
            description="Hemostasis verification, socket preservation/suturing documentation, and post-operative instruction review.",
        ),
    ),
)

# G2-M14: Removable Denture Template v1
PROS_DENTURE_TEMPLATE_V1 = WorkflowTemplateDefinition(
    template_code=ProcedureCode.PROS_DENTURE.value,
    version=1,
    title="Removable Denture Documentation Workflow",
    procedure_code=ProcedureCode.PROS_DENTURE.value,
    description="Configurable chairside documentation workflow for complete or partial removable dentures.",
    is_active=True,
    steps=(
        WorkflowStepDefinition(
            step_code="assessment",
            step_order=1,
            title="Assessment & Preliminary Examination",
            description="Examination of edentulous ridges, oral mucosa, existing prostheses, and treatment objectives.",
        ),
        WorkflowStepDefinition(
            step_code="impression",
            step_order=2,
            title="Preliminary & Final Impressions",
            description="Preliminary anatomical impression, custom tray fabrication, border molding, and definitive wash impression.",
        ),
        WorkflowStepDefinition(
            step_code="jaw_relation",
            step_order=3,
            title="Jaw Relation Records",
            description="Recording resting vertical dimension, occlusal vertical dimension, centric relation, and facebow transfer.",
        ),
        WorkflowStepDefinition(
            step_code="try_in",
            step_order=4,
            title="Wax Try-In Verification",
            description="Evaluation of teeth arrangement, phonetics, smile line, aesthetics, and centric relation verification.",
        ),
        WorkflowStepDefinition(
            step_code="delivery",
            step_order=5,
            title="Denture Delivery & Adjustment",
            description="Initial prosthesis insertion, pressure-indicating paste adjustment, occlusal equilibration, and patient care guidance.",
        ),
        WorkflowStepDefinition(
            step_code="review",
            step_order=6,
            title="Post-Insertion Review",
            description="Follow-up evaluation for pressure areas, retention, stability, masticatory adaptation, and adjustments.",
        ),
    ),
)

CANONICAL_WORKFLOW_TEMPLATES: tuple[WorkflowTemplateDefinition, ...] = (
    ENDO_RCT_TEMPLATE_V1,
    PROS_CROWN_TEMPLATE_V1,
    PROS_BRIDGE_TEMPLATE_V1,
    REST_COMPOSITE_TEMPLATE_V1,
    SURG_EXTRACTION_TEMPLATE_V1,
    PROS_DENTURE_TEMPLATE_V1,
)


# ---------------------------------------------------------------------------
# G2-M15: Workflow Template Registry
# ---------------------------------------------------------------------------

class WorkflowTemplateRegistry:
    """
    In-memory, immutable-definition registry for versioned workflow blueprints.

    Enforces:
    - Positive integer versioning.
    - Unique (template_code, version) composite key.
    - Exact version lookup.
    - Deterministic latest version lookup.
    - Safe deep-copy JSON export.
    - Seal/freeze capability ensuring canonical collections are immutable after construction.
    """

    def __init__(
        self,
        templates: Iterable[WorkflowTemplateDefinition] | None = None,
        *,
        frozen: bool = False,
    ) -> None:
        self._templates: dict[tuple[str, int], WorkflowTemplateDefinition] = {}
        self._frozen: bool = False
        if templates:
            for template in templates:
                self.register(template)
        if frozen:
            self._frozen = True

    @property
    def is_frozen(self) -> bool:
        """Whether this registry is sealed against modifications."""
        return self._frozen

    def freeze(self) -> None:
        """Seal this registry, preventing any further registrations."""
        self._frozen = True

    def register(self, template: WorkflowTemplateDefinition) -> None:
        """
        Register a workflow template definition.
        Raises TypeError if the registry is sealed/frozen.
        Raises ValueError if (code, version) already exists.
        """
        if self._frozen:
            raise TypeError("Cannot register template: this workflow registry is sealed/immutable")
        if not isinstance(template, WorkflowTemplateDefinition):
            raise TypeError(f"Expected WorkflowTemplateDefinition, got {type(template).__name__}")
        key = (template.template_code, template.version)
        if key in self._templates:
            raise ValueError(
                f"Template with code '{template.template_code}' and version {template.version} "
                "is already registered in registry"
            )
        self._templates[key] = template

    def get_template(self, template_code: str, version: int) -> WorkflowTemplateDefinition:
        """
        Exact lookup by template_code and positive integer version.
        Raises KeyError if not found. Raises ValueError if version <= 0.
        """
        if type(version) is not int or version <= 0:
            raise ValueError(f"version must be a positive integer > 0 (got {version!r})")
        key = (template_code, version)
        if key not in self._templates:
            raise KeyError(f"Template '{template_code}' with version {version} not found in registry")
        return self._templates[key]

    def get_latest_template(self, template_code: str) -> WorkflowTemplateDefinition:
        """
        Deterministic latest lookup: returns the highest positive integer version for template_code.
        Raises KeyError if no versions are registered for template_code.
        """
        matches = [t for t in self._templates.values() if t.template_code == template_code]
        if not matches:
            raise KeyError(f"No templates registered for code '{template_code}'")
        return max(matches, key=lambda t: t.version)

    def list_templates(self, template_code: str | None = None) -> tuple[WorkflowTemplateDefinition, ...]:
        """List registered templates sorted deterministically by (template_code, version)."""
        if template_code is not None:
            matches = [t for t in self._templates.values() if t.template_code == template_code]
        else:
            matches = list(self._templates.values())
        matches.sort(key=lambda t: (t.template_code, t.version))
        return tuple(matches)

    def has_template(self, template_code: str, version: int | None = None) -> bool:
        """Check whether a template code (and optionally specific version) is registered."""
        if version is not None:
            return (template_code, version) in self._templates
        return any(t.template_code == template_code for t in self._templates.values())

    def export_all(self) -> list[dict[str, Any]]:
        """Safe deep-copy JSON export of all registered templates."""
        return copy.deepcopy([t.to_dict() for t in self.list_templates()])

    def copy(self, *, frozen: bool = False) -> WorkflowTemplateRegistry:
        """Return an independent copy of this registry."""
        return WorkflowTemplateRegistry(self._templates.values(), frozen=frozen)

    def __len__(self) -> int:
        return len(self._templates)


# ---------------------------------------------------------------------------
# Default Global Registry & Module Helpers
# ---------------------------------------------------------------------------

def create_default_registry(*, frozen: bool = False) -> WorkflowTemplateRegistry:
    """
    Create a fresh registry initialized with the 6 canonical v1 documentation templates.
    By default, returns an independent mutable registry (e.g. for testing versioning).
    Pass frozen=True to create a sealed instance.
    """
    return WorkflowTemplateRegistry(CANONICAL_WORKFLOW_TEMPLATES, frozen=frozen)


_DEFAULT_REGISTRY: WorkflowTemplateRegistry = create_default_registry(frozen=True)


def get_workflow_registry() -> WorkflowTemplateRegistry:
    """Return the sealed, immutable canonical default workflow template registry."""
    return _DEFAULT_REGISTRY


def get_template(template_code: str, version: int) -> WorkflowTemplateDefinition:
    """Exact version lookup from default registry."""
    return _DEFAULT_REGISTRY.get_template(template_code, version)


def get_latest_template(template_code: str) -> WorkflowTemplateDefinition:
    """Deterministic latest version lookup from default registry."""
    return _DEFAULT_REGISTRY.get_latest_template(template_code)


def list_templates(template_code: str | None = None) -> tuple[WorkflowTemplateDefinition, ...]:
    """List templates from default registry."""
    return _DEFAULT_REGISTRY.list_templates(template_code)
