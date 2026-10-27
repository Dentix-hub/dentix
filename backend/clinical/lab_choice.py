"""Canonical classification and validation for explicit laboratory choices."""
from collections.abc import Mapping
from fastapi import HTTPException

from backend.clinical.catalog import CANONICAL_PROCEDURE_CODES, is_lab_required_procedure
from backend.clinical.legacy_mapping import map_legacy_procedure


LAB_CHOICES = frozenset({"external_lab", "in_clinic"})


def requires_laboratory(procedure: str | None, *, custom_category: str | None = None) -> bool:
    """Classify canonical/allowlisted procedures, or an explicit custom category.

    Unknown names are not classified by fuzzy text. An explicitly assigned
    prosthodontic category can classify an otherwise custom procedure.
    """
    if procedure in CANONICAL_PROCEDURE_CODES:
        return is_lab_required_procedure(procedure)
    canonical, _ = map_legacy_procedure(procedure)
    if canonical:
        return is_lab_required_procedure(canonical)
    return custom_category == "prosthodontic"


def validate_lab_choice(
    *, procedure: str | None, choice: str | None,
    lab_order: Mapping | None, custom_category: str | None = None,
    has_valid_linked_order: bool = False,
) -> None:
    """Validate choice without performing writes or trusting a lab identifier.

    The service using this function must separately check the referenced lab,
    patient and treatment against the current tenant and transaction.
    """
    if choice is not None and choice not in LAB_CHOICES:
        raise HTTPException(status_code=422, detail="يرجى اختيار معمل أو بدون معمل داخل العيادة")
    if choice == "in_clinic" and lab_order is not None:
        raise HTTPException(status_code=422, detail="لا يمكن إضافة بيانات معمل عند اختيار العلاج داخل العيادة")
    if lab_order is not None and (choice != "external_lab" or not lab_order.get("laboratory_id")):
        raise HTTPException(status_code=422, detail="يرجى اختيار معمل صالح لبيانات المعمل")
    if choice == "external_lab" and lab_order is None and not has_valid_linked_order:
        raise HTTPException(status_code=422, detail="يرجى اختيار معمل صالح لبيانات المعمل")
    if requires_laboratory(procedure, custom_category=custom_category) and choice is None and not has_valid_linked_order:
        raise HTTPException(status_code=422, detail="يرجى اختيار معمل أو بدون معمل داخل العيادة")
