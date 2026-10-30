"""
Tests for legacy treatment clinical work item projection (Fix 2 / Item 5).
Ensures that legacy treatments without a standard procedure code:
1. Require EXACT allowlist match per legacy_mapping.py (G3-M03); no substring or fuzzy matching.
2. Blank or unmapped procedures skip projection safely with a structured warning, never inserting empty code "".
3. Every ClinicalWorkItem insert guards against empty codes (raises ValueError).
4. Updating treatments wraps shadow projection in a nested transaction (begin_nested), so a projection error
   rolls back only to the savepoint and the outer transaction commits successfully (PUT returns 200).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.exc import IntegrityError
from httpx import AsyncClient, ASGITransport

from backend import models, schemas, auth
from backend.services.treatment_service import TreatmentService
from backend.clinical.catalog import CANONICAL_PROCEDURE_CODES
from backend.clinical.legacy_mapping import LEGACY_PROCEDURE_ALLOWLIST
from backend.main import app


@pytest.fixture
def mock_db():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    # Async nested transaction context manager mock
    nested_ctx = AsyncMock()
    nested_ctx.__aenter__.return_value = AsyncMock()
    nested_ctx.__aexit__.return_value = None
    session.begin_nested = MagicMock(return_value=nested_ctx)

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


def test_map_treatment_requires_exact_allowlist_match(treatment_service):
    """
    Per legacy_mapping.py (G3-M03):
    Exact allowlist matches map to canonical codes. Substring or fuzzy keywords are rejected.
    """
    # Exact canonical code
    canonical_sample = next(iter(CANONICAL_PROCEDURE_CODES))
    t_canonical = models.Treatment(patient_id=1, tooth_number=16, procedure=canonical_sample, status="Done")
    mapping_can = treatment_service._map_treatment_to_clinical(t_canonical)
    assert mapping_can is not None
    assert mapping_can[0] == canonical_sample

    # Exact legacy allowlist match
    legacy_sample_key = next(iter(LEGACY_PROCEDURE_ALLOWLIST.keys()))
    expected_code = LEGACY_PROCEDURE_ALLOWLIST[legacy_sample_key]
    t_legacy = models.Treatment(patient_id=1, tooth_number=16, procedure=legacy_sample_key, status="Done")
    mapping_leg = treatment_service._map_treatment_to_clinical(t_legacy)
    assert mapping_leg is not None
    assert mapping_leg[0] == expected_code

    # Non-exact / substring procedure must NOT be fuzzy matched (must return None to skip projection)
    t_fuzzy = models.Treatment(patient_id=1, tooth_number=16, procedure="Random unmapped composite filling", status="Done")
    assert treatment_service._map_treatment_to_clinical(t_fuzzy) is None


def test_map_treatment_skips_empty_or_blank_procedure(treatment_service):
    """Blank or whitespace-only procedures return None and skip projection."""
    t_empty = models.Treatment(id=40, patient_id=1, tooth_number=16, procedure="", status="Done")
    assert treatment_service._map_treatment_to_clinical(t_empty) is None

    t_spaces = models.Treatment(id=40, patient_id=1, tooth_number=16, procedure="   ", status="Done")
    assert treatment_service._map_treatment_to_clinical(t_spaces) is None

    t_none = models.Treatment(id=41, patient_id=1, tooth_number=16, procedure=None, status="Done")
    assert treatment_service._map_treatment_to_clinical(t_none) is None


def test_clinical_work_item_validator_rejects_empty_code():
    """models.ClinicalWorkItem validator prevents empty or whitespace-only codes at construction."""
    with pytest.raises(ValueError, match="ClinicalWorkItem.code cannot be empty"):
        models.ClinicalWorkItem(
            tenant_id=1,
            patient_id=1,
            kind="procedure",
            code="",
        )

    with pytest.raises(ValueError, match="ClinicalWorkItem.code cannot be empty"):
        models.ClinicalWorkItem(
            tenant_id=1,
            patient_id=1,
            kind="procedure",
            code="   ",
        )


@pytest.mark.asyncio
async def test_update_treatment_nested_transaction_survives_integrity_error(treatment_service, mock_db):
    """
    Verify that update_treatment uses self.db.begin_nested() around _sync_clinical_work_item_update.
    A forced IntegrityError inside the projection rolls back only to the savepoint and the
    outer transaction commits successfully without raising 500.
    """
    treatment_id = 40
    existing_treatment = models.Treatment(
        id=treatment_id,
        tenant_id=1,
        patient_id=5,
        tooth_number=16,
        procedure="Root Canal",
        cost=100.0,
        discount=0.0,
        status="Done",
        notes="[Surfaces: O, B]",
        is_deleted=False,
    )

    def mock_exec(stmt):
        mock_res = MagicMock()
        s = str(stmt).lower()
        if "from treatments" in s:
            mock_res.scalars.return_value.first.return_value = existing_treatment
        return mock_res

    mock_db.execute = AsyncMock(side_effect=mock_exec)

    # Force IntegrityError inside _sync_clinical_work_item_update
    with patch.object(
        treatment_service,
        "_sync_clinical_work_item_update",
        side_effect=IntegrityError("ck_clinical_work_items_code_not_empty", orig=Exception("check constraint failed"), params={})
    ):
        update_data = schemas.TreatmentCreate(
            patient_id=5,
            procedure="Root Canal",
            notes="Updated notes",
            cost=150.0,
        )
        updated = await treatment_service.update_treatment(treatment_id, update_data)

        # Assert begin_nested was used
        mock_db.begin_nested.assert_called_once()
        # Assert treatment was updated and outer transaction committed
        assert updated is not None
        assert updated.cost == 150.0
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_put_treatment_api_returns_200_on_unmapped_legacy_treatment(async_db_session):
    """
    Real API test: PUT /api/v1/treatments/{id} with an unmapped procedure code
    updates the treatment and returns 200 without CheckViolationError / 500.
    """
    tenant = models.Tenant(name="Clinical Test Tenant", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="dentist_40",
        email="dentist40@example.com",
        role="admin",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.flush()

    patient = models.Patient(
        name="Patient Forty",
        age=30,
        phone="01012345678",
        medical_history="{}",
        notes="",
        tenant_id=tenant.id,
    )
    async_db_session.add(patient)
    await async_db_session.flush()

    # Legacy treatment 40 with an empty or custom unmapped procedure
    treatment = models.Treatment(
        id=40,
        tenant_id=tenant.id,
        patient_id=patient.id,
        tooth_number=16,
        procedure="",
        notes="[Surfaces: O, B]",
        cost=200.0,
        discount=0.0,
        status="Done",
        doctor_id=user.id,
    )
    async_db_session.add(treatment)
    await async_db_session.commit()

    token = auth.create_access_token({"sub": user.username, "tenant_id": tenant.id, "role": user.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/v1/treatments/{treatment.id}",
            json={
                "patient_id": patient.id,
                "procedure": "",
                "tooth_number": 16,
                "notes": "Updated note without procedure code",
                "cost": 250.0,
                "discount": 0.0,
                "status": "Done",
                "doctor_id": user.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    body = response.json()
    assert body["data"]["cost"] == 250.0
    assert body["data"]["notes"] == "Updated note without procedure code"
