"""
C6.3 — Appointment Service / CRUD Unit Tests

Tests appointment logic:
- Creation with double-booking prevention
- Listing with tenant isolation
- Doctor filtering
- Status updates
- Soft delete
- Edge cases
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from backend import models, schemas
from backend.crud.appointment import (
    create_appointment,
    get_appointments,
    update_appointment_status,
    delete_appointment,
)


# ============================================
# FIXTURES
# ============================================


@pytest.fixture
def mock_db():
    """Chainable mock DB session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()

    # Default mock result behavior
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def sample_appointment():
    """Basic appointment creation data."""
    return schemas.AppointmentCreate(
        patient_id=1,
        doctor_id=10,
        date_time=datetime(2026, 6, 15, 10, 0),
        status="Scheduled",
        notes="Routine checkup",
    )


@pytest.fixture
def appointment_no_doctor():
    """Appointment without doctor assignment."""
    return schemas.AppointmentCreate(
        patient_id=1,
        date_time=datetime(2026, 6, 15, 14, 0),
        status="Scheduled",
    )


# ============================================
# CREATION TESTS
# ============================================


class TestAppointmentCreation:
    """Tests for appointment creation logic."""

    async def test_create_appointment_success(self, mock_db, sample_appointment):
        """Standard appointment creation stores and returns the record."""
        # No existing appointment at that time
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        await create_appointment(mock_db, sample_appointment, tenant_id=1)

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, models.Appointment)
        assert added.patient_id == 1
        assert added.doctor_id == 10
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_once()

    async def test_create_appointment_double_booking_raises(self, mock_db, sample_appointment):
        """Must reject if doctor is already booked at the same time."""
        # Existing appointment found
        existing = MagicMock(spec=models.Appointment)
        existing.id = 99
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already booked"):
            await create_appointment(mock_db, sample_appointment, tenant_id=1)

    async def test_create_appointment_no_doctor_skips_booking_check(
        self, mock_db, appointment_no_doctor
    ):
        """Appointments without a doctor should skip double-booking check."""
        await create_appointment(mock_db, appointment_no_doctor, tenant_id=1)

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, models.Appointment)
        assert added.doctor_id is None

    async def test_create_appointment_cancelled_slot_available(self, mock_db):
        """Cancelled appointments should NOT block the time slot."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        data = schemas.AppointmentCreate(
            patient_id=1,
            doctor_id=10,
            date_time=datetime(2026, 6, 15, 10, 0),
        )

        await create_appointment(mock_db, data, tenant_id=1)
        mock_db.add.assert_called_once()


# ============================================
# LISTING TESTS
# ============================================


class TestAppointmentListing:
    """Tests for appointment retrieval."""

    async def test_get_appointments_applies_tenant_filter(self, mock_db):
        """Must filter by tenant_id through Patient join."""
        await get_appointments(mock_db, tenant_id=5, skip=0, limit=50)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "patient" in sql_str
        assert "tenant_id" in sql_str

    async def test_get_appointments_filters_soft_deleted(self, mock_db):
        """Soft-deleted appointments must be excluded."""
        await get_appointments(mock_db, tenant_id=1)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "is_deleted" in sql_str

    async def test_get_appointments_doctor_filter(self, mock_db):
        """When doctor_id is provided, only that doctor's appointments show."""
        await get_appointments(mock_db, tenant_id=1, doctor_id=10)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "doctor_id" in sql_str

    async def test_get_appointments_pagination(self, mock_db):
        """skip and limit must be applied."""
        await get_appointments(mock_db, tenant_id=1, skip=20, limit=10)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        assert stmt._limit == 10
        assert stmt._offset == 20


# ============================================
# STATUS UPDATE TESTS
# ============================================


class TestAppointmentStatusUpdate:
    """Tests for appointment status updates."""

    async def test_update_status_success(self, mock_db):
        """Standard status update on existing appointment."""
        mock_appt = MagicMock(spec=models.Appointment)
        mock_appt.id = 1
        mock_appt.status = "Scheduled"
        mock_appt.patient = MagicMock()
        mock_appt.patient.tenant_id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_appt
        mock_db.execute.return_value = mock_result

        await update_appointment_status(mock_db, 1, "Completed", tenant_id=1)

        assert mock_appt.status == "Completed"
        mock_db.commit.assert_called_once()

    async def test_update_status_not_found(self, mock_db):
        """Non-existent appointment returns None."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await update_appointment_status(mock_db, 999, "Completed", tenant_id=1)
        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.parametrize(
        "new_status",
        ["Scheduled", "Confirmed", "In Progress", "Completed", "Cancelled", "No Show"],
    )
    async def test_update_status_all_transitions(self, mock_db, new_status):
        """All valid status transitions should work."""
        mock_appt = MagicMock(spec=models.Appointment)
        mock_appt.id = 1
        mock_appt.status = "Scheduled"
        mock_appt.patient = MagicMock()
        mock_appt.patient.tenant_id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_appt
        mock_db.execute.return_value = mock_result

        await update_appointment_status(mock_db, 1, new_status, tenant_id=1)
        assert mock_appt.status == new_status


# ============================================
# SOFT DELETE TESTS
# ============================================


class TestAppointmentDeletion:
    """Tests for appointment soft delete."""

    async def test_soft_delete_sets_flags(self, mock_db):
        """Soft delete must set is_deleted=True and deleted_at."""
        mock_appt = MagicMock(spec=models.Appointment)
        mock_appt.id = 1
        mock_appt.is_deleted = False
        mock_appt.patient = MagicMock()
        mock_appt.patient.tenant_id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_appt
        mock_db.execute.return_value = mock_result

        await delete_appointment(mock_db, 1, tenant_id=1)

        assert mock_appt.is_deleted is True
        assert mock_appt.deleted_at is not None
        mock_db.commit.assert_called_once()

    async def test_soft_delete_not_found(self, mock_db):
        """Deleting non-existent appointment returns None."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await delete_appointment(mock_db, 999, tenant_id=1)
        assert result is None

    async def test_cannot_double_delete(self, mock_db):
        """Already soft-deleted appointments should not be found (filtered by is_deleted=False)."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await delete_appointment(mock_db, 1, tenant_id=1)
        assert result is None


# ============================================
# TENANT ISOLATION
# ============================================


class TestAppointmentTenantIsolation:
    """Tests for tenant isolation in appointment operations."""

    async def test_listing_respects_tenant_boundary(self, mock_db):
        """Appointments are always filtered by tenant_id via Patient join."""
        await get_appointments(mock_db, tenant_id=5)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "patient" in sql_str
        assert "tenant_id" in sql_str

    async def test_status_update_respects_tenant_boundary(self, mock_db):
        """Status update must join Patient table for tenant check."""
        mock_appt = MagicMock(spec=models.Appointment)
        mock_appt.id = 1
        mock_appt.patient = MagicMock()
        mock_appt.patient.tenant_id = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_appt
        mock_db.execute.return_value = mock_result

        await update_appointment_status(mock_db, 1, "Completed", tenant_id=5)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "patient" in sql_str

    async def test_delete_respects_tenant_boundary(self, mock_db):
        """Delete must join Patient table for tenant check."""
        mock_appt = MagicMock(spec=models.Appointment)
        mock_appt.id = 1
        mock_appt.patient = MagicMock()
        mock_appt.patient.tenant_id = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_appt
        mock_db.execute.return_value = mock_result

        await delete_appointment(mock_db, 1, tenant_id=5)

        mock_db.execute.assert_called_once()
        stmt = mock_db.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "patient" in sql_str
