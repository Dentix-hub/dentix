import pytest
from backend.crud import patient
from backend.core.tenancy import set_current_tenant_id, reset_current_tenant_id
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

def test_tenant_isolation_enforcement():
    # 1. Setup Context: User belongs to Tenant 100
    set_current_tenant_id(100)
    
    mock_db = MagicMock(spec=Session)
    
    # 2. Attempt to access data for Tenant 100 (Should pass validation)
    try:
        # We expect this to call db.query... but fail on query building since it's a mock
        # We just want to ensure it passes the _validate_tenant check
        patient.get_patients(mock_db, tenant_id=100)
    except ValueError as e:
        pytest.fail(f"Valid access raised ValueError: {e}")
    except Exception:
        # Ignore other errors (like the mock not supporting query)
        pass

    # 3. Attempt to access data for Tenant 200 (Should FAIL validation)
    try:
        patient.get_patients(mock_db, tenant_id=200)
        pytest.fail("Cross-tenant access was NOT blocked!")
    except ValueError as e:
        assert "Tenant Isolation Violation" in str(e)
        print("\nSUCCESS: Blocked cross-tenant access.")
    
    # Clean up
    reset_current_tenant_id()

if __name__ == "__main__":
    test_tenant_isolation_enforcement()
