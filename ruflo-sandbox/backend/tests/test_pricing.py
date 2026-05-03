"""
Tests for Multi Price List System

Test Scenarios:
1. Procedure price lookup (Cash vs Insurance)
2. Treatment pricing application (Snapshot)
3. Insurance share calculation
4. Admin vs Doctor access to price lists
5. AI Context restrictions
"""

from unittest.mock import MagicMock, patch
from backend.models import Treatment
from backend.services.pricing_service import PricingService
from backend.services.ai.ai_price_context import AIPriceContext


class TestPricingService:
    """Tests for PricingService business logic."""

    def test_get_procedure_price_priority(self):
        """Should prioritize PriceListItem over Procedure.price."""
        # Setup
        mock_db = MagicMock()
        mock_tenant_id = 1
        service = PricingService(mock_db, mock_tenant_id)

        # Mock item in list
        mock_item = MagicMock()
        mock_item.final_price = 450.0  # Insurance price

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        # Test
        price = service.get_procedure_price(procedure_id=1, price_list_id=10)
        assert price == 450.0

    def test_fallback_to_default_list(self):
        """Should fallback to Default List if not in specific list."""
        # Setup
        mock_db = MagicMock()
        mock_tenant_id = 1
        service = PricingService(mock_db, mock_tenant_id)

        # Specific list returns None
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,
            MagicMock(final_price=500.0),
        ]

        # Mock default list
        mock_default = MagicMock()
        mock_default.id = 99
        service.get_default_price_list = MagicMock(return_value=mock_default)

        # Test
        price = service.get_procedure_price(procedure_id=1, price_list_id=10)
        assert price == 500.0

    def test_apply_price_to_treatment_snapshot(self):
        """Should create JSON snapshot in treatment."""
        # Setup
        mock_db = MagicMock()
        mock_tenant_id = 1
        service = PricingService(mock_db, mock_tenant_id)

        treatment = Treatment()
        treatment.discount = 0.0

        # Mock price lookup
        service.get_procedure_price = MagicMock(return_value=1000.0)

        # Mock price list
        mock_list = MagicMock()
        mock_list.name = "Test List"
        mock_list.type = "cash"
        service.get_price_list = MagicMock(return_value=mock_list)

        # Test
        updated_treatment = service.apply_price_to_treatment(
            treatment, price_list_id=5, procedure_id=1
        )

        assert updated_treatment.unit_price == 1000.0
        assert updated_treatment.cost == 1000.0
        assert '"unit_price": 1000.0' in updated_treatment.price_snapshot
        assert '"list_name": "Test List"' in updated_treatment.price_snapshot

    def test_insurance_share_calculation(self):
        """Should calculate insurance vs patient share correctly."""
        service = PricingService(MagicMock(), 1)

        price_list = MagicMock()
        price_list.type = "insurance"
        price_list.coverage_percent = 80.0
        price_list.copay_percent = 20.0
        price_list.copay_fixed = 0.0

        share = service.calculate_patient_share(total=1000.0, price_list=price_list)

        assert share["total"] == 1000.0
        assert share["insurance_pays"] == 800.0
        assert share["patient_pays"] == 200.0


class TestAIPriceContext:
    """Tests for AI security context."""

    def test_admin_sees_all_lists(self):
        mock_db = MagicMock()
        user = MagicMock(role="admin", id=1)

        context = AIPriceContext.from_user(mock_db, user, 1)
        assert context.can_compare_prices
        assert context.can_access_price_list(999)

    def test_doctor_restricted_access(self):
        """Doctor should verify allowed lists."""
        mock_db = MagicMock()
        user = MagicMock(role="doctor", id=2)

        # Mock available lists
        pl1 = MagicMock(id=10)
        pl2 = MagicMock(id=11)

        with patch(
            "backend.services.pricing_service.PricingService.get_available_price_lists",
            return_value=[pl1, pl2],
        ):
            context = AIPriceContext.from_user(mock_db, user, 1)

            assert not context.can_compare_prices
            assert context.can_access_price_list(10)
            assert not context.can_access_price_list(99)

    def test_system_prompt_injection(self):
        """System prompt should contain mandatory rules."""
        context = AIPriceContext(
            user_id=1, user_role="doctor", tenant_id=1, allowed_price_list_ids={1}
        )
        prompt = context.get_system_prompt_rules()
        assert "PRICING RULES" in prompt
        assert "NEVER compare prices" in prompt
        assert "RESTRICTED" in prompt
