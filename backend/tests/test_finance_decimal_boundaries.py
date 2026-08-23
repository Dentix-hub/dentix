"""Regression tests for PostgreSQL NUMERIC/Decimal finance boundaries."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.routers.laboratories_decimal import build_lab_stats_payload
from backend.routers.metrics_decimal import build_profitability_payload
from backend.services.accounting_decimal_service import (
    DecimalSafeAccountingService,
    _NumericSafeUserProxy,
)
from backend.services.inventory_decimal_service import DecimalInventoryService


def test_profitability_payload_never_mixes_decimal_and_float():
    payload = build_profitability_payload(
        "30d",
        Decimal("1000.00"),
        Decimal("125.25"),
        Decimal("200.50"),
        Decimal("74.25"),
    )

    assert payload["revenue"] == 1000.0
    assert payload["total_costs"] == 400.0
    assert payload["net_profit"] == 600.0
    assert payload["margin_percent"] == 60.0
    assert payload["breakdown"]["material_costs"] == 74.25


def test_lab_stats_empty_payments_use_decimal_zero():
    payload = build_lab_stats_payload(
        lab_id=7,
        lab_name="Test Lab",
        total_orders=2,
        pending_orders=1,
        completed_orders=1,
        total_cost=Decimal("350.75"),
        total_revenue=Decimal("500.00"),
        total_paid=None,
    )

    assert payload["total_cost"] == 350.75
    assert payload["total_paid"] == 0.0
    assert payload["balance"] == 350.75


def test_compensation_proxy_normalizes_numeric_columns_at_legacy_boundary():
    user = SimpleNamespace(
        commission_percent=Decimal("35.00"),
        fixed_salary=Decimal("2500.00"),
        per_appointment_fee=Decimal("20.00"),
        username="doctor",
        id=9,
    )
    safe = _NumericSafeUserProxy(user)

    assert safe.commission_percent == 35.0
    assert safe.fixed_salary == 2500.0
    assert safe.per_appointment_fee == 20.0
    assert safe.username == "doctor"
    assert safe.commission_percent / 100.0 == 0.35


def test_accounting_facade_does_not_mutate_shared_legacy_service_class():
    """The Decimal router adapter must not leak method mutations into services."""
    from backend.services.accounting_service_legacy import (
        AccountingService as LegacyAccountingService,
    )

    original_method = LegacyAccountingService.get_doctor_details_data

    import backend.routers.accounting_decimal  # noqa: F401
    from backend.routers import accounting_legacy as accounting_legacy_router
    from backend.services.accounting_service import (
        AccountingService as FinanceV2AccountingService,
    )

    assert accounting_legacy_router.AccountingService is DecimalSafeAccountingService
    assert LegacyAccountingService.get_doctor_details_data is original_method
    assert (
        LegacyAccountingService.get_doctor_details_data
        is not DecimalSafeAccountingService.get_doctor_details_data
    )
    assert issubclass(DecimalSafeAccountingService, FinanceV2AccountingService)


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _statement):
        return _FakeExecuteResult(self.rows)


@pytest.mark.asyncio
async def test_cogs_service_returns_decimal_not_float():
    rows = [
        (
            SimpleNamespace(change_amount=Decimal("-2.00")),
            SimpleNamespace(cost_per_unit=Decimal("12.345")),
            SimpleNamespace(standard_price=Decimal("0")),
        ),
        (
            SimpleNamespace(change_amount=Decimal("-1.00")),
            SimpleNamespace(cost_per_unit=Decimal("0")),
            SimpleNamespace(standard_price=Decimal("5.555")),
        ),
    ]
    service = DecimalInventoryService()
    result = await service.get_cogs_summary(
        start_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 8, 31, tzinfo=timezone.utc),
        tenant_id=1,
        db=_FakeDb(rows),
    )

    assert isinstance(result, Decimal)
    assert result == Decimal("30.25")
