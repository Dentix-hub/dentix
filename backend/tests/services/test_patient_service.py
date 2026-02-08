
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from backend.services.patient_service import PatientService
from backend.schemas.patient import PatientCreate, PatientUpdate
from backend.models.patient import Patient

@pytest.fixture
def mock_db_session():
    """Mocks the SQLAlchemy database session."""
    session = Mock()
    session.query.return_value = session.query
    session.filter.return_value = session.filter
    session.first.return_value = None
    session.all.return_value = []
    session.add.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None
    return session

@pytest.fixture
def mock_policy_engine():
    """Mocks the policy engine to bypass permission checks."""
    with patch("backend.services.patient_service.policy_engine") as mock:
        mock.check_permission.return_value = True
        mock.get_policy.return_value = Mock(allowed_fields=None)
        yield mock

@pytest.fixture
def patient_service(mock_db_session):
    """Returns an instance of PatientService with mocked DB."""
    return PatientService(db=mock_db_session, tenant_id=1)

def test_create_patient_success(patient_service, mock_db_session, mock_policy_engine):
    """Test successful patient creation."""
    # Setup
    patient_data = PatientCreate(
        name="John Doe",
        phone="1234567890",
        age=30,
        address="123 Main St",
        medical_history="None"
    )
    
    # Mocking existing check to return None (no duplicate)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    result = patient_service.create_patient(patient_data, creator_role="doctor")
    
    # Assert
    assert result.name == "John Doe"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_create_patient_duplicate(patient_service, mock_db_session, mock_policy_engine):
    """Test error when creating a duplicate patient."""
    # Setup
    patient_data = PatientCreate(name="Jane Doe", phone="9876543210")
    
    # Mocking existing check to return a patient (duplicate found)
    mock_db_session.query.return_value.filter.return_value.first.return_value = Patient(id=1, name="Jane Doe")
    
    # Act & Assert
    with pytest.raises(ValueError, match="already exists"):
        patient_service.create_patient(patient_data, creator_role="doctor")

def test_get_patient_found(patient_service, mock_db_session):
    """Test retrieving an existing patient."""
    # Setup
    mock_patient = Patient(id=1, name="Alice", tenant_id=1)
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_patient
    
    # Act
    result = patient_service.get_patient(patient_id=1)
    
    # Assert
    assert result == mock_patient
    assert result.name == "Alice"

def test_get_patient_not_found(patient_service, mock_db_session):
    """Test retrieving a non-existent patient."""
    # Setup
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Act
    result = patient_service.get_patient(patient_id=999)
    
    # Assert
    assert result is None

def test_update_patient_success(patient_service, mock_db_session, mock_policy_engine):
    """Test successful patient update."""
    # Setup
    update_data = PatientUpdate(name="Bob Updated")
    existing_patient = Patient(id=1, name="Bob", tenant_id=1)
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_patient
    
    # Act
    result = patient_service.update_patient(patient_id=1, updates=update_data, updater_role="doctor")
    
    # Assert
    assert existing_patient.name == "Bob Updated"
    mock_db_session.commit.assert_called_once()    
