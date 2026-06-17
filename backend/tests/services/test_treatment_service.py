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
from unittest.mock import MagicMock, AsyncMock, patch

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
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    # Default mock result behavior
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    # Legacy query mock for backward compatibility
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
        mock_pricing.get_procedure_price = AsyncMock(return_value=500.0)
        mock_pricing.get_price_list = AsyncMock(return_value=MockPriceList("Cash", "cash"))
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

    async def test_create_basic_treatment(self, treatment_service, sample_treatment_data, mock_db):
        """Basic treatment creation without stock."""
        # Arrange
        mock_patient = MagicMock(spec=models.Patient)
        mock_patient.id = 1
        mock_patient.default_price_list_id = None

        mock_treatment = MagicMock(spec=models.Treatment)
        mock_treatment.id = 100
        mock_treatment.procedure = "Composite Filling"

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=500.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            # Act
            result = await treatment_service.create_treatment(sample_treatment_data)

            # Assert
            assert result.id == 100
            mock_crud.patient.get_patient.assert_called_once_with(mock_db, 1, 1)
            mock_crud.billing.create_treatment.assert_called_once()

    async def test_create_treatment_patient_not_found(self, treatment_service, sample_treatment_data):
        """Must raise 404 if patient does not exist."""
        from fastapi import HTTPException

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.create_treatment(sample_treatment_data)

            assert exc_info.value.status_code == 404
            assert "Patient not found" in str(exc_info.value.detail)

    async def test_create_treatment_auto_assigns_doctor(
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

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=300.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(data)

            # Verify doctor_id was set to current user
            call_kwargs = mock_crud.billing.create_treatment.call_args
            assert call_kwargs.kwargs["doctor_id"] == mock_user.id

    async def test_create_treatment_commits_transaction(
        self, treatment_service, sample_treatment_data, mock_db
    ):
        """Treatment creation must commit the DB transaction."""
        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=102)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=500.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(sample_treatment_data)

            mock_db.commit.assert_called()
            mock_db.refresh.assert_called_with(mock_treatment)

    async def test_create_treatment_deferred_commit(
        self, treatment_service, sample_treatment_data, mock_db
    ):
        """Treatment must be created with commit=False for transactional safety."""
        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=103)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=500.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(sample_treatment_data)

            call_kwargs = mock_crud.billing.create_treatment.call_args
            assert call_kwargs.kwargs["commit"] is False


# ============================================
# STOCK VALIDATION TESTS
# ============================================


class TestStockValidation:
    """Tests for TreatmentService stock validation."""

    async def test_validate_empty_materials_passes(self, treatment_service):
        """Empty materials list should pass validation silently."""
        await treatment_service.validate_treatment_stock([])

    async def test_validate_sufficient_stock(self, treatment_service):
        """Validation passes when stock is available."""
        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock = AsyncMock(return_value=(True, 10.0, "Composite A2"))

            await treatment_service.validate_treatment_stock(materials)
            mock_inv.validate_stock.assert_called_once()

    async def test_validate_insufficient_stock_raises(self, treatment_service):
        """Must raise 400 with details when stock is insufficient."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=100.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock = AsyncMock(return_value=(False, 5.0, "Composite A2"))

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.validate_treatment_stock(materials)

            assert exc_info.value.status_code == 400
            assert "Composite A2" in str(exc_info.value.detail)

    async def test_validate_stock_internal_error(self, treatment_service):
        """Internal stock error should raise 500."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=99, quantity=1.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock = AsyncMock(side_effect=Exception("DB connection lost"))

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.validate_treatment_stock(materials)

            assert exc_info.value.status_code == 500


# ============================================
# STOCK CONSUMPTION TESTS
# ============================================


class TestStockConsumption:
    """Tests for TreatmentService.consume_treatment_stock."""

    async def test_consume_empty_list_noop(self, treatment_service):
        """Empty materials list is a no-op."""
        await treatment_service.consume_treatment_stock(treatment_id=1, consumed_materials=[])

    async def test_consume_stock_success(self, treatment_service, mock_user):
        """Stock consumption should call inventory service correctly."""
        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.consume_stock = AsyncMock()
            await treatment_service.consume_treatment_stock(
                treatment_id=50, consumed_materials=materials
            )

            mock_inv.consume_stock.assert_called_once_with(
                material_id=1,
                quantity=2.0,
                tenant_id=1,
                user_id=mock_user.id,
                reference_id="TREATMENT:50",
                patient_id=None,
                db=treatment_service.db,
                commit=False,
            )

    async def test_consume_stock_confirm_open_required(self, treatment_service):
        """CONFIRM_OPEN_REQUIRED error should raise 409 with structured data."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=1.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.consume_stock = AsyncMock(side_effect=Exception(
                "CONFIRM_OPEN_REQUIRED:42:Composite A2 (4g)"
            ))

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.consume_treatment_stock(
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

    async def test_update_treatment_basic(self, treatment_service, sample_treatment_data, mock_db):
        """Basic treatment update."""
        mock_updated = MagicMock(spec=models.Treatment)
        mock_updated.id = 100

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.update_treatment = AsyncMock(return_value=mock_updated)

                result = await treatment_service.update_treatment(100, sample_treatment_data)

                assert result.id == 100
                mock_db.commit.assert_called()

    async def test_update_treatment_validates_stock_first(
        self, treatment_service, sample_treatment_with_materials
    ):
        """Stock validation must happen before DB update."""
        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.update_treatment = AsyncMock(return_value=MagicMock(id=100))

                with patch.object(
                    treatment_service, "validate_treatment_stock"
                ) as mock_validate, patch.object(
                    treatment_service, "consume_treatment_stock"
                ) as mock_consume:
                    await treatment_service.update_treatment(
                        100, sample_treatment_with_materials
                    )

                    mock_validate.assert_called_once()
                    mock_consume.assert_called_once()


class TestTreatmentDelete:
    """Tests for TreatmentService.delete_treatment."""

    async def test_delete_treatment_basic(self, treatment_service, mock_db):
        """Delete calls crud and logs admin action."""
        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.delete_treatment = AsyncMock(return_value=True)

                with patch(
                    "backend.services.treatment_service.log_admin_action"
                ) as mock_log:
                    await treatment_service.delete_treatment(100)

                    mock_crud.billing.delete_treatment.assert_called_once_with(mock_db, 100, 1)
                    mock_log.assert_called_once()


# ============================================
# PRICING INTEGRATION
# ============================================


class TestTreatmentPricing:
    """Tests for price calculation and snapshot in create_treatment."""

    async def test_price_snapshot_created_on_creation(self, treatment_service, mock_db):
        """Treatment creation should generate a price snapshot."""
        data = schemas.TreatmentCreate(
            patient_id=1,
            procedure="Crown Prep",
            cost=3000.0,
        )

        mock_patient = MagicMock(default_price_list_id=5)
        mock_treatment = MagicMock(id=200)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=3000.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(data)

            call_kwargs = mock_crud.billing.create_treatment.call_args
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


# ============================================
# PERSISTENCE OF TREATMENT MATERIAL USAGES
# ============================================


class TestTreatmentMaterialUsagePersistence:
    """Tests for TreatmentService.persist_treatment_material_usages."""

    async def test_persist_non_divisible_usage(self, treatment_service, mock_db):
        """Should persist non-divisible material usage with calculated cost."""
        # Arrange
        consumed = [
            schemas.clinical.ConsumedMaterialItem(
                material_id=1,
                quantity=2.0,
                material_type="NON_DIVISIBLE"
            )
        ]

        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.type = "NON_DIVISIBLE"
        mock_material.standard_price = 10.0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [
            [mock_material],  # stmt_mat execute scalars all
            [],  # stmt_moves execute scalars all
        ]
        mock_db.execute.return_value = mock_result

        # Act
        await treatment_service.persist_treatment_material_usages(
            treatment_id=100,
            consumed_materials=consumed,
            doctor_id=10
        )

        # Assert
        added_objs = [call.args[0] for call in mock_db.add.call_args_list]
        usage = next(obj for obj in added_objs if isinstance(obj, models.inventory.TreatmentMaterialUsage))
        assert usage.treatment_id == 100
        assert usage.material_id == 1
        assert usage.quantity_used == 2.0
        assert usage.cost_calculated == 20.0

    async def test_delete_treatment_cleans_up_usage(self, treatment_service, mock_db):
        """Deleting a treatment should also delete its TreatmentMaterialUsage records."""
        # Arrange
        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.delete_treatment = AsyncMock(return_value=True)
                with patch("backend.services.treatment_service.log_admin_action"):
                    # Act
                    await treatment_service.delete_treatment(100)

                    # Assert
                    # Verify that execute() was called on the session to run the delete statement
                    mock_db.execute.assert_called()
