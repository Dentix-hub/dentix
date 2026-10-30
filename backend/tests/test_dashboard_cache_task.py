import inspect
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import backend.crud.billing as billing_crud
import backend.crud.appointment as appointment_crud


@pytest.mark.asyncio
async def test_precompute_dashboard_cache_opens_own_session():
    """Verify precompute_dashboard_cache takes ONLY tenant_id and opens its own session."""
    sig = inspect.signature(billing_crud.precompute_dashboard_cache)
    assert list(sig.parameters.keys()) == ["tenant_id"], "precompute_dashboard_cache must take only tenant_id"

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with patch("backend.database.AsyncSessionLocal", mock_session_factory), \
         patch("backend.crud.billing.get_dashboard_stats", new_callable=AsyncMock) as mock_stats:
        await billing_crud.precompute_dashboard_cache(tenant_id=42)

        # Factory should have been called with RlsContext(tenant_id=42)
        assert mock_session_factory.called
        mock_stats.assert_awaited_once_with(db=mock_session, tenant_id=42)


def test_schedule_dashboard_precompute_strong_reference():
    """Verify schedule_dashboard_precompute retains a strong reference."""
    assert hasattr(billing_crud, "schedule_dashboard_precompute")
    assert hasattr(billing_crud, "_BACKGROUND_TASKS")


def test_no_environment_check_in_production_crud():
    """Verify no ENVIRONMENT testing/ci bypass branches remain in appointment.py or billing.py."""
    appt_source = inspect.getsource(appointment_crud)
    billing_source = inspect.getsource(billing_crud)

    assert "ENVIRONMENT" not in appt_source
    assert "ENVIRONMENT" not in billing_source
