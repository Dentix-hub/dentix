"""
C6.2 — TreatmentService Unit Tests

Tests all TreatmentService logic:
- Treatment creation (with pricing + stock)
- Treatment update
- Treatment deletion
- Stock validation and consumption
- Price snapshot generation
- Edge cases and error handling
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.treatment_service import TreatmentService, get_treatment_service
from backend.services.pricing_service import PricingService
from backend import models, schemas


# ============================================
# FIXTURES
# ============================================


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.flush = MagicMock()
    session.refresh = MagicMock()
    session.rollback = MagicMock()

    # Chainable query mock
    query = MagicMock()
    session.query.return_value = query
    query.filter.return_value = query
    query.join.return_value = query
    query.options.return_value = query
    query.order_by.return_value = query
    query.first.return_value = None
    query.all.return_value = []
    
    return session


@pytest.fixture
def mock_user():
    """Mock authenticated user (doctor)."""
    user = MagicMock(spec=models.User)
    user.id = 10
    user.tenant_id = 1
    user.role = "doctor"
    user.username = "dr_test"
    return user


@pytest.fixture
def treatment_service(mock_db, mock_user):
    """Create TreatmentService with mocked dependencies."""
    with patch(
        "backend.services.treatment_service.get_pricing_service"
    ) as mock_pricing_factory:
        class MockPriceList:
            def __init__(self, name, pl_type):
                self.name = name
                self.type = pl_type

        mock_pricing = MagicMock(spec=PricingService)
        mock_pricing.get_procedure_price.return_value = 500.0
        mock_pricing.get_price_list.return_value = MockPriceList("Cash", "cash")
        mock_pricing_factory.return_value = mock_pricing

        svc = TreatmentService(mock_db, tenant_id=1, current_user=mock_user)
        svc.pricing = mock_pricing
        yield svc


@pytest.fixture
def sample_treatment_data():
    """Sample treatment creation payload."""
    return schemas.TreatmentCreate(
        patient_id=1,
        procedure="Composite Filling",
        cost=500.0,
        diagnosis="Caries",
        notes="Mesial surface",
        consumedMaterials=None,
    )


@pytest.fixture
def sample_treatment_with_materials():
    """Treatment with consumed materials."""
    return schemas.TreatmentCreate(
        patient_id=1,
        procedure="Root Canal",
        cost=2000.0,
        diagnosis="Irreversible Pulpitis",
        consumedMaterials=[
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0),
            schemas.clinical.ConsumedMaterialItem(material_id=2, quantity=0.5),
        ],
    )


# ============================================
# CREATION TESTS
# ============================================


class TestTreatmentCreation:
    """Tests for TreatmentService.create_treatment."""

    def test_create_basic_treatment(self, treatment_service, sample_treatment_data, mock_db):
        """Basic treatment creation without stock."""
        # Arrange
        mock_patient = MagicMock(spec=models.Patient)
        mock_patient.id = 1
        mock_patient.default_price_list_id = None

        mock_treatment = MagicMock(spec=models.Treatment)
        mock_treatment.id = 100
        mock_treatment.procedure = "Composite Filling"

        with patch("backend.crud") as mock_crud:
            mock_crud.get_patient.return_value = mock_patient
            mock_crud.create_treatment.return_value = mock_treatment

            # Act
            result = treatment_service.create_treatment(sample_treatment_data)

            # Assert
            assert result.id == 100
            mock_crud.get_patient.assert_called_once_with(mock_db, 1, 1)
            mock_crud.create_treatment.assert_called_once()

    def test_create_treatment_patient_not_found(self, treatment_service, sample_treatment_data):
        """Must raise 404 if patient does not exist."""
        from fastapi import HTTPException

        with patch("backend.crud") as mock_crud:
            mock_crud.get_patient.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                treatment_service.create_treatment(sample_treatment_data)

            assert exc_info.value.status_code == 404
            assert "Patient not found" in str(exc_info.value.detail)

    def test_create_treatment_auto_assigns_doctor(
        self, treatment_service, mock_db, mock_user
    ):
        """Doctor ID should default to current user if not provided."""
        data = schemas.TreatmentCreate(
            patient_id=1,
            procedure="Scaling",
            cost=300.0,
            doctor_id=None,
        )

        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=101)

        with patch("backend.crud") as mock_crud:
            mock_crud.get_patient.return_value = mock_patient
            mock_crud.create_treatment.return_value = mock_treatment

            treatment_service.create_treatment(data)

            # Verify doctor_id was set to current user
            call_kwargs = mock_crud.create_treatment.call_args
            assert call_kwargs.kwargs["doctor_id"] == mock_user.id

    def test_create_treatment_commits_transaction(
        self, treatment_service, sample_treatment_data, mock_db
    ):
        """Treatment creation must commit the DB transaction."""
        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=102)

        with patch("backend.crud") as mock_crud:
            mock_crud.get_patient.return_value = mock_patient
            mock_crud.create_treatment.return_value = mock_treatment

            treatment_service.create_treatment(sample_treatment_data)

            mock_db.commit.assert_called()
            mock_db.refresh.assert_called_with(mock_treatment)

    def test_create_treatment_deferred_commit(
        self, treatment_service, sample_treatment_data, mock_db
    ):
        """Treatment must be created with commit=False for transactional safety."""
        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=103)

        with patch("backend.crud") as mock_crud:
            mock_crud.get_patient.return_value = mock_patient
            mock_crud.create_treatment.return_value = mock_treatment

            treatment_service.create_treatment(sample_treatment_data)

            call_kwargs = mock_crud.create_treatment.call_args
            assert call_kwargs.kwargs["commit"] is False


# ============================================
# STOCK VALIDATION TESTS
# ============================================


class TestStockValidation:
    """Tests for TreatmentService stock validation."""

    def test_validate_empty_materials_passes(self, treatment_service):
        """Empty materials list should pass validation silently."""
        treatment_service.validate_treatment_stock([])

    def test_validate_sufficient_stock(self, treatment_service):
        """Validation passes when stock is available."""
        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock.return_value = (True, 10.0, "Composite A2")

            treatment_service.validate_treatment_stock(materials)
            mock_inv.validate_stock.assert_called_once()

    def test_validate_insufficient_stock_raises(self, treatment_service):
        """Must raise 400 with details when stock is insufficient."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=100.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock.return_value = (False, 5.0, "Composite A2")

            with pytest.raises(HTTPException) as exc_info:
                treatment_service.validate_treatment_stock(materials)

            assert exc_info.value.status_code == 400
            assert "Composite A2" in str(exc_info.value.detail)

    def test_validate_stock_internal_error(self, treatment_service):
        """Internal stock error should raise 500."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=99, quantity=1.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock.side_effect = Exception("DB connection lost")

            with pytest.raises(HTTPException) as exc_info:
                treatment_service.validate_treatment_stock(materials)

            assert exc_info.value.status_code == 500


# ============================================
# STOCK CONSUMPTION TESTS
# ============================================


class TestStockConsumption:
    """Tests for TreatmentService.consume_treatment_stock."""

    def test_consume_empty_list_noop(self, treatment_service):
        """Empty materials list is a no-op."""
        treatment_service.consume_treatment_stock(treatment_id=1, consumed_materials=[])

    def test_consume_stock_success(self, treatment_service, mock_user):
        """Stock consumption should call inventory service correctly."""
        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            treatment_service.consume_treatment_stock(
                treatment_id=50, consumed_materials=materials
            )

            mock_inv.consume_stock.assert_called_once_with(
                material_id=1,
                quantity=2.0,
                tenant_id=1,
                user_id=mock_user.id,
                reference_id="TREATMENT:50",
                db=treatment_service.db,
            )

    def test_consume_stock_confirm_open_required(self, treatment_service):
        """CONFIRM_OPEN_REQUIRED error should raise 409 with structured data."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=1.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.consume_stock.side_effect = Exception(
                "CONFIRM_OPEN_REQUIRED:42:Composite A2 (4g)"
            )

            with pytest.raises(HTTPException) as exc_info:
                treatment_service.consume_treatment_stock(
                    treatment_id=50, consumed_materials=materials
                )

            assert exc_info.value.status_code == 409
            detail = exc_info.value.detail
            assert detail["code"] == "CONFIRM_OPEN_REQUIRED"
            assert detail["stock_item_id"] == 42


# ============================================
# UPDATE & DELETE TESTS
# ============================================


class TestTreatmentUpdate:
    """Tests for TreatmentService.update_treatment."""

    def test_update_treatment_basic(self, treatment_service, sample_treatment_data, mock_db):
        """Basic treatment update."""
        mock_updated = MagicMock(spec=models.Treatment)
        mock_updated.id = 100

        with patch("backend.crud") as mock_crud:
            mock_crud.update_treatment.return_value = mock_updated

            result = treatment_service.update_treatment(100, sample_treatment_data)

            assert result.id == 100
            mock_db.commit.assert_called()

    def test_update_treatment_validates_stock_first(
        self, treatment_service, sample_treatment_with_materials
    ):
        """Stock validation must happen before DB update."""
        with patch("backend.crud") as mock_crud:
            mock_crud.update_treatment.return_value = MagicMock(id=100)

            with patch.object(
                treatment_service, "validate_treatment_stock"
            ) as mock_validate, patch.object(
                treatment_service, "consume_treatment_stock"
            ) as mock_consume:
                treatment_service.update_treatment(
                    100, sample_treatment_with_materials
                )

                mock_validate.assert_called_once()
                mock_consume.assert_called_once()


class TestTreatmentDelete:
    """Tests for TreatmentService.delete_treatment."""

    def test_delete_treatment_basic(self, treatment_service, mock_db):
        """Delete calls crud and logs admin action."""
        with patch("backend.crud") as mock_crud:
            mock_crud.delete_treatment.return_value = True

            with patch(
                "backend.services.treatment_service.log_admin_action"
            ) as mock_log:
                treatment_service.delete_treatment(100)

                mock_crud.delete_treatment.assert_called_once_with(mock_db, 100, 1)
                mock_log.assert_called_once()


# ============================================
# PRICING INTEGRATION
# ============================================


class TestTreatmentPricing:
    """Tests for price calculation and snapshot in create_treatment."""

    def test_price_snapshot_created_on_creation(self, treatment_service, mock_db):
        """Treatment creation should generate a price snapshot."""
        data = schemas.TreatmentCreate(
            patient_id=1,
            procedure="Crown Prep",
            cost=3000.0,
        )

        mock_patient = MagicMock(default_price_list_id=5)
        mock_treatment = MagicMock(id=200)

        with patch("backend.crud") as mock_crud:
            mock_crud.get_patient.return_value = mock_patient
            mock_crud.create_treatment.return_value = mock_treatment

            treatment_service.create_treatment(data)

            call_kwargs = mock_crud.create_treatment.call_args
            assert call_kwargs.kwargs["unit_price"] is not None


# ============================================
# FACTORY FUNCTION
# ============================================


class TestTreatmentServiceFactory:
    """Tests for the factory function."""

    def test_get_treatment_service_returns_instance(self):
        """Factory should return a TreatmentService instance."""
        mock_db = MagicMock()
        mock_user = MagicMock(spec=models.User)
        mock_user.tenant_id = 1

        with patch(
            "backend.services.treatment_service.get_pricing_service"
        ):
            svc = get_treatment_service(mock_db, 1, mock_user)
            assert isinstance(svc, TreatmentService)
            assert svc.tenant_id == 1
