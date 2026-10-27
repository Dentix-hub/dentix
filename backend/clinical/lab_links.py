"""Cross-check lab-order procedure and tooth against the linked clinical record."""
from sqlalchemy import select

from backend import models
from backend.clinical.catalog import CANONICAL_PROCEDURE_CODES
from backend.clinical.legacy_mapping import map_legacy_procedure


def _code(name):
    if name in CANONICAL_PROCEDURE_CODES:
        return name
    return map_legacy_procedure(name)[0]


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
    if order.tooth_number and str(order.tooth_number) not in {str(tooth) for tooth in targets if tooth}:
        raise ValueError('سن طلب المعمل لا يطابق العلاج')


def validate_treatment_lab_link(treatment, order):
    if not matching_procedure(treatment.procedure, order.work_type):
        raise ValueError('إجراء طلب المعمل لا يطابق العلاج')
    if treatment.tooth_number is not None and order.tooth_number and str(treatment.tooth_number) != str(order.tooth_number):
        raise ValueError('سن طلب المعمل لا يطابق العلاج')
