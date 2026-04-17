"""
C6.4 — Insurance Pricing & Copay Tests

Tests the full pricing pipeline:
- PricingService price lookup (fallback chain)
- Price list validity checks
- Insurance copay calculations (percent + fixed)
- PriceListItem discount logic
- Patient share breakdown
- Edge cases (zero coverage, expired lists, etc.)
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from backend.services.pricing_service import PricingService, get_pricing_service
from backend.models.price_list import PriceList, PriceListItem
from backend.models.clinical import Procedure, Treatment


# ============================================
# FIXTURES
# ============================================


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def pricing_service(mock_db):
    """PricingService instance."""
    return PricingService(mock_db, tenant_id=1)


def _make_price_list(
    type_="cash",
    coverage=100.0,
    copay_percent=0.0,
    copay_fixed=0.0,
    is_active=True,
    effective_from=None,
    effective_to=None,
):
    """Helper to create a price list mock."""
    pl = MagicMock(spec=PriceList)
    pl.type = type_
    pl.coverage_percent = coverage
    pl.copay_percent = copay_percent
    pl.copay_fixed = copay_fixed
    pl.is_active = is_active
    pl.effective_from = effective_from
    pl.effective_to = effective_to
    pl.name = f"Test {type_} list"
    return pl


# ============================================
# PRICE LOOKUP CHAIN
# ============================================


class TestPriceLookupChain:
    """Tests for get_procedure_price fallback logic."""

    def test_price_from_specified_list(self, pricing_service, mock_db):
        """Price from explicit price list takes priority."""
        mock_item = MagicMock(spec=PriceListItem)
        mock_item.final_price = 750.0

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        price = pricing_service.get_procedure_price(procedure_id=1, price_list_id=10)
        assert price == 750.0

    def test_fallback_to_default_list(self, pricing_service, mock_db):
        """When specified list has no price, fall to default list."""
        # First call (specified list) → None
        # Second call (default list) → item with price
        mock_item_default = MagicMock(spec=PriceListItem)
        mock_item_default.final_price = 500.0

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,        # specified list returns nothing
            mock_item_default,   # default list returns price
        ]

        mock_default = MagicMock(spec=PriceList)
        mock_default.id = 99

        pricing_service.get_default_price_list = MagicMock(return_value=mock_default)

        price = pricing_service.get_procedure_price(procedure_id=1, price_list_id=10)
        assert price == 500.0

    def test_fallback_to_procedure_price(self, pricing_service, mock_db):
        """When no price list has an entry, fall to Procedure.price."""
        # Both lists return None
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,   # specified list
            None,   # default list
            None,   # default PriceListItem
        ]

        # Procedure fallback — need to restructure the mock chain
        mock_proc = MagicMock(spec=Procedure)
        mock_proc.price = 200.0

        pricing_service.get_default_price_list = MagicMock(return_value=None)

        # Override the query chain to return the procedure on the last call
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,       # specified list item
            mock_proc,  # procedure fallback
        ]

        price = pricing_service.get_procedure_price(procedure_id=1, price_list_id=10)
        assert price == 200.0

    def test_no_price_anywhere_returns_zero(self, pricing_service, mock_db):
        """When no price exists at all, return 0."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        pricing_service.get_default_price_list = MagicMock(return_value=None)

        price = pricing_service.get_procedure_price(procedure_id=999)
        assert price == 0.0

    def test_no_price_list_id_uses_default(self, pricing_service, mock_db):
        """When no price_list_id is provided, go straight to default."""
        mock_item = MagicMock(spec=PriceListItem)
        mock_item.final_price = 600.0

        mock_default = MagicMock(spec=PriceList)
        mock_default.id = 99

        pricing_service.get_default_price_list = MagicMock(return_value=mock_default)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        price = pricing_service.get_procedure_price(procedure_id=1)
        assert price == 600.0


# ============================================
# INSURANCE COPAY CALCULATIONS
# ============================================


class TestInsuranceCopayCalculation:
    """Tests for calculate_patient_share — the core copay logic."""

    def test_cash_price_list_patient_pays_all(self, pricing_service):
        """Cash price list: patient pays 100%, insurance pays 0."""
        pl = _make_price_list(type_="cash")

        result = pricing_service.calculate_patient_share(total=1000.0, price_list=pl)

        assert result["total"] == 1000.0
        assert result["insurance_pays"] == 0.0
        assert result["patient_pays"] == 1000.0
        assert result["copay_type"] == "none"

    def test_insurance_80_20_copay_percent(self, pricing_service):
        """Insurance 80% coverage with 20% copay."""
        pl = _make_price_list(
            type_="insurance",
            coverage=80.0,
            copay_percent=20.0,
            copay_fixed=0.0,
        )

        result = pricing_service.calculate_patient_share(total=1000.0, price_list=pl)

        assert result["total"] == 1000.0
        assert result["patient_pays"] == 200.0    # 20% of 1000
        assert result["insurance_pays"] == 800.0   # 1000 - 200
        assert result["copay_type"] == "percent"

    def test_insurance_fixed_copay(self, pricing_service):
        """Insurance with fixed copay amount."""
        pl = _make_price_list(
            type_="insurance",
            coverage=100.0,
            copay_percent=0.0,
            copay_fixed=50.0,
        )

        result = pricing_service.calculate_patient_share(total=1000.0, price_list=pl)

        assert result["total"] == 1000.0
        assert result["patient_pays"] == 50.0       # Fixed copay
        assert result["insurance_pays"] == 950.0     # 1000 - 50
        assert result["copay_type"] == "fixed"

    def test_insurance_fixed_copay_priority_over_percent(self, pricing_service):
        """Fixed copay takes priority when both are set."""
        pl = _make_price_list(
            type_="insurance",
            coverage=80.0,
            copay_percent=20.0,
            copay_fixed=100.0,  # Fixed > 0 takes priority
        )

        result = pricing_service.calculate_patient_share(total=1000.0, price_list=pl)

        assert result["patient_pays"] == 100.0  # Fixed wins
        assert result["copay_type"] == "fixed"

    def test_insurance_100_percent_coverage(self, pricing_service):
        """Full coverage with no copay — patient pays nothing."""
        pl = _make_price_list(
            type_="insurance",
            coverage=100.0,
            copay_percent=0.0,
            copay_fixed=0.0,
        )

        result = pricing_service.calculate_patient_share(total=1000.0, price_list=pl)

        assert result["patient_pays"] == 0.0
        assert result["insurance_pays"] == 1000.0

    def test_insurance_zero_total(self, pricing_service):
        """Zero total should produce zero for all."""
        pl = _make_price_list(
            type_="insurance",
            coverage=80.0,
            copay_percent=20.0,
        )

        result = pricing_service.calculate_patient_share(total=0.0, price_list=pl)

        assert result["total"] == 0.0
        assert result["patient_pays"] == 0.0
        assert result["insurance_pays"] == 0.0

    def test_insurance_large_fixed_copay_clamped(self, pricing_service):
        """Fixed copay larger than total should not produce negative insurance."""
        pl = _make_price_list(
            type_="insurance",
            coverage=100.0,
            copay_fixed=2000.0,  # More than the 500 total
        )

        result = pricing_service.calculate_patient_share(total=500.0, price_list=pl)

        assert result["patient_pays"] == 2000.0
        assert result["insurance_pays"] == 0.0  # max(0, -1500) = 0

    @pytest.mark.parametrize(
        "total,coverage,copay_pct,copay_fixed,exp_patient,exp_insurance",
        [
            (1000.0, 80.0, 20.0, 0.0, 200.0, 800.0),
            (500.0, 70.0, 30.0, 0.0, 150.0, 350.0),
            (2000.0, 90.0, 0.0, 100.0, 100.0, 1900.0),
            (100.0, 50.0, 50.0, 0.0, 50.0, 50.0),
            (750.0, 100.0, 0.0, 25.0, 25.0, 725.0),
        ],
    )
    def test_insurance_parametrized_scenarios(
        self,
        pricing_service,
        total,
        coverage,
        copay_pct,
        copay_fixed,
        exp_patient,
        exp_insurance,
    ):
        """Parametrized insurance calculation scenarios."""
        pl = _make_price_list(
            type_="insurance",
            coverage=coverage,
            copay_percent=copay_pct,
            copay_fixed=copay_fixed,
        )

        result = pricing_service.calculate_patient_share(total=total, price_list=pl)

        assert result["patient_pays"] == pytest.approx(exp_patient, abs=0.01)
        assert result["insurance_pays"] == pytest.approx(exp_insurance, abs=0.01)


# ============================================
# PRICE LIST ITEM DISCOUNT
# ============================================


class TestPriceListItemDiscount:
    """Tests for PriceListItem.final_price property."""

    def test_no_discount_returns_base_price(self):
        """No discount → final_price == price."""
        item = PriceListItem()
        item.price = 1000.0
        item.discount_percent = 0.0

        assert item.final_price == 1000.0

    def test_discount_percent_applied(self):
        """10% discount on 1000 → 900."""
        item = PriceListItem()
        item.price = 1000.0
        item.discount_percent = 10.0

        assert item.final_price == pytest.approx(900.0)

    def test_full_discount(self):
        """100% discount → 0."""
        item = PriceListItem()
        item.price = 500.0
        item.discount_percent = 100.0

        assert item.final_price == pytest.approx(0.0)

    def test_none_discount_treated_as_zero(self):
        """None discount should return base price."""
        item = PriceListItem()
        item.price = 500.0
        item.discount_percent = None

        assert item.final_price == 500.0


# ============================================
# PRICE LIST VALIDITY
# ============================================


class TestPriceListValidity:
    """Tests for PriceList.is_valid() method."""

    def test_active_no_dates_is_valid(self):
        """Active list with no date constraints is valid."""
        pl = PriceList()
        pl.is_active = True
        pl.effective_from = None
        pl.effective_to = None

        assert pl.is_valid() is True

    def test_inactive_is_not_valid(self):
        """Inactive list should be invalid regardless of dates."""
        pl = PriceList()
        pl.is_active = False
        pl.effective_from = None
        pl.effective_to = None

        assert pl.is_valid() is False

    def test_future_start_date_not_valid(self):
        """List with future effective_from is not yet valid."""
        pl = PriceList()
        pl.is_active = True
        pl.effective_from = date.today() + timedelta(days=30)
        pl.effective_to = None

        assert pl.is_valid() is False

    def test_past_end_date_not_valid(self):
        """List with past effective_to is expired."""
        pl = PriceList()
        pl.is_active = True
        pl.effective_from = None
        pl.effective_to = date.today() - timedelta(days=1)

        assert pl.is_valid() is False

    def test_current_date_in_range_is_valid(self):
        """List with today within [effective_from, effective_to] is valid."""
        pl = PriceList()
        pl.is_active = True
        pl.effective_from = date.today() - timedelta(days=30)
        pl.effective_to = date.today() + timedelta(days=30)

        assert pl.is_valid() is True


# ============================================
# TREATMENT PRICING APPLICATION
# ============================================


class TestApplyPriceToTreatment:
    """Tests for PricingService.apply_price_to_treatment."""

    def test_applies_unit_price_and_snapshot(self, pricing_service):
        """Should set unit_price, cost, and price_snapshot on treatment."""
        treatment = Treatment()
        treatment.discount = 0.0
        treatment.cost = 0.0

        pricing_service.get_procedure_price = MagicMock(return_value=1500.0)
        mock_pl = MagicMock(spec=PriceList)
        mock_pl.name = "Insurance ABC"
        mock_pl.type = "insurance"
        pricing_service.get_price_list = MagicMock(return_value=mock_pl)

        result = pricing_service.apply_price_to_treatment(
            treatment, price_list_id=5, procedure_id=10
        )

        assert result.unit_price == 1500.0
        assert result.cost == 1500.0
        assert result.price_list_id == 5
        assert result.price_snapshot is not None
        assert "Insurance ABC" in result.price_snapshot

    def test_applies_discount_correctly(self, pricing_service):
        """Cost should be unit_price minus discount."""
        treatment = Treatment()
        treatment.discount = 200.0
        treatment.cost = 0.0

        pricing_service.get_procedure_price = MagicMock(return_value=1000.0)
        mock_pl = MagicMock(spec=PriceList)
        mock_pl.name = "Cash"
        mock_pl.type = "cash"
        pricing_service.get_price_list = MagicMock(return_value=mock_pl)

        result = pricing_service.apply_price_to_treatment(
            treatment, price_list_id=1, procedure_id=5
        )

        assert result.unit_price == 1000.0
        assert result.cost == 800.0  # 1000 - 200

    def test_fallback_to_default_list_when_none_provided(self, pricing_service):
        """When no price_list_id, use default price list."""
        treatment = Treatment()
        treatment.discount = 0.0
        treatment.cost = 500.0

        mock_default = MagicMock(spec=PriceList)
        mock_default.id = 99
        mock_default.name = "Default Cash"
        mock_default.type = "cash"

        pricing_service.get_default_price_list = MagicMock(return_value=mock_default)
        pricing_service.get_procedure_price = MagicMock(return_value=500.0)
        pricing_service.get_price_list = MagicMock(return_value=mock_default)

        result = pricing_service.apply_price_to_treatment(
            treatment, price_list_id=None, procedure_id=5
        )

        assert result.price_list_id == 99


# ============================================
# FACTORY
# ============================================


class TestPricingFactory:
    """Test factory function."""

    def test_factory_returns_service(self, mock_db):
        svc = get_pricing_service(mock_db, tenant_id=42)
        assert isinstance(svc, PricingService)
        assert svc.tenant_id == 42
