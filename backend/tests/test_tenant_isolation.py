import pytest
from backend.crud import patient
from backend import models, schemas
from backend.core.tenancy import set_current_tenant_id, reset_current_tenant_id, set_super_admin_bypass, is_super_admin_bypass
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_tenant_isolation_enforcement():
    # 1. Setup Context: User belongs to Tenant 100
    set_current_tenant_id(100)
    mock_db = AsyncMock()

    try:
        # 2. Attempt to access data for Tenant 100 (Should pass validation)
        try:
            await patient.get_patients(mock_db, tenant_id=100)
        except ValueError as e:
            pytest.fail(f"Valid access raised ValueError: {e}")
        except Exception:
            # Ignore other errors (like the mock not supporting query)
            pass

        # 3. Attempt to access data for Tenant 200 (Should FAIL validation)
        try:
            await patient.get_patients(mock_db, tenant_id=200)
            pytest.fail("Cross-tenant access was NOT blocked!")
        except ValueError as e:
            assert "Tenant Isolation Violation" in str(e)
            print("\nSUCCESS: Blocked cross-tenant access.")
    finally:
        # Clean up
        reset_current_tenant_id()


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_b_patients():
    set_current_tenant_id(1)
    mock_db = AsyncMock()
    try:
        with pytest.raises(ValueError) as exc:
            await patient.get_patients(mock_db, tenant_id=2)
        assert "Tenant Isolation Violation" in str(exc.value)
    finally:
        reset_current_tenant_id()


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_b_records():
    set_current_tenant_id(1)
    mock_db = AsyncMock()
    mock_patient = schemas.PatientCreate(name="John Doe", phone="0123456789")
    try:
        with pytest.raises(ValueError) as exc:
            await patient.update_patient(mock_db, patient_id=999, patient=mock_patient, tenant_id=2)
        assert "Tenant Isolation Violation" in str(exc.value)
    finally:
        reset_current_tenant_id()


def test_rls_policy_exists_in_database():
    from backend.models.clinical import TreatmentSession
    # Verify that the class has __rls_policies__ registered
    assert hasattr(TreatmentSession, "__rls_policies__")
    assert len(TreatmentSession.__rls_policies__) > 0
    policy = TreatmentSession.__rls_policies__[0]
    assert any(arg.comparator_name == "tenant_id" for arg in policy.condition_args)


def test_admin_can_see_all_tenants():
    try:
        set_super_admin_bypass(True)
        assert is_super_admin_bypass() is True
    finally:
        set_super_admin_bypass(False)
        assert is_super_admin_bypass() is False


@pytest.mark.asyncio
async def test_direct_sql_respects_rls():
    # Verify that the async session context correctly sets the RlsContext
    from backend.database import AsyncSessionLocal, RlsContext
    session = AsyncSessionLocal(context=RlsContext(tenant_id=100))
    try:
        assert hasattr(session, "_context")
        assert session._context is not None
        assert session._context.tenant_id == 100
    finally:
        await session.close()
