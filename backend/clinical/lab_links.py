"""Cross-check lab-order procedure and tooth against the linked clinical record."""
from sqlalchemy import select

from backend import models
from backend.clinical.catalog import CANONICAL_PROCEDURE_CODES, PROCEDURE_DEFINITIONS
from backend.clinical.legacy_mapping import map_legacy_procedure

_DISPLAY_NAME_CODES = {
    defn.display_name.casefold(): code
    for code, defn in PROCEDURE_DEFINITIONS.items()
}


def _single_code(name):
    if not isinstance(name, str):
        return None
    if name in CANONICAL_PROCEDURE_CODES:
        return name
    if name.strip().casefold() in _DISPLAY_NAME_CODES:
        return _DISPLAY_NAME_CODES[name.strip().casefold()]
    return map_legacy_procedure(name)[0]


def _code(name):
    direct = _single_code(name)
    if direct is not None or not isinstance(name, str):
        return direct
    codes = {c for tok in name.split() if (c := _single_code(tok)) is not None}
    return next(iter(codes)) if len(codes) == 1 else None


def matching_procedure(first, second):
    if first == second:
        return True
    first_code, second_code = _code(first), _code(second)
    return first_code is not None and first_code == second_code


async def validate_work_item_lab_link(db, *, tenant_id, work_item, order):
    if work_item.kind != 'procedure' or not matching_procedure(work_item.code, order.work_type):
        raise ValueError('إجراء طلب المعمل لا يطابق العلاج')
    targets = (await db.execute(select(models.ClinicalWorkItemTarget.tooth_key).where(
        models.ClinicalWorkItemTarget.tenant_id == tenant_id,
        models.ClinicalWorkItemTarget.work_item_id == work_item.id,
    ))).scalars().all()
    tooth_targets = {str(tooth) for tooth in targets if tooth}
    if tooth_targets and order.tooth_number and str(order.tooth_number) not in tooth_targets:
        raise ValueError('سن طلب المعمل لا يطابق العلاج')


def validate_treatment_lab_link(treatment, order):
    if not matching_procedure(treatment.procedure, order.work_type):
        raise ValueError('إجراء طلب المعمل لا يطابق العلاج')
    if treatment.tooth_number is not None and order.tooth_number and str(treatment.tooth_number) != str(order.tooth_number):
        raise ValueError('سن طلب المعمل لا يطابق العلاج')
