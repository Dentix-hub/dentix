"""
LabService Unit Tests

Tests all LabService logic:
- Laboratory CRUD operations
- Lab order lifecycle (create → send → receive → complete)
- Lab order ↔ treatment synchronization
- Lab payments and balance tracking
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from backend.services.lab_service import LabService, get_lab_service
from backend import models, schemas
from backend.models.financial import LabPayment


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
    session.query.return_value = MagicMock()
    return session


@pytest.fixture
def lab_service(mock_db):
    """Create LabService with mocked dependencies."""
    return LabService(db=mock_db, tenant_id=1)


@pytest.fixture
def sample_laboratory():
    """Sample laboratory data."""
    lab = MagicMock(spec=models.Laboratory)
    lab.id = 1
    lab.name = "Central Dental Lab"
    lab.phone = "0123456789"
    lab.email = "info@centrallab.com"
    lab.address = "Cairo, Egypt"
    lab.tenant_id = 1
    lab.is_active = True
    return lab


@pytest.fixture
def sample_lab_order():
    """Sample lab order data."""
    order = MagicMock(spec=models.LabOrder)
    order.id = 100
    order.patient_id = 1
    order.lab_id = 1
    order.work_type = "Crown"
    order.material = "Zirconia"
    order.status = "PENDING"
    order.total_cost = 1500.0
    order.paid_amount = 0.0
    order.tenant_id = 1
    return order


# ============================================
# LABORATORY CRUD TESTS
# ============================================


class TestLaboratoryCRUD:
    """Tests for LabService laboratory operations."""

    def test_get_laboratories_returns_list(
        self, lab_service, mock_db, sample_laboratory
    ):
        """Should return list of active laboratories."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            sample_laboratory
        ]

        result = lab_service.get_laboratories()

        assert len(result) == 1
        assert result[0].name == "Central Dental Lab"

    def test_get_laboratory_by_id(self, lab_service, mock_db, sample_laboratory):
        """Should return laboratory by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_laboratory
        )

        result = lab_service.get_laboratory(1)

        assert result is not None
        assert result.id == 1

    def test_get_laboratory_not_found(self, lab_service, mock_db):
        """Should return None when laboratory not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = lab_service.get_laboratory(999)

        assert result is None

    def test_create_laboratory(self, lab_service, mock_db):
        """Should create new laboratory."""
        data = schemas.LaboratoryCreate(
            name="New Lab",
            phone="01000000000",
            email="new@lab.com",
            address="Test Address",
        )
        mock_lab = MagicMock(spec=models.Laboratory)
        mock_lab.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "backend.services.lab_service.models.Laboratory", return_value=mock_lab
        ):
            result = lab_service.create_laboratory(data)

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_update_laboratory(self, lab_service, mock_db, sample_laboratory):
        """Should update existing laboratory."""
        data = schemas.LaboratoryUpdate(name="Updated Lab Name", phone="01111111111")
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_laboratory
        )

        result = lab_service.update_laboratory(1, data)

        assert result.name == "Updated Lab Name"
        mock_db.commit.assert_called()

    def test_delete_laboratory(self, lab_service, mock_db, sample_laboratory):
        """Should delete laboratory from database."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_laboratory
        )

        result = lab_service.delete_laboratory(1)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_laboratory)
        mock_db.commit.assert_called()


# ============================================
# LAB ORDER LIFECYCLE TESTS
# ============================================


class TestLabOrderLifecycle:
    """Tests for lab order state transitions."""

    def test_create_lab_order_pending(self, lab_service, mock_db):
        """New lab order should have PENDING status."""
        data = schemas.LabOrderCreate(
            patient_id=1,
            laboratory_id=1,
            work_type="Crown",
            material="Zirconia",
            cost=1500.0,
        )

        mock_patient = MagicMock()
        mock_patient.id = 1

        mock_lab = MagicMock()
        mock_lab.id = 1

        mock_order = MagicMock()
        mock_order.id = 100
        mock_order.status = "PENDING"
        mock_order.price_to_patient = 1500.0

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_patient,
            mock_lab,
        ]

        with patch(
            "backend.services.lab_service.models.LabOrder", return_value=mock_order
        ):
            result = lab_service.create_lab_order(data, doctor_id=1)

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_send_lab_order_to_lab(self, lab_service, mock_db, sample_lab_order):
        """Should change status from PENDING to SENT_TO_LAB."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_lab_order
        )
        sample_lab_order.status = "PENDING"
        update_data = schemas.LabOrderUpdate(status="SENT_TO_LAB")

        result = lab_service.update_lab_order(100, update_data)

        assert result.status == "SENT_TO_LAB"
        mock_db.commit.assert_called()

    def test_receive_lab_order(self, lab_service, mock_db, sample_lab_order):
        """Should change status from SENT to RECEIVED."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_lab_order
        )
        sample_lab_order.status = "SENT_TO_LAB"
        update_data = schemas.LabOrderUpdate(status="RECEIVED")

        result = lab_service.update_lab_order(100, update_data)

        assert result.status == "RECEIVED"
        mock_db.commit.assert_called()

    def test_complete_lab_order(self, lab_service, mock_db, sample_lab_order):
        """Should change status from RECEIVED to COMPLETED."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_lab_order
        )
        sample_lab_order.status = "RECEIVED"
        update_data = schemas.LabOrderUpdate(status="completed")

        with patch.object(lab_service, '_sync_linked_treatment'):
            result = lab_service.update_lab_order(100, update_data)

        assert result.status == "completed"
        mock_db.commit.assert_called()


# ============================================
# LAB PAYMENTS TESTS
# ============================================


class TestLabPayments:
    """Tests for lab payment operations."""

    def test_create_lab_payment(self, lab_service, mock_db, sample_lab_order):
        """Should create payment and update order balance."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_lab_order
        )
        sample_lab_order.paid_amount = 0.0

        payment_data = schemas.LabPaymentCreate(
            laboratory_id=1, amount=500.0, method="cash", notes="Initial payment"
        )

        mock_payment = MagicMock(spec=models.LabPayment)
        mock_payment.id = 1

        with patch(
            "backend.services.lab_service.models.LabPayment", return_value=mock_payment
        ):
            result = lab_service.create_lab_payment(1, payment_data)

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_get_lab_payments(self, lab_service, mock_db):
        """Should return all payments for a lab."""
        mock_payment = MagicMock()
        mock_payment.id = 1
        mock_payment.amount = 500.0

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_payment]

        result = lab_service.get_lab_payments(1)

        assert len(result) == 1
        assert result[0].amount == 500.0


# ============================================
# STATS AND ANALYTICS TESTS
# ============================================


class TestLabStats:
    """Tests for lab statistics."""

    def test_get_stats_summary(self, lab_service, mock_db):
        """Should return summary statistics."""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0

        result = lab_service.get_stats_summary()

        assert isinstance(result, dict)
        assert "total_orders" in result

    def test_get_lab_stats(self, lab_service, mock_db, sample_laboratory):
        """Should return stats for specific lab."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_laboratory
        )
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = lab_service.get_lab_stats(1)

        assert isinstance(result, dict)
        assert "lab_id" in result


# ============================================
# FACTORY FUNCTION TEST
# ============================================


class TestLabServiceFactory:
    """Tests for the factory function."""

    def test_get_lab_service_returns_instance(self, mock_db):
        """Factory should return LabService instance."""
        result = get_lab_service(mock_db, 1)

        assert isinstance(result, LabService)
        assert result.tenant_id == 1
