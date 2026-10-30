"""Clinical lab selection must not infer choices or discard explicit zeroes."""
import pytest
from fastapi import HTTPException

from backend.clinical.lab_choice import requires_laboratory, validate_lab_choice
from backend.clinical.catalog import ProcedureCode


def test_lab_classification_uses_canonical_legacy_and_explicit_category():
    assert requires_laboratory(ProcedureCode.PROS_CROWN.value)
    assert requires_laboratory('Crown')
    assert not requires_laboratory('an ambiguous crown-like note')
    assert requires_laboratory('custom procedure', custom_category='prosthodontic')
    assert not requires_laboratory(ProcedureCode.REST_COMPOSITE.value, custom_category='prosthodontic')


@pytest.mark.parametrize('choice,lab_order', [
    (None, None), ('in_clinic', {'cost': 0}), ('external_lab', None),
    (None, {'laboratory_id': 2}), ('external_lab', {'laboratory_id': None, 'paid_now': 0}),
])
def test_invalid_lab_input_is_rejected(choice, lab_order):
    with pytest.raises(HTTPException) as exc:
        validate_lab_choice(procedure=ProcedureCode.PROS_CROWN.value, choice=choice, lab_order=lab_order)
    assert exc.value.status_code == 422


def test_valid_choices_and_existing_order():
    validate_lab_choice(procedure=ProcedureCode.PROS_CROWN.value, choice='in_clinic', lab_order=None)
    validate_lab_choice(procedure=ProcedureCode.PROS_CROWN.value, choice='external_lab', lab_order={'laboratory_id': 2, 'cost': 0})
    validate_lab_choice(procedure=ProcedureCode.PROS_CROWN.value, choice=None, lab_order=None, has_valid_linked_order=True)
    validate_lab_choice(procedure='unknown', choice=None, lab_order=None)
