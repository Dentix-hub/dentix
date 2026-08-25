from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.inventory_service import InventoryService


def _result(*, all_items=None, first_item=None):
    result = MagicMock()
    scalars = result.scalars.return_value
    scalars.all.return_value = list(all_items or [])
    scalars.first.return_value = first_item
    return result


@pytest.mark.asyncio
async def test_reverse_stock_by_reference_restores_initial_outstanding_movement():
    service = InventoryService()
    db = MagicMock()
    db.execute = AsyncMock()

    original = [SimpleNamespace(stock_item_id=7, change_amount=-2.0, tenant_id=1)]
    stock_item = SimpleNamespace(id=7, quantity=8.0, tenant_id=1)
    db.execute.side_effect = [
        _result(all_items=original),
        _result(all_items=[]),
        _result(first_item=stock_item),
    ]

    reversals = await service.reverse_stock_by_reference(
        reference_id="TREATMENT:100",
        user_id=10,
        db=db,
    )

    assert len(reversals) == 1
    assert reversals[0].stock_item_id == 7
    assert reversals[0].change_amount == pytest.approx(2.0)
    assert reversals[0].reference_id == "REVERSE:TREATMENT:100"
    assert stock_item.quantity == pytest.approx(10.0)
    db.add.assert_called_once_with(reversals[0])


@pytest.mark.asyncio
async def test_reverse_stock_by_reference_is_noop_when_reference_is_fully_balanced():
    service = InventoryService()
    db = MagicMock()
    db.execute = AsyncMock()

    original = [SimpleNamespace(stock_item_id=7, change_amount=-2.0)]
    prior_reversal = [SimpleNamespace(stock_item_id=7, change_amount=2.0)]
    db.execute.side_effect = [
        _result(all_items=original),
        _result(all_items=prior_reversal),
    ]

    reversals = await service.reverse_stock_by_reference(
        reference_id="TREATMENT:100",
        user_id=10,
        db=db,
    )

    assert reversals == []
    db.add.assert_not_called()
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_reverse_stock_by_reference_reverses_new_usage_after_prior_reversal():
    service = InventoryService()
    db = MagicMock()
    db.execute = AsyncMock()

    # Initial usage (-2) was already reversed (+2), then the first edit consumed
    # another 3 units under the same treatment reference. The next edit must
    # reverse only the still-outstanding -3 rather than treating the reference
    # as permanently reversed.
    original = [
        SimpleNamespace(stock_item_id=7, change_amount=-2.0, tenant_id=1),
        SimpleNamespace(stock_item_id=7, change_amount=-3.0, tenant_id=1),
    ]
    prior_reversal = [SimpleNamespace(stock_item_id=7, change_amount=2.0)]
    stock_item = SimpleNamespace(id=7, quantity=7.0, tenant_id=1)
    db.execute.side_effect = [
        _result(all_items=original),
        _result(all_items=prior_reversal),
        _result(first_item=stock_item),
    ]

    reversals = await service.reverse_stock_by_reference(
        reference_id="TREATMENT:100",
        user_id=10,
        db=db,
    )

    assert len(reversals) == 1
    assert reversals[0].change_amount == pytest.approx(3.0)
    assert stock_item.quantity == pytest.approx(10.0)
