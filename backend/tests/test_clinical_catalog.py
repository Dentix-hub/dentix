"""
Tests for DENTIX Clinical VNext Phase G2: Canonical Catalog, Taxonomy, and Workflow Templates.
Verifies G2-M01 through G2-M16:

- G2-M01: Canonical procedure codes (7 frozen renderer + 1 backend catalog-only PROS_DENTURE, zero aliases).
- G2-M02: Canonical finding codes (CARIES, FRACTURE, PAIN, zero aliases).
- G2-M03: Tooth lifecycle codes (PRESENT, MISSING, EXTRACTED, IMPACTED, UNERUPTED).
- G2-M04: Treatment lifecycle codes (proposed, planned, active, completed, cancelled; existing is visual phase).
- G2-M05: Procedure category model (restorative, endodontic, prosthodontic, implantology, oral-surgery).
- G2-M06: Procedure subcategory model (direct, root-canal, fixed, removable, fixture, prosthetic, extraction).
- G2-M07: Core procedure mappings to categories (deterministic mapping).
- G2-M08: Finding and procedure target mappings (strictly tooth, surface, root, canal).
- G2-M09: RCT template v1 (assessment, access, canal_measurement, clean_shape, obturate, restore).
- G2-M10: Crown template v1 (assessment, preparation, impression_scan, provisional, lab, fit_cement).
- G2-M11: Bridge template v1 (assessment, abutment_preparation, impression_scan, provisional, lab, try_in, fit_cement).
- G2-M12: Composite template v1 (assessment, preparation, restore, finish_polish).
- G2-M13: Extraction template v1 (assessment, consent, procedure, post_op).
- G2-M14: Denture template v1 (assessment, impression, jaw_relation, try_in, delivery, review).
- G2-M15: Template versioning rules and registry (positive integer, uniqueness, exact lookup, latest, immutability, JSON roundtrip, rejections).
- G2-M16: Catalog and frontend parity integration tests.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from backend.clinical.catalog import (
    ALLOWED_TARGET_KINDS,
    CANONICAL_FINDING_CODES,
    CANONICAL_PROCEDURE_CODES,
    CANONICAL_TOOTH_LIFECYCLE_CODES,
    CANONICAL_TREATMENT_LIFECYCLE_CODES,
    FROZEN_RENDERER_PROCEDURE_CODES,
    PROCEDURE_CATEGORIES,
    PROCEDURE_SUBCATEGORIES,
    FindingCode,
    ProcedureCode,
    ProcedureDefinition,
    get_category,
    get_finding,
    get_procedure,
    get_subcategory,
    is_renderer_supported,
    list_categories,
    list_subcategories,
    validate_finding_targets,
    validate_procedure_targets,
    validate_target_kind,
    validate_tooth_lifecycle,
    validate_treatment_status,
)
from backend.clinical.workflow_templates import (
    CANONICAL_WORKFLOW_TEMPLATES,
    ENDO_RCT_TEMPLATE_V1,
    WorkflowStepDefinition,
    WorkflowTemplateDefinition,
    create_default_registry,
    get_template,
    get_workflow_registry,
    list_templates,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_VISUAL_CODES_PATH = (
    REPO_ROOT / "frontend" / "src" / "features" / "clinical-chart" / "domain" / "clinicalVisualCodes.js"
)
FRONTEND_PROJECTION_PATH = (
    REPO_ROOT / "frontend" / "src" / "features" / "clinical-chart" / "domain" / "clinicalChartProjection.js"
)


# ===========================================================================
# G2-M01: Canonical Procedure Codes & Renderer Support
# ===========================================================================

def test_g2_m01_frozen_renderer_procedures():
    """Verify exact 7 frozen renderer procedures without aliases."""
    expected_renderer = {
        "REST_COMPOSITE",
        "ENDO_RCT",
        "PROS_CROWN",
        "PROS_BRIDGE",
        "IMPLANT_FIXTURE",
        "IMPLANT_CROWN",
        "SURG_EXTRACTION",
    }
    assert set(FROZEN_RENDERER_PROCEDURE_CODES) == expected_renderer
    assert len(FROZEN_RENDERER_PROCEDURE_CODES) == 7

    for code in FROZEN_RENDERER_PROCEDURE_CODES:
        assert is_renderer_supported(code) is True
        proc = get_procedure(code)
        assert proc.renderer_supported is True


def test_g2_m01_pros_denture_is_backend_only():
    """Verify PROS_DENTURE is backend catalog-only with renderer_supported=False."""
    assert ProcedureCode.PROS_DENTURE.value == "PROS_DENTURE"
    assert "PROS_DENTURE" in CANONICAL_PROCEDURE_CODES
    assert "PROS_DENTURE" not in FROZEN_RENDERER_PROCEDURE_CODES

    proc = get_procedure("PROS_DENTURE")
    assert proc.renderer_supported is False
    assert is_renderer_supported("PROS_DENTURE") is False


def test_g2_m01_zero_procedure_aliases():
    """Verify no procedure aliases exist in the canonical set."""
    disallowed_aliases = {
        "RCT",
        "CROWN",
        "BRIDGE",
        "EXTRACTION",
        "COMPOSITE",
        "IMPLANT",
        "endo_rct",
        "pros_crown",
        "surg_extraction",
        "rest_composite",
    }
    for alias in disallowed_aliases:
        assert alias not in CANONICAL_PROCEDURE_CODES
        with pytest.raises(KeyError):
            get_procedure(alias)
        assert is_renderer_supported(alias) is False


# ===========================================================================
# G2-M02: Canonical Finding Codes
# ===========================================================================

def test_g2_m02_canonical_finding_codes():
    """Verify finding codes are exactly CARIES, FRACTURE, PAIN."""
    expected = {"CARIES", "FRACTURE", "PAIN"}
    assert set(CANONICAL_FINDING_CODES) == expected
    assert len(CANONICAL_FINDING_CODES) == 3

    disallowed_aliases = {"caries", "decay", "fracture", "pain", "PAIN_ACUTE", "PERIAPICAL_LESION"}
    for alias in disallowed_aliases:
        assert alias not in CANONICAL_FINDING_CODES
        with pytest.raises(KeyError):
            get_finding(alias)


# ===========================================================================
# G2-M03: Tooth Lifecycle Codes
# ===========================================================================

def test_g2_m03_tooth_lifecycle_codes():
    """Verify tooth lifecycle codes are exactly PRESENT, MISSING, EXTRACTED, IMPACTED, UNERUPTED."""
    expected = {"PRESENT", "MISSING", "EXTRACTED", "IMPACTED", "UNERUPTED"}
    assert set(CANONICAL_TOOTH_LIFECYCLE_CODES) == expected
    assert len(CANONICAL_TOOTH_LIFECYCLE_CODES) == 5

    for code in expected:
        assert validate_tooth_lifecycle(code) == code

    with pytest.raises(ValueError):
        validate_tooth_lifecycle("present")
    with pytest.raises(ValueError):
        validate_tooth_lifecycle("EXFOLIATED")


# ===========================================================================
# G2-M04: Treatment Lifecycle Codes (Work-Item Statuses)
# ===========================================================================

def test_g2_m04_treatment_lifecycle_codes():
    """Verify treatment work-item lifecycle is strictly proposed, planned, active, completed, cancelled."""
    expected = {"proposed", "planned", "active", "completed", "cancelled"}
    assert set(CANONICAL_TREATMENT_LIFECYCLE_CODES) == expected
    assert len(CANONICAL_TREATMENT_LIFECYCLE_CODES) == 5

    for status in expected:
        assert validate_treatment_status(status) == status


def test_g2_m04_reject_existing_as_writable_status():
    """Verify 'existing' is explicitly rejected as a writable treatment work-item status."""
    with pytest.raises(ValueError, match="projection visual phase / provenance indicator"):
        validate_treatment_status("existing")


def test_g2_m04_reject_invalid_treatment_statuses():
    """Verify unknown or upper-case statuses are rejected."""
    for invalid in ["PROPOSED", "in_progress", "draft", "abandoned", "pending"]:
        with pytest.raises(ValueError):
            validate_treatment_status(invalid)


# ===========================================================================
# G2-M05 & G2-M06: Categories & Subcategories
# ===========================================================================

def test_g2_m05_categories():
    """Verify procedure categories match requirements."""
    expected_categories = {
        "restorative",
        "endodontic",
        "prosthodontic",
        "implantology",
        "oral-surgery",
    }
    assert set(PROCEDURE_CATEGORIES.keys()) == expected_categories
    assert len(list_categories()) == 5

    for cat_code in expected_categories:
        cat = get_category(cat_code)
        assert cat.code == cat_code
        assert len(cat.display_name) > 0


def test_g2_m06_subcategories():
    """Verify procedure subcategories match requirements and link to parent categories."""
    expected_subcategories = {
        "direct": "restorative",
        "root-canal": "endodontic",
        "fixed": "prosthodontic",
        "removable": "prosthodontic",
        "fixture": "implantology",
        "prosthetic": "implantology",
        "extraction": "oral-surgery",
    }
    assert set(PROCEDURE_SUBCATEGORIES.keys()) == set(expected_subcategories.keys())

    for subcat_code, expected_parent in expected_subcategories.items():
        subcat = get_subcategory(subcat_code)
        assert subcat.code == subcat_code
        assert subcat.category_code == expected_parent

    prostho_subcats = list_subcategories("prosthodontic")
    assert {s.code for s in prostho_subcats} == {"fixed", "removable"}


def test_g2_m05_m06_immutability():
    """Verify categories and subcategories are immutable dataclasses."""
    cat = get_category("restorative")
    with pytest.raises(FrozenInstanceError):
        cat.display_name = "Modified Name"  # type: ignore

    subcat = get_subcategory("direct")
    with pytest.raises(FrozenInstanceError):
        subcat.display_name = "Modified Subcat"  # type: ignore

# ===========================================================================
# G2-M07: Map Core Procedures to Categories (Deterministic Mapping)
# ===========================================================================

def test_g2_m07_deterministic_procedure_category_mappings():
    """Verify every canonical procedure maps deterministically to its category and subcategory."""
    expected_mappings = {
        "REST_COMPOSITE": ("restorative", "direct"),
        "ENDO_RCT": ("endodontic", "root-canal"),
        "PROS_CROWN": ("prosthodontic", "fixed"),
        "PROS_BRIDGE": ("prosthodontic", "fixed"),
        "PROS_DENTURE": ("prosthodontic", "removable"),
        "IMPLANT_FIXTURE": ("implantology", "fixture"),
        "IMPLANT_CROWN": ("implantology", "prosthetic"),
        "SURG_EXTRACTION": ("oral-surgery", "extraction"),
    }

    assert len(expected_mappings) == len(CANONICAL_PROCEDURE_CODES)

    for proc_code, (expected_cat, expected_subcat) in expected_mappings.items():
        proc = get_procedure(proc_code)
        assert proc.category == expected_cat, f"{proc_code} expected category {expected_cat}"
        assert proc.subcategory == expected_subcat, f"{proc_code} expected subcategory {expected_subcat}"


def test_g2_m07_procedure_validation_mismatched_category():
    """Verify that creating a procedure definition with mismatched category/subcategory raises ValueError."""
    with pytest.raises(ValueError, match="does not belong to category"):
        ProcedureDefinition(
            code="REST_COMPOSITE",
            display_name="Test Invalid",
            category="endodontic",
            subcategory="direct",
            allowed_target_kinds=("surface",),
        )


# ===========================================================================
# G2-M08: Target Kinds and Mapping Rules
# ===========================================================================

def test_g2_m08_allowed_target_kinds():
    """Verify allowed target kinds are strictly tooth, surface, root, canal."""
    expected = {"tooth", "surface", "root", "canal"}
    assert set(ALLOWED_TARGET_KINDS) == expected
    assert len(ALLOWED_TARGET_KINDS) == 4

    for kind in expected:
        assert validate_target_kind(kind) == kind

    with pytest.raises(ValueError, match="Invalid target kind"):
        validate_target_kind("jaw")
    with pytest.raises(ValueError, match="Invalid target kind"):
        validate_target_kind("pocket")


def test_g2_m08_finding_target_mappings():
    """Verify finding mappings: CARIES (tooth+surface), FRACTURE (tooth+surface), PAIN (tooth+root+canal)."""
    caries = get_finding("CARIES")
    assert set(caries.allowed_target_kinds) == {"tooth", "surface"}

    fracture = get_finding("FRACTURE")
    assert set(fracture.allowed_target_kinds) == {"tooth", "surface"}

    pain = get_finding("PAIN")
    assert set(pain.allowed_target_kinds) == {"tooth", "root", "canal"}

    # Validation successes
    assert validate_finding_targets("CARIES", ["tooth", "surface"]) == ("tooth", "surface")
    assert validate_finding_targets("FRACTURE", ["surface"]) == ("surface",)
    assert validate_finding_targets("PAIN", ["canal", "root"]) == ("canal", "root")

    # Validation failures
    with pytest.raises(ValueError, match="does not support target kind 'root'"):
        validate_finding_targets("CARIES", ["root"])

    with pytest.raises(ValueError, match="does not support target kind 'surface'"):
        validate_finding_targets("PAIN", ["surface"])

    with pytest.raises(ValueError, match="At least one target kind is required"):
        validate_finding_targets("CARIES", [])


def test_g2_m08_procedure_target_mappings():
    """
    Verify procedure mappings per prompt specification:
    - REST_COMPOSITE: surface
    - ENDO_RCT: tooth+root+canal
    - PROS_CROWN: tooth
    - PROS_BRIDGE: tooth with multiple targets allowed
    - IMPLANT_FIXTURE: tooth+root
    - IMPLANT_CROWN: tooth
    - SURG_EXTRACTION: tooth
    - PROS_DENTURE: tooth with multiple targets allowed
    """
    rc = get_procedure("REST_COMPOSITE")
    assert set(rc.allowed_target_kinds) == {"surface"}
    assert rc.allow_multiple_targets is False

    endo = get_procedure("ENDO_RCT")
    assert set(endo.allowed_target_kinds) == {"tooth", "root", "canal"}
    assert endo.allow_multiple_targets is False

    crown = get_procedure("PROS_CROWN")
    assert set(crown.allowed_target_kinds) == {"tooth"}
    assert crown.allow_multiple_targets is False

    bridge = get_procedure("PROS_BRIDGE")
    assert set(bridge.allowed_target_kinds) == {"tooth"}
    assert bridge.allow_multiple_targets is True

    fixture = get_procedure("IMPLANT_FIXTURE")
    assert set(fixture.allowed_target_kinds) == {"tooth", "root"}
    assert fixture.allow_multiple_targets is False

    ic = get_procedure("IMPLANT_CROWN")
    assert set(ic.allowed_target_kinds) == {"tooth"}
    assert ic.allow_multiple_targets is False

    surg = get_procedure("SURG_EXTRACTION")
    assert set(surg.allowed_target_kinds) == {"tooth"}
    assert surg.allow_multiple_targets is False

    denture = get_procedure("PROS_DENTURE")
    assert set(denture.allowed_target_kinds) == {"tooth"}
    assert denture.allow_multiple_targets is True

    # Validate procedure targets success
    assert validate_procedure_targets("REST_COMPOSITE", ["surface"]) == ("surface",)
    assert validate_procedure_targets("ENDO_RCT", ["tooth", "root", "canal"]) == ("tooth", "root", "canal")
    assert validate_procedure_targets("PROS_CROWN", ["tooth"]) == ("tooth",)
    assert validate_procedure_targets("PROS_BRIDGE", ["tooth", "tooth"], target_count=2) == ("tooth", "tooth")
    assert validate_procedure_targets("PROS_DENTURE", ["tooth", "tooth"], target_count=2) == ("tooth", "tooth")

    # Validate procedure targets failures
    with pytest.raises(ValueError, match="does not support target kind 'tooth'"):
        validate_procedure_targets("REST_COMPOSITE", ["tooth"])

    with pytest.raises(ValueError, match="does not allow multiple targets"):
        validate_procedure_targets("PROS_CROWN", ["tooth", "tooth"], target_count=2)

    with pytest.raises(ValueError, match="does not allow multiple targets"):
        validate_procedure_targets("SURG_EXTRACTION", ["tooth", "tooth"], target_count=2)

    with pytest.raises(ValueError, match="At least one target kind is required"):
        validate_procedure_targets("ENDO_RCT", [])

# ===========================================================================
# G2-M09 through G2-M14: Six Configurable Documentation Workflow Templates
# ===========================================================================

def test_g2_m09_endo_rct_template_v1():
    """G2-M09: ENDO_RCT steps: assessment, access, canal_measurement, clean_shape, obturate, restore."""
    tmpl = get_template("ENDO_RCT", 1)
    assert tmpl.template_code == "ENDO_RCT"
    assert tmpl.version == 1
    assert tmpl.procedure_code == "ENDO_RCT"

    expected_steps = [
        "assessment",
        "access",
        "canal_measurement",
        "clean_shape",
        "obturate",
        "restore",
    ]
    actual_steps = [s.step_code for s in tmpl.steps]
    assert actual_steps == expected_steps
    assert [s.step_order for s in tmpl.steps] == [1, 2, 3, 4, 5, 6]


def test_g2_m10_pros_crown_template_v1():
    """G2-M10: PROS_CROWN steps: assessment, preparation, impression_scan, provisional, lab, fit_cement."""
    tmpl = get_template("PROS_CROWN", 1)
    assert tmpl.template_code == "PROS_CROWN"
    assert tmpl.version == 1
    assert tmpl.procedure_code == "PROS_CROWN"

    expected_steps = [
        "assessment",
        "preparation",
        "impression_scan",
        "provisional",
        "lab",
        "fit_cement",
    ]
    actual_steps = [s.step_code for s in tmpl.steps]
    assert actual_steps == expected_steps
    assert [s.step_order for s in tmpl.steps] == [1, 2, 3, 4, 5, 6]


def test_g2_m11_pros_bridge_template_v1():
    """G2-M11: PROS_BRIDGE steps: assessment, abutment_preparation, impression_scan, provisional, lab, try_in, fit_cement."""
    tmpl = get_template("PROS_BRIDGE", 1)
    assert tmpl.template_code == "PROS_BRIDGE"
    assert tmpl.version == 1
    assert tmpl.procedure_code == "PROS_BRIDGE"

    expected_steps = [
        "assessment",
        "abutment_preparation",
        "impression_scan",
        "provisional",
        "lab",
        "try_in",
        "fit_cement",
    ]
    actual_steps = [s.step_code for s in tmpl.steps]
    assert actual_steps == expected_steps
    assert [s.step_order for s in tmpl.steps] == [1, 2, 3, 4, 5, 6, 7]


def test_g2_m12_rest_composite_template_v1():
    """G2-M12: REST_COMPOSITE steps: assessment, preparation, restore, finish_polish."""
    tmpl = get_template("REST_COMPOSITE", 1)
    assert tmpl.template_code == "REST_COMPOSITE"
    assert tmpl.version == 1
    assert tmpl.procedure_code == "REST_COMPOSITE"

    expected_steps = [
        "assessment",
        "preparation",
        "restore",
        "finish_polish",
    ]
    actual_steps = [s.step_code for s in tmpl.steps]
    assert actual_steps == expected_steps
    assert [s.step_order for s in tmpl.steps] == [1, 2, 3, 4]


def test_g2_m13_surg_extraction_template_v1():
    """G2-M13: SURG_EXTRACTION steps: assessment, consent, procedure, post_op."""
    tmpl = get_template("SURG_EXTRACTION", 1)
    assert tmpl.template_code == "SURG_EXTRACTION"
    assert tmpl.version == 1
    assert tmpl.procedure_code == "SURG_EXTRACTION"

    expected_steps = [
        "assessment",
        "consent",
        "procedure",
        "post_op",
    ]
    actual_steps = [s.step_code for s in tmpl.steps]
    assert actual_steps == expected_steps
    assert [s.step_order for s in tmpl.steps] == [1, 2, 3, 4]


def test_g2_m14_pros_denture_template_v1():
    """G2-M14: PROS_DENTURE steps: assessment, impression, jaw_relation, try_in, delivery, review."""
    tmpl = get_template("PROS_DENTURE", 1)
    assert tmpl.template_code == "PROS_DENTURE"
    assert tmpl.version == 1
    assert tmpl.procedure_code == "PROS_DENTURE"

    expected_steps = [
        "assessment",
        "impression",
        "jaw_relation",
        "try_in",
        "delivery",
        "review",
    ]
    actual_steps = [s.step_code for s in tmpl.steps]
    assert actual_steps == expected_steps
    assert [s.step_order for s in tmpl.steps] == [1, 2, 3, 4, 5, 6]


def test_g2_templates_clinical_boundary_compliance():
    """
    Verify templates do not contain:
    - clinical thresholds
    - drug names / dosages (e.g. mg, ml, amoxicillin, epinephrine)
    - billing / pricing / currency / fees
    - lab charges
    - auto-booking triggers
    - inventory deduction
    - auto-completion
    """
    prohibited_terms = [
        "mg",
        "ml",
        "dosage",
        "amoxicillin",
        "epinephrine",
        "lidocaine",
        "price",
        "cost",
        "fee",
        "charge",
        "billing",
        "auto-book",
        "auto-complete",
        "deduct_inventory",
        "threshold",
    ]
    for tmpl in CANONICAL_WORKFLOW_TEMPLATES:
        full_text = f"{tmpl.title} {tmpl.description}".lower()
        for step in tmpl.steps:
            full_text += f" {step.title} {step.description}".lower()

        for term in prohibited_terms:
            assert term not in full_text.split(), (
                f"Prohibited term '{term}' found in template '{tmpl.template_code}'"
            )

# ===========================================================================
# G2-M15: Template Versioning Invariants, Registry & Failure Paths
# ===========================================================================

def test_g2_m15_version_must_be_positive_integer():
    """Verify version must be a positive integer (> 0). Reject 0, negative, float, bool, string."""
    valid_step = WorkflowStepDefinition(step_code="s1", step_order=1, title="Step 1")

    # Version 0 rejected
    with pytest.raises(ValueError, match="version must be a positive integer"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=0,
            title="Invalid",
            procedure_code="ENDO_RCT",
            steps=(valid_step,),
        )

    # Negative version rejected
    with pytest.raises(ValueError, match="version must be a positive integer"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=-1,
            title="Invalid",
            procedure_code="ENDO_RCT",
            steps=(valid_step,),
        )

    # Boolean rejected (bool is subclass of int in python)
    with pytest.raises(ValueError, match="version must be a positive integer"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=True,  # type: ignore
            title="Invalid",
            procedure_code="ENDO_RCT",
            steps=(valid_step,),
        )


def test_g2_m15_registry_uniqueness_and_duplicate_rejection():
    """Verify registry rejects duplicate (template_code, version)."""
    registry = create_default_registry()
    assert len(registry) == 6

    # Attempt to re-register ENDO_RCT v1
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ENDO_RCT_TEMPLATE_V1)


def test_g2_m15_registry_exact_lookup_and_not_found():
    """Verify get_template retrieves exact version, or raises KeyError."""
    registry = create_default_registry()
    tmpl = registry.get_template("ENDO_RCT", 1)
    assert tmpl.template_code == "ENDO_RCT"
    assert tmpl.version == 1

    with pytest.raises(KeyError, match="not found in registry"):
        registry.get_template("ENDO_RCT", 99)

    with pytest.raises(ValueError, match="positive integer"):
        registry.get_template("ENDO_RCT", 0)


def test_g2_m15_registry_deterministic_latest_lookup():
    """Verify get_latest_template returns highest version deterministically."""
    registry = create_default_registry()

    # Initially v1 is latest
    latest = registry.get_latest_template("ENDO_RCT")
    assert latest.version == 1

    # Register v2
    v2_template = WorkflowTemplateDefinition(
        template_code="ENDO_RCT",
        version=2,
        title="Endodontic Root Canal Therapy v2",
        procedure_code="ENDO_RCT",
        description="Updated v2 workflow",
        steps=ENDO_RCT_TEMPLATE_V1.steps,
    )
    registry.register(v2_template)

    # Now v2 is latest
    new_latest = registry.get_latest_template("ENDO_RCT")
    assert new_latest.version == 2

    # Exact lookup for v1 still returns v1
    assert registry.get_template("ENDO_RCT", 1).version == 1
    assert registry.get_template("ENDO_RCT", 2).version == 2

    # Non-existent code raises KeyError
    with pytest.raises(KeyError, match="No templates registered"):
        registry.get_latest_template("UNKNOWN_PROC")


def test_g2_m15_registry_immutability():
    """Verify templates and registry definitions cannot be modified in-place."""
    tmpl = get_template("ENDO_RCT", 1)

    # Cannot reassign attribute on frozen dataclass
    with pytest.raises(FrozenInstanceError):
        tmpl.title = "Changed Title"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        tmpl.steps[0].title = "Changed Step Title"  # type: ignore


def test_g2_m15_canonical_default_registry_is_frozen():
    """
    Verify the canonical default workflow registry is sealed/immutable after construction,
    callers cannot register into it, and no module-level mutation helper is exported.
    """
    import backend.clinical as bc
    import backend.clinical.workflow_templates as bcw

    # Verify no module-level mutation helper is exported
    assert not hasattr(bc, "register_template")
    assert not hasattr(bcw, "register_template")

    # Canonical default registry must be frozen
    default_reg = get_workflow_registry()
    assert default_reg.is_frozen is True

    # Attempting to register into canonical default registry must raise TypeError
    v2_template = WorkflowTemplateDefinition(
        template_code="ENDO_RCT",
        version=2,
        title="Endodontic Root Canal Therapy v2",
        procedure_code="ENDO_RCT",
        steps=ENDO_RCT_TEMPLATE_V1.steps,
    )
    with pytest.raises(TypeError, match="this workflow registry is sealed/immutable"):
        default_reg.register(v2_template)

    # Independent mutable registry can be created for versioning tests
    mutable_reg = create_default_registry()
    assert mutable_reg.is_frozen is False
    mutable_reg.register(v2_template)
    assert mutable_reg.get_template("ENDO_RCT", 2).version == 2

    # Sealed copy or frozen creation works as expected
    sealed_reg = create_default_registry(frozen=True)
    assert sealed_reg.is_frozen is True
    with pytest.raises(TypeError, match="sealed/immutable"):
        sealed_reg.register(v2_template)


def test_g2_m15_reject_mismatched_metadata():
    """
    Verify WorkflowTemplateDefinition rejects mismatched metadata:
    template_code must exactly equal procedure_code, even when both are individually canonical.
    """
    valid_step = WorkflowStepDefinition(step_code="assessment", step_order=1, title="Assessment")

    # Canonical PROS_CROWN with canonical ENDO_RCT must be rejected
    with pytest.raises(
        ValueError,
        match="Mismatched metadata: template_code 'PROS_CROWN' must equal procedure_code 'ENDO_RCT'",
    ):
        WorkflowTemplateDefinition(
            template_code="PROS_CROWN",
            version=1,
            title="Mismatched Crown/RCT",
            procedure_code="ENDO_RCT",
            steps=(valid_step,),
        )

    # Canonical ENDO_RCT with canonical SURG_EXTRACTION must be rejected
    with pytest.raises(
        ValueError,
        match="Mismatched metadata: template_code 'ENDO_RCT' must equal procedure_code 'SURG_EXTRACTION'",
    ):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=1,
            title="Mismatched RCT/Extraction",
            procedure_code="SURG_EXTRACTION",
            steps=(valid_step,),
        )


def test_g2_m15_safe_deep_copy_json_export_and_roundtrip():
    """Verify to_dict returns safe deep copies and roundtrips without side effects."""
    tmpl = get_template("ENDO_RCT", 1)
    exported = tmpl.to_dict()

    assert exported["template_code"] == "ENDO_RCT"
    assert exported["version"] == 1
    assert len(exported["steps"]) == 6

    # Mutating exported dict does NOT mutate tmpl
    exported["title"] = "MUTATED"
    exported["steps"][0]["title"] = "MUTATED STEP"
    assert tmpl.title != "MUTATED"
    assert tmpl.steps[0].title != "MUTATED STEP"

    # Reconstruct from dict
    original_dict = tmpl.to_dict()
    reconstructed = WorkflowTemplateDefinition.from_dict(original_dict)
    assert reconstructed == tmpl
    assert reconstructed.to_dict() == original_dict


def test_g2_m15_reject_duplicate_step_codes():
    """Verify template creation rejects duplicate step codes."""
    duplicate_steps = (
        WorkflowStepDefinition(step_code="access", step_order=1, title="Access 1"),
        WorkflowStepDefinition(step_code="access", step_order=2, title="Access 2"),
    )
    with pytest.raises(ValueError, match="Duplicate step_code 'access'"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=1,
            title="Test Dups",
            procedure_code="ENDO_RCT",
            steps=duplicate_steps,
        )


def test_g2_m15_reject_duplicate_step_orders():
    """Verify template creation rejects duplicate step orders."""
    duplicate_orders = (
        WorkflowStepDefinition(step_code="assessment", step_order=1, title="Step 1"),
        WorkflowStepDefinition(step_code="access", step_order=1, title="Step 2"),
    )
    with pytest.raises(ValueError, match="Duplicate step_order 1"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=1,
            title="Test Duplicate Orders",
            procedure_code="ENDO_RCT",
            steps=duplicate_orders,
        )


def test_g2_m15_reject_non_deterministic_step_ordering():
    """Verify template creation rejects non-sequential or gapped step orders."""
    # Order has gaps: 1, 3 (missing 2)
    gapped_steps = (
        WorkflowStepDefinition(step_code="step1", step_order=1, title="Step 1"),
        WorkflowStepDefinition(step_code="step3", step_order=3, title="Step 3"),
    )
    with pytest.raises(ValueError, match="Non-deterministic step ordering"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=1,
            title="Test Gaps",
            procedure_code="ENDO_RCT",
            steps=gapped_steps,
        )

    # Order does not start at 1: e.g. 2, 3
    non_one_based = (
        WorkflowStepDefinition(step_code="step1", step_order=2, title="Step 1"),
        WorkflowStepDefinition(step_code="step2", step_order=3, title="Step 2"),
    )
    with pytest.raises(ValueError, match="Non-deterministic step ordering"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=1,
            title="Test Non-One-Based",
            procedure_code="ENDO_RCT",
            steps=non_one_based,
        )


def test_g2_m15_reject_unknown_procedure_code():
    """Verify template creation rejects unknown procedure code."""
    valid_step = WorkflowStepDefinition(step_code="s1", step_order=1, title="Step 1")
    with pytest.raises(ValueError, match="not a canonical procedure code"):
        WorkflowTemplateDefinition(
            template_code="UNKNOWN_PROCEDURE",
            version=1,
            title="Unknown Procedure",
            procedure_code="UNKNOWN_PROCEDURE",
            steps=(valid_step,),
        )


def test_g2_m15_reject_empty_steps():
    """Verify template creation rejects empty steps sequence."""
    with pytest.raises(ValueError, match="must contain at least one step"):
        WorkflowTemplateDefinition(
            template_code="ENDO_RCT",
            version=1,
            title="Empty Steps",
            procedure_code="ENDO_RCT",
            steps=(),
        )


# ===========================================================================
# G2-M16: Frontend Parity Integration Test
# ===========================================================================

def test_g2_m16_frontend_visual_codes_parity():
    """
    Direct code inspection verifying exact 1:1 parity between backend canonical codes
    and frontend frozen clinicalVisualCodes.js.
    """
    assert FRONTEND_VISUAL_CODES_PATH.exists(), f"Missing {FRONTEND_VISUAL_CODES_PATH}"
    content = FRONTEND_VISUAL_CODES_PATH.read_text(encoding="utf-8")

    # 1. Tooth lifecycle codes in frontend
    for code in CANONICAL_TOOTH_LIFECYCLE_CODES:
        assert f"{code}: '{code}'" in content or f"{code}: \"{code}\"" in content

    # 2. Finding codes in frontend
    for code in CANONICAL_FINDING_CODES:
        assert f"{code}: '{code}'" in content or f"{code}: \"{code}\"" in content

    # 3. Frozen renderer procedure codes in frontend
    for code in FROZEN_RENDERER_PROCEDURE_CODES:
        assert f"{code}: '{code}'" in content or f"{code}: \"{code}\"" in content

    # 4. PROS_DENTURE must NOT be in frontend clinicalVisualCodes.js
    assert "PROS_DENTURE" not in content, (
        "PROS_DENTURE must NOT be in frozen frontend clinicalVisualCodes.js prior to G6!"
    )


def test_g2_m16_frontend_target_kinds_parity():
    """
    Direct code inspection verifying exact parity of target kinds between backend
    and frontend clinicalChartProjection.js.
    """
    assert FRONTEND_PROJECTION_PATH.exists(), f"Missing {FRONTEND_PROJECTION_PATH}"
    content = FRONTEND_PROJECTION_PATH.read_text(encoding="utf-8")

    # Target kinds in frontend
    for kind in ALLOWED_TARGET_KINDS:
        assert f"'{kind}'" in content or f"\"{kind}\"" in content


def test_g2_m16_traceability_invariance():
    """Verify that backend catalog and templates satisfy all 6 default templates in registry."""
    templates = list_templates()
    assert len(templates) == 6
    codes = {t.template_code for t in templates}
    assert codes == {
        "ENDO_RCT",
        "PROS_CROWN",
        "PROS_BRIDGE",
        "REST_COMPOSITE",
        "SURG_EXTRACTION",
        "PROS_DENTURE",
    }
