"""
Tests for legacy treatment clinical work item projection (Item 5).
Ensures that legacy treatments without a standard procedure code:
1. Attempt code derivation from procedure text (Arabic/English terms).
2. Skip projection safely with a warning if no code can be derived, never inserting/updating with empty code "".
3. Updating treatments never throws a 500 / CheckViolationError.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend import models, schemas
from backend.services.treatment_service import TreatmentService
from backend.clinical.catalog import ProcedureCode


@pytest.fixture
def mock_db():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_user():
    user = MagicMock(spec=models.User)
    user.id = 10
    user.tenant_id = 1
    user.role = "doctor"
    user.username = "dr_test"
    return user


@pytest.fixture
def treatment_service(mock_db, mock_user):
    svc = TreatmentService(mock_db, tenant_id=1, current_user=mock_user)
    return svc


def test_map_treatment_derives_fuzzy_procedure_codes(treatment_service):
    """Fuzzy procedure strings like 'حشو عصب' or 'Dental Crown' derive proper canonical codes."""
    t_endo = models.Treatment(patient_id=1, tooth_number=16, procedure="حشو عصب", status="Done")
    mapping_endo = treatment_service._map_treatment_to_clinical(t_endo)
    assert mapping_endo is not None
    assert mapping_endo[0] == ProcedureCode.ENDO_RCT.value

    t_crown = models.Treatment(patient_id=1, tooth_number=21, procedure="Porcelain Crown", status="Done")
    mapping_crown = treatment_service._map_treatment_to_clinical(t_crown)
    assert mapping_crown is not None
    assert mapping_crown[0] == ProcedureCode.PROS_CROWN.value


def test_map_treatment_skips_empty_or_unmappable_procedure(treatment_service, caplog):
    """Empty or unmappable procedures return None (skip projection) and never return empty code string."""
    # Empty string
    t_empty = models.Treatment(id=40, patient_id=1, tooth_number=16, procedure="", status="Done")
    assert treatment_service._map_treatment_to_clinical(t_empty) is None

    # None
    t_none = models.Treatment(id=41, patient_id=1, tooth_number=16, procedure=None, status="Done")
    assert treatment_service._map_treatment_to_clinical(t_none) is None

    # Completely unmappable custom text
    t_unknown = models.Treatment(id=42, patient_id=1, tooth_number=16, procedure="XYZ Nonexistent Proc 123", status="Done")
    assert treatment_service._map_treatment_to_clinical(t_unknown) is None


@pytest.mark.asyncio
async def test_update_treatment_survives_unmapped_procedure_without_500(treatment_service, mock_db):
    """Editing a legacy treatment without a mapped procedure completes successfully without error."""
    treatment_id = 40
    existing_treatment = models.Treatment(
        id=treatment_id,
        tenant_id=1,
        patient_id=5,
        tooth_number=16,
        procedure="",  # Empty code in legacy treatment
        cost=100.0,
        discount=0.0,
        status="Done",
        notes="[Surfaces: O, B]",
        is_deleted=False,
    )

    # Mock DB queries: get treatment by id
    def mock_exec(stmt):
        mock_res = MagicMock()
        s = str(stmt).lower()
        if "from treatments" in s:
            mock_res.scalars.return_value.first.return_value = existing_treatment
        elif "from clinical_events" in s:
            mock_res.scalars.return_value.all.return_value = []
        elif "from clinical_work_items" in s:
            mock_res.scalars.return_value.first.return_value = None
        else:
            mock_res.scalars.return_value.first.return_value = None
            mock_res.scalars.return_value.all.return_value = []
        return mock_res

    mock_db.execute = AsyncMock(side_effect=mock_exec)

    update_data = schemas.TreatmentCreate(
        patient_id=5,
        procedure="",
        notes="Updated notes [Surfaces: O, B]",
        cost=100.0,
    )

    updated = await treatment_service.update_treatment(treatment_id, update_data)
    assert updated is not None
    assert updated.notes == "Updated notes [Surfaces: O, B]"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_treatment_survives_sync_exception(treatment_service, mock_db):
    """Even if shadow projection sync raises an unexpected error, update_treatment catches it and commits."""
    treatment_id = 40
    existing_treatment = models.Treatment(
        id=treatment_id,
        tenant_id=1,
        patient_id=5,
        tooth_number=16,
        procedure="Composite",
        cost=100.0,
        discount=0.0,
        status="Done",
        is_deleted=False,
    )

    def mock_exec(stmt):
        mock_res = MagicMock()
        s = str(stmt).lower()
        if "from treatments" in s:
            mock_res.scalars.return_value.first.return_value = existing_treatment
        return mock_res

    mock_db.execute = AsyncMock(side_effect=mock_exec)

    with patch.object(
        treatment_service,
        "_sync_clinical_work_item_update",
        side_effect=Exception("Simulated CheckViolationError: ck_clinical_work_items_code_not_empty")
    ):
        update_data = schemas.TreatmentCreate(
            patient_id=5,
            procedure="Composite",
            cost=120.0,
        )
        updated = await treatment_service.update_treatment(treatment_id, update_data)
        assert updated is not None
        mock_db.commit.assert_awaited_once()
