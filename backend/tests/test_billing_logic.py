"""Billing service unit tests.

Calculation math for tenant-business-day reporting is covered by
``test_dashboard_business_day.py`` against the database. These tests keep the
BillingService public contract focused on orchestration and payment creation.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend import schemas
from backend.services.billing_service import BillingService
from backend.services.tenant_time_service import TenantTimeContext


class TestBillingServiceFinancialStats:
    """Verify BillingService delegates to the authoritative reporting layer."""

    def setup_method(self):
        self.mock_db = MagicMock()
        self.mock_db.execute = AsyncMock()
        self.mock_db.scalar = AsyncMock()
        self.tenant_id = 1
        self.service = BillingService(self.mock_db, self.tenant_id)
        self.context = TenantTimeContext(
            timezone_name="Africa/Cairo",
            business_date=date(2026, 8, 17),
            utc_start=datetime(2026, 8, 16, 21, 0),
            utc_end=datetime(2026, 8, 17, 21, 0),
            local_start=datetime(2026, 8, 17, 0, 0),
            local_end=datetime(2026, 8, 18, 0, 0),
        )

    @pytest.mark.asyncio
    async def test_get_financial_stats_uses_authoritative_reporting_contract(self):
        expected = {
            "total_revenue": 900.0,
            "total_received": 500.0,
            "outstanding": 400.0,
            "total_expenses": 80.0,
            "net_profit": 420.0,
            "monthly_revenue": 0.0,
            "today_revenue": 300.0,
            "today_received": 100.0,
            # This value is deliberately not derived from aggregate subtraction.
            # It represents the shared per-patient debtor calculation.
            "today_outstanding": 175.0,
            "today_expenses": 15.0,
        }

        with (
            patch.object(
                self.service,
                "_get_time_context",
                new=AsyncMock(return_value=self.context),
            ),
            patch(
                "backend.services.billing_service.reporting_crud.get_financial_stats",
                new=AsyncMock(return_value=expected),
            ) as reporting_mock,
        ):
            result = await self.service.get_financial_stats()

        assert result == expected
        reporting_mock.assert_awaited_once_with(
            self.mock_db,
            self.tenant_id,
            timezone_name="Africa/Cairo",
            business_date=date(2026, 8, 17),
            doctor_patient_scope_id=None,
            is_doctor=False,
        )

    @pytest.mark.asyncio
    async def test_get_financial_stats_preserves_doctor_patient_scope(self):
        service = BillingService(
            self.mock_db,
            self.tenant_id,
            doctor_patient_scope_id=42,
            is_doctor=True,
        )
        expected = {
            "total_revenue": 100.0,
            "total_received": 50.0,
            "outstanding": 50.0,
            "total_expenses": 0.0,
            "net_profit": 50.0,
            "monthly_revenue": 0.0,
            "today_revenue": 100.0,
            "today_received": 50.0,
            "today_outstanding": 50.0,
            "today_expenses": 0.0,
        }

        with (
            patch.object(
                service,
                "_get_time_context",
                new=AsyncMock(return_value=self.context),
            ),
            patch(
                "backend.services.billing_service.reporting_crud.get_financial_stats",
                new=AsyncMock(return_value=expected),
            ) as reporting_mock,
        ):
            result = await service.get_financial_stats()

        assert result == expected
        reporting_mock.assert_awaited_once_with(
            self.mock_db,
            self.tenant_id,
            timezone_name="Africa/Cairo",
            business_date=date(2026, 8, 17),
            doctor_patient_scope_id=42,
            is_doctor=True,
        )


class TestBillingServiceCreatePayment:
    """Tests for create_payment() method."""

    def setup_method(self):
        self.mock_db = MagicMock()
        self.mock_db.execute = AsyncMock()
        self.tenant_id = 1
        self.service = BillingService(self.mock_db, self.tenant_id)

    @pytest.mark.asyncio
    async def test_create_payment_patient_not_found(self):
        """Verify ValueError raised when patient doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        self.mock_db.execute.return_value = mock_result

        payment = schemas.PaymentCreate(patient_id=999, amount=100.0, method="cash")

        with pytest.raises(ValueError, match="Patient not found"):
            await self.service.create_payment(payment)

    @pytest.mark.asyncio
    async def test_create_payment_wrong_tenant(self):
        """Verify ValueError when patient belongs to different tenant."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        self.mock_db.execute.return_value = mock_result

        payment = schemas.PaymentCreate(patient_id=1, amount=100.0, method="cash")

        with pytest.raises(ValueError, match="Patient not found"):
            await self.service.create_payment(payment)
