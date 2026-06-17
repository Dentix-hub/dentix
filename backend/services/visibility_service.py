"""
Patient Visibility Service (Multi-Doctor Support)

This service determines which patients a user can see based on:
- User role
- Patient visibility mode setting
- Doctor assignments and appointments

SECURITY: This is the ONLY place patient visibility should be determined.
All patient queries MUST use this service.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from typing import List, Optional, Set
from backend.models import User, Patient, Appointment
from backend.core.permissions import PatientVisibilityMode
import logging

logger = logging.getLogger(__name__)


class PatientVisibilityService:
    """
    Central service for patient visibility logic.

    SECURITY CRITICAL:
    - Admin sees all patients
    - Doctor sees based on patient_visibility_mode
    - Other roles see all patients (receptionist, nurse, etc.)
    """

    def __init__(self, db: AsyncSession, user: User, tenant_id: int):
        self.db = db
        self.user = user
        self.tenant_id = tenant_id
        self._visible_ids_cache: Optional[Set[int]] = None

    async def get_visible_patient_query(self):
        """
        Get a filtered query for visible patients.

        Returns:
            SQLAlchemy Select filtered to only visible patients
        """
        base_query = select(Patient).where(
            Patient.tenant_id == self.tenant_id, Patient.is_deleted == False  # noqa: E712
        )

        # Admin sees all
        if self.user.role == "admin":
            return base_query

        # Doctor visibility based on mode
        if self.user.role == "doctor":
            return await self._get_doctor_filtered_query(base_query)

        # Default: all patients (receptionist, nurse, accountant, etc.)
        return base_query

    async def _get_doctor_filtered_query(self, base_query):
        """Filter patients for doctor based on visibility mode."""
        mode = self.user.patient_visibility_mode or "all_assigned"

        if mode == PatientVisibilityMode.ALL_ASSIGNED.value:
            # Only assigned patients
            return base_query.where(Patient.assigned_doctor_id == self.user.id)

        elif mode == PatientVisibilityMode.APPOINTMENTS_ONLY.value:
            # Only patients with appointments
            patient_ids = await self._get_appointment_patient_ids()
            return base_query.where(Patient.id.in_(patient_ids))

        elif mode == PatientVisibilityMode.MIXED.value:
            # Both assigned and appointment patients
            appointment_patient_ids = await self._get_appointment_patient_ids()
            return base_query.where(
                or_(
                    Patient.assigned_doctor_id == self.user.id,
                    Patient.id.in_(appointment_patient_ids),
                )
            )

        # Fallback: only assigned (safest default)
        return base_query.where(Patient.assigned_doctor_id == self.user.id)

    async def _get_appointment_patient_ids(self) -> List[int]:
        """Get patient IDs that have appointments with this doctor."""
        stmt = (
            select(Appointment.patient_id)
            .where(Appointment.doctor_id == self.user.id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        return [r[0] for r in result.all()]

    async def get_visible_patient_ids(self) -> Set[int]:
        """
        Get set of visible patient IDs.

        Cached for performance during single request.
        """
        if self._visible_ids_cache is None:
            query = await self.get_visible_patient_query()
            result = await self.db.execute(query)
            self._visible_ids_cache = {p.id for p in result.scalars().all()}

        return self._visible_ids_cache

    async def can_view_patient(self, patient_id: int) -> bool:
        """
        Check if user can view a specific patient.

        Args:
            patient_id: The patient ID to check

        Returns:
            True if user can view this patient
        """
        visible_ids = await self.get_visible_patient_ids()
        return patient_id in visible_ids

    async def filter_patients(self, patients: List[Patient]) -> List[Patient]:
        """
        Filter a list of patients to only visible ones.

        Args:
            patients: List of patient objects

        Returns:
            Filtered list containing only visible patients
        """
        visible_ids = await self.get_visible_patient_ids()
        return [p for p in patients if p.id in visible_ids]


def get_visibility_service(
    db: AsyncSession, user: User, tenant_id: int
) -> PatientVisibilityService:
    """Factory function to create visibility service."""
    return PatientVisibilityService(db, user, tenant_id)
