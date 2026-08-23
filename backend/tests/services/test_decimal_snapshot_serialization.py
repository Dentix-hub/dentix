"""Regression tests: Decimal values from Numeric columns must serialize.

HIGH-01: price snapshot json.dumps raised TypeError under PostgreSQL.
HIGH-02: inventory learning log json.dumps raised TypeError before commit.
"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.money import money_json_default
from backend.services.export_service import serialize_value
from backend.services.inventory_learning_service import InventoryLearningService
from backend.services.pricing_service import PricingService


DECIMAL_PRICE = Decimal("1000.55")


class TestMoneyJsonDefault:
    def test_decimal_becomes_json_number(self):
        dumped = json.dumps({"unit_price": DECIMAL_PRICE}, default=money_json_default)
        assert '"unit_price": 1000.55' in dumped

    def test_non_decimal_raises_type_error(self):
        with pytest.raises(TypeError):
            json.dumps({"bad": object()}, default=money_json_default)


async def test_apply_price_to_treatment_survives_decimal_price():
    """HIGH-01 reproduction: Decimal unit price + discount must not crash dumps."""
    service = PricingService(db=MagicMock(), tenant_id=1)
    service.get_procedure_price = AsyncMock(return_value=DECIMAL_PRICE)
    service.get_default_price_list = AsyncMock(return_value=None)
    service.get_price_list = AsyncMock(return_value=None)

    treatment = MagicMock()
    treatment.discount = Decimal("100.25")
    treatment.cost = Decimal("0")

    result = await service.apply_price_to_treatment(
        treatment, price_list_id=None, procedure_id=7
    )

    snapshot = json.loads(result.price_snapshot)
    assert snapshot["unit_price"] == 1000.55
    assert snapshot["discount"] == 100.25
    # cost = unit_price - discount, computed without float/Decimal TypeError
    assert result.cost == Decimal("900.30")


async def test_apply_price_to_treatment_float_price_with_decimal_discount():
    """Fallback 0.0/float prices combined with Decimal discount must not raise."""
    service = PricingService(db=MagicMock(), tenant_id=1)
    service.get_default_price_list = AsyncMock(return_value=None)
    service.get_price_list = AsyncMock(return_value=None)

    treatment = MagicMock()
    treatment.discount = Decimal("50")
    treatment.cost = 250.0

    result = await service.apply_price_to_treatment(treatment, price_list_id=None)

    assert result.cost == Decimal("200.00")


async def test_calculate_price_and_snapshot_serializes_decimal():
    """TreatmentService._calculate_price_and_snapshot with Decimal price."""
    from backend.services.treatment_service import TreatmentService

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    patient_row = MagicMock(default_price_list_id=None)
    procedure_row = MagicMock(spec_check=False)
    procedure_row.id = 3

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [patient_row, procedure_row]
    mock_db.execute.return_value = mock_result

    service = TreatmentService.__new__(TreatmentService)
    service.db = mock_db
    service.tenant_id = 1

    fake_pricing = MagicMock()
    fake_pricing.get_procedure_price = AsyncMock(return_value=DECIMAL_PRICE)
    fake_pricing.get_price_list = AsyncMock(return_value=None)
    service.pricing = fake_pricing

    data = MagicMock()
    data.patient_id = 1
    data.procedure = "حشو"

    unit_price, price_snapshot = await service._calculate_price_and_snapshot(
        data, price_list_id=None
    )

    assert unit_price == DECIMAL_PRICE
    snapshot = json.loads(price_snapshot)
    assert snapshot["unit_price"] == 1000.55


async def test_learning_log_serializes_decimal_usage_costs():
    """HIGH-02 reproduction: Decimal cost_calculated inside learning log."""
    mock_db = MagicMock()

    session_mock = MagicMock()
    session_mock.stock_item.batch.material_id = 5
    session_mock.stock_item.tenant_id = 1
    session_mock.id = 77

    service = InventoryLearningService(mock_db)
    await service._log_learning(session_mock, 3.5, {
        "usage_updates": [{"treatment_id": 9, "quantity": 1.5, "cost": DECIMAL_PRICE}],
        "unit_weight_value": 2.5,
    })

    added_log = mock_db.add.call_args.args[0]
    payload = json.loads(added_log.calculation_data)
    assert payload["usage_updates"][0]["cost"] == 1000.55


def test_export_serialize_value_handles_decimal():
    assert serialize_value(DECIMAL_PRICE) == 1000.55
