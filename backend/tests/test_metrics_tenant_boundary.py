from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.routers import metrics as metrics_router


def _scalar_result(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def test_global_business_metrics_are_platform_only():
    with pytest.raises(HTTPException) as exc:
        metrics_router._require_platform_metrics(SimpleNamespace(role="admin"))
    assert exc.value.status_code == 403

    metrics_router._require_platform_metrics(SimpleNamespace(role="super_admin"))


@pytest.mark.asyncio
async def test_profitability_attributes_legacy_payments_through_tenant_patient(monkeypatch):
    db = AsyncMock()
    db.execute.side_effect = [
        _scalar_result(100.0),
        _scalar_result(20.0),
        _scalar_result(10.0),
    ]
    cogs_mock = AsyncMock(return_value=5.0)
    monkeypatch.setattr(metrics_router.inventory_service, "get_cogs_summary", cogs_mock)
    user = SimpleNamespace(role="admin", tenant_id=7)

    response = await metrics_router.get_profitability(period="30d", db=db, current_user=user)

    assert response["data"]["revenue"] == 100.0
    first_statement = str(db.execute.await_args_list[0].args[0])
    assert "JOIN patients" in first_statement
    assert "patients.tenant_id" in first_statement
    assert "payments.tenant_id IS NULL" not in first_statement
    cogs_mock.assert_awaited_once()
    assert cogs_mock.await_args.kwargs["tenant_id"] == 7


@pytest.mark.asyncio
async def test_profitability_rejects_platform_account_without_clinic_context():
    db = AsyncMock()
    user = SimpleNamespace(role="super_admin", tenant_id=None)

    with pytest.raises(HTTPException) as exc:
        await metrics_router.get_profitability(period="30d", db=db, current_user=user)

    assert exc.value.status_code == 400
    db.execute.assert_not_awaited()
