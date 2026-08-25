"""
CRUD Refactor Unit Tests (Async)
"""

import pytest
from sqlalchemy import delete
from backend import models, schemas
from backend.crud import patient as crud_patient
from backend.crud import procedure as crud_procedure
from backend.crud import billing as crud_billing

@pytest.fixture(autouse=True)
async def cleanup_db(async_db_session, async_engine_fixture):
    # Ensure tables are created
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # Clean up tables
    await async_db_session.execute(delete(models.ToothStatus))
    await async_db_session.execute(delete(models.Attachment))
    await async_db_session.execute(delete(models.Prescription))
    await async_db_session.execute(delete(models.Patient))
    await async_db_session.execute(delete(models.Procedure))
    await async_db_session.commit()
    yield

@pytest.mark.asyncio
async def test_patient_lifecycle(async_db_session):
    tenant_id = 1

    # Mock Schema/Payload
    class MockPatientCreate:
        name = "Test Patient CRUD"
        phone = "1234567890"
        age = 30
        address = "123 Test St"
        medical_history = "None"
        notes = "Test"

        def dict(self):
            return {
                "name": self.name,
                "phone": self.phone,
                "age": self.age,
                "address": self.address,
                "medical_history": self.medical_history,
                "notes": self.notes,
            }

    mock_patient = MockPatientCreate()

    # Test Create via CRUD
    created_patient = await crud_patient.create_patient(
        async_db_session, mock_patient, tenant_id
    )
    assert created_patient.id is not None
    assert created_patient.name == "Test Patient CRUD"
    assert created_patient.tenant_id == tenant_id

    # Test Read via CRUD
    fetched = await crud_patient.get_patient(async_db_session, created_patient.id, tenant_id)
    assert fetched is not None
    assert fetched.name == "Test Patient CRUD"

@pytest.mark.asyncio
async def test_basic_crud_imports_and_execution():
    """
    Verify that we can call functions from the new modules.
    This test will fail if the imports are broken or if the code has syntax errors.
    """
    assert callable(crud_patient.get_patient)
    assert callable(crud_patient.create_patient)
    assert callable(crud_billing.create_treatment)
    assert callable(crud_billing.get_financial_stats)
    assert callable(crud_procedure.get_procedures)

@pytest.mark.asyncio
async def test_procedure_crud(async_db_session):
    tenant_id = 1

    # Manual DB insertion to test READ
    proc = models.Procedure(name="Cleaning", price=100.0, tenant_id=tenant_id)
    async_db_session.add(proc)
    await async_db_session.commit()

    # Test GET
    procs = await crud_procedure.get_procedures(async_db_session, tenant_id)
    assert len(procs) == 1
    assert procs[0].name == "Cleaning"
