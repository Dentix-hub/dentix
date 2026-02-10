"""
Billing Logic Unit Tests
Tests for BillingService financial calculations with mocked DB.
"""

import pytest
from unittest.mock import MagicMock
from backend.services.billing_service import BillingService
from backend import models, schemas


class TestBillingServiceFinancialStats:
    """Tests for get_financial_stats() method."""

    def setup_method(self):
        """Setup mock DB and service for each test."""
        self.mock_db = MagicMock()
        self.tenant_id = 1
        self.service = BillingService(self.mock_db, self.tenant_id)

    def _mock_scalar_sequence(self, values: list):
        """Helper to mock multiple scalar() calls in sequence."""
        call_count = [0]

        def mock_scalar():
            result = values[call_count[0]] if call_count[0] < len(values) else 0.0
            call_count[0] += 1
            return result

        return mock_scalar

    def test_calculate_revenue_basic(self):
        """Verify revenue = total_cost - total_discount."""
        # Mock: cost=1000, discount=100, payments=500
        # Expected: revenue=900, outstanding=400
        values = [
            1000.0,  # total_cost (treatments)
            100.0,  # total_discount (treatments)
            200.0,  # today_revenue
            500.0,  # total_received (payments)
            100.0,  # today_received
            50.0,  # total_lab_costs
            30.0,  # total_expenses
            10.0,  # today_lab_costs
            5.0,  # today_expenses
        ]

        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = self._mock_scalar_sequence(values)
        self.mock_db.query.return_value = mock_query

        result = self.service.get_financial_stats()

        # Verify calculations
        assert result["total_revenue"] == 900.0  # 1000 - 100
        assert result["total_received"] == 500.0
        assert result["outstanding"] == 400.0  # 900 - 500
        assert result["total_expenses"] == 80.0  # 50 + 30
        assert result["net_profit"] == 420.0  # 500 - 30 - 50

    def test_outstanding_never_negative(self):
        """Verify outstanding is clamped to 0 when payments exceed revenue."""
        # Mock: revenue=100, payments=200
        values = [
            100.0,  # total_cost
            0.0,  # total_discount
            50.0,  # today_revenue
            200.0,  # total_received (exceeds revenue!)
            100.0,  # today_received
            0.0,  # lab costs
            0.0,  # expenses
            0.0,  # today lab
            0.0,  # today expenses
        ]

        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = self._mock_scalar_sequence(values)
        self.mock_db.query.return_value = mock_query

        result = self.service.get_financial_stats()

        # Outstanding should be 0, not negative
        assert result["outstanding"] == 0  # max(0, 100-200)

    def test_empty_database_returns_zeros(self):
        """Verify all values are 0 when no data exists."""
        values = [0.0] * 9  # All queries return None/0

        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = self._mock_scalar_sequence(values)
        self.mock_db.query.return_value = mock_query

        result = self.service.get_financial_stats()

        assert result["total_revenue"] == 0.0
        assert result["total_received"] == 0.0
        assert result["outstanding"] == 0
        assert result["net_profit"] == 0.0
        assert result["today_revenue"] == 0.0

    def test_today_outstanding_calculation(self):
        """Verify today_outstanding = max(0, today_revenue - today_received)."""
        values = [
            1000.0,  # total_cost
            0.0,  # total_discount
            300.0,  # today_revenue
            500.0,  # total_received
            100.0,  # today_received (less than today_revenue)
            0.0,
            0.0,
            0.0,
            0.0,  # expenses
        ]

        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = self._mock_scalar_sequence(values)
        self.mock_db.query.return_value = mock_query

        result = self.service.get_financial_stats()

        assert result["today_outstanding"] == 200.0  # max(0, 300-100)

    def test_null_values_treated_as_zero(self):
        """Verify NULL database values are converted to 0.0."""
        values = [None, None, None, None, None, None, None, None, None]

        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = self._mock_scalar_sequence(values)
        self.mock_db.query.return_value = mock_query

        result = self.service.get_financial_stats()

        # Should not crash and return zeros
        assert result["total_revenue"] == 0.0
        assert result["net_profit"] == 0.0


class TestBillingServiceCreatePayment:
    """Tests for create_payment() method."""

    def setup_method(self):
        self.mock_db = MagicMock()
        self.tenant_id = 1
        self.service = BillingService(self.mock_db, self.tenant_id)

    def test_create_payment_patient_not_found(self):
        """Verify ValueError raised when patient doesn't exist."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        payment = schemas.PaymentCreate(patient_id=999, amount=100.0, method="cash")

        with pytest.raises(ValueError, match="Patient not found"):
            self.service.create_payment(payment)

    def test_create_payment_wrong_tenant(self):
        """Verify ValueError when patient belongs to different tenant."""
        # Patient exists but with different tenant_id
        wrong_tenant_patient = models.Patient(id=1, tenant_id=999)  # Different tenant
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            None  # Filter blocks it
        )

        payment = schemas.PaymentCreate(patient_id=1, amount=100.0, method="cash")

        with pytest.raises(ValueError, match="Patient not found"):
            self.service.create_payment(payment)
