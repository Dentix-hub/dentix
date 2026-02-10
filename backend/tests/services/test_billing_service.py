import pytest
from unittest.mock import Mock, patch
from backend.services.billing_service import BillingService
from backend.schemas.billing import PaymentCreate
from backend.models import Patient


@pytest.fixture
def mock_db_session():
    """Mocks the SQLAlchemy database session."""
    session = Mock()
    session.query.return_value = session.query
    session.filter.return_value = session.filter
    session.join.return_value = session.join
    session.scalar.return_value = 0.0
    session.first.return_value = None
    return session


@pytest.fixture
def billing_service(mock_db_session):
    return BillingService(db=mock_db_session, tenant_id=1)


def test_create_payment_success(billing_service, mock_db_session):
    """Test successful payment creation."""
    # Setup
    payment_data = PaymentCreate(patient_id=1, amount=100.0, method="cash")
    mock_patient = Patient(id=1, tenant_id=1)

    # Mock patient search
    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        mock_patient
    )

    # Mock crud
    with patch("backend.services.billing_service.billing_crud") as mock_crud:
        mock_crud.create_payment.return_value = {"id": 1, "status": "success"}

        # Act
        result = billing_service.create_payment(payment_data, doctor_id=10)

        # Assert
        assert result == {"id": 1, "status": "success"}
        mock_crud.create_payment.assert_called_once()


def test_create_payment_patient_not_found(billing_service, mock_db_session):
    """Test payment creation for non-existent patient."""
    # Setup
    payment_data = PaymentCreate(patient_id=999, amount=100.0)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="Patient not found"):
        billing_service.create_payment(payment_data)


def test_get_outstanding_balance_calculation(billing_service, mock_db_session):
    """Test outstanding balance logic."""
    # Setup
    # Mocking _scalar returns for revenue and payments
    # First call: Revenue, Second call: Payments
    billing_service._scalar = Mock(side_effect=[500.0, 200.0])

    # Act
    balance = billing_service.get_outstanding_balance(patient_id=1)

    # Assert
    assert balance == 300.0  # 500 - 200
    assert billing_service._scalar.call_count == 2
