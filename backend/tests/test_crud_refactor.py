import unittest
import os
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import models and crud
from backend import models
# Import from the new package structure
from backend.crud import patient as crud_patient
from backend.crud import procedure as crud_procedure
from backend.crud import billing as crud_billing
from backend.crud import auth as crud_auth

# Setup in-memory SQLite
# Setup DB for testing
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    import os
    # Fallback only if we really must, but instruction says remove SQLite.
    # We will expect DATABASE_URL.
    raise RuntimeError("DATABASE_URL must be set for tests.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TestCRUDRefactor(unittest.TestCase):
    def setUp(self):
        # Create tables
        models.Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.tenant_id = 1
        self.doctor_id = 1

    def tearDown(self):
        self.db.close()
        models.Base.metadata.drop_all(bind=engine)

    def test_patient_lifecycle(self):
        # Mock Schema
        class MockPatientCreate:
            name = "Test Patient CRUD"
            phone = "1234567890"
            age = 30
            address = "123 Test St"
            medical_history = "None"
            notes = "Test"
            # crud.create_patient does: db_patient = models.Patient(**patient.dict())
            # So we need .dict()
            def dict(self):
                return {
                    "name": self.name,
                    "phone": self.phone,
                    "age": self.age,
                    "address": self.address,
                    "medical_history": self.medical_history,
                    "notes": self.notes
                }

        mock_patient = MockPatientCreate()
        
        # Test Create via CRUD
        created_patient = crud_patient.create_patient(self.db, mock_patient, self.tenant_id)
        self.assertIsNotNone(created_patient.id)
        self.assertEqual(created_patient.name, "Test Patient CRUD")
        self.assertEqual(created_patient.tenant_id, self.tenant_id)
        
        # Test Read via CRUD
        fetched = crud_patient.get_patient(self.db, created_patient.id, self.tenant_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Test Patient CRUD")

    def test_basic_crud_imports_and_execution(self):
        """
        Verify that we can call functions from the new modules.
        This test will fail if the imports are broken or if the code has syntax errors.
        """
        # 1. Auth / User (Mocking)
        # We need to create a dummy user/tenant manually for foreign keys if we were doing full integration
        # For now, just checking function existence and basic query behavior (even if return empty)
        
        # Check CRUD functions presence
        self.assertTrue(callable(crud_patient.get_patient))
        self.assertTrue(callable(crud_patient.create_patient))
        self.assertTrue(callable(crud_billing.create_treatment))
        self.assertTrue(callable(crud_billing.get_financial_stats))
        self.assertTrue(callable(crud_procedure.get_procedures))

    def test_procedure_crud(self):
        # Manual DB insertion to test READ
        proc = models.Procedure(name="Cleaning", price=100.0, tenant_id=self.tenant_id)
        self.db.add(proc)
        self.db.commit()
        
        # Test GET
        procs = crud_procedure.get_procedures(self.db, self.tenant_id)
        self.assertEqual(len(procs), 1)
        self.assertEqual(procs[0].name, "Cleaning")

if __name__ == '__main__':
    unittest.main()
