import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.patient_service import PatientService
from backend.schemas.patient import PatientCreate, PatientUpdate
from backend.models.patient import Patient


@pytest.fixture
def mock_db_session():
    """Mocks the SQLAlchemy database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    # Default mock result behavior
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_policy_engine():
    """Mocks the policy engine to bypass permission checks."""
    with patch("backend.services.patient_service.policy_engine") as mock:
        mock.check_permission.return_value = True
        mock.get_policy.return_value = MagicMock(allowed_fields=None)
        yield mock


@pytest.fixture
def patient_service(mock_db_session):
    """Returns an instance of PatientService with mocked DB."""
    return PatientService(db=mock_db_session, tenant_id=1)


async def test_create_patient_success(patient_service, mock_db_session, mock_policy_engine):
    """Test successful patient creation."""
    # Setup
    patient_data = PatientCreate(
        name="John Doe",
        phone="1234567890",
        age=30,
        address="123 Main St",
        medical_history="None",
    )

    # Mocking existing check to return None (no duplicate)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await patient_service.create_patient(patient_data, creator_role="doctor")

    # Assert
    assert result.name == "John Doe"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


async def test_create_patient_duplicate(patient_service, mock_db_session, mock_policy_engine):
    """Test error when creating a duplicate patient."""
    # Setup
    patient_data = PatientCreate(name="Jane Doe", phone="9876543210")

    # Mocking existing check to return a patient (duplicate found)
    mock_patient = Patient(id=1, name="Jane Doe")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_patient]
    mock_db_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(ValueError, match="already exists"):
        await patient_service.create_patient(patient_data, creator_role="doctor")


async def test_get_patient_found(patient_service, mock_db_session):
    """Test retrieving an existing patient."""
    # Setup
    mock_patient = Patient(id=1, name="Alice", tenant_id=1)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_patient
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await patient_service.get_patient(patient_id=1)

    # Assert
    assert result == mock_patient
    assert result.name == "Alice"


async def test_get_patient_not_found(patient_service, mock_db_session):
    """Test retrieving a non-existent patient."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await patient_service.get_patient(patient_id=999)

    # Assert
    assert result is None


async def test_update_patient_success(patient_service, mock_db_session, mock_policy_engine):
    """Test successful patient update."""
    # Setup
    update_data = PatientUpdate(name="Bob Updated")
    existing_patient = Patient(id=1, name="Bob", tenant_id=1)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_patient
    mock_db_session.execute.return_value = mock_result

    mock_policy_engine.get_policy.return_value = MagicMock(allowed_fields=["name"])

    # Act
    await patient_service.update_patient(
        patient_id=1, updates=update_data, updater_role="doctor"
    )

    # Assert
    assert existing_patient.name == "Bob Updated"
    mock_db_session.commit.assert_called_once()
