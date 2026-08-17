"""Patient Visibility Service (Multi-Doctor Support)."""

import logging
from typing import List, Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.permissions import PatientVisibilityMode
from backend.models import Appointment, Patient, User

logger = logging.getLogger(__name__)


class PatientVisibilityService:
    """Central service for patient visibility logic."""

    def __init__(self, db: AsyncSession, user: User, tenant_id: int):
        self.db = db
        self.user = user
        self.tenant_id = tenant_id
        self._visible_ids_cache: Optional[Set[int]] = None

    async def get_visible_patient_query(self):
        base_query = select(Patient).where(
            Patient.tenant_id == self.tenant_id,
            Patient.is_deleted == False,
        )
        if self.user.role == "admin":
            return base_query
        if self.user.role == "doctor":
            return self._get_doctor_filtered_query(base_query)
        return base_query

    def _appointment_patient_subquery(self):
        return (
            select(Appointment.patient_id)
            .where(
                Appointment.doctor_id == self.user.id,
                Appointment.tenant_id == self.tenant_id,
            )
            .distinct()
        )

    def _get_doctor_filtered_query(self, base_query):
        mode = self.user.patient_visibility_mode or "all_assigned"
        if mode == PatientVisibilityMode.ALL_ASSIGNED.value:
            return base_query.where(Patient.assigned_doctor_id == self.user.id)

        appointment_patient_ids = self._appointment_patient_subquery()
        if mode == PatientVisibilityMode.APPOINTMENTS_ONLY.value:
            return base_query.where(Patient.id.in_(appointment_patient_ids))
        if mode == PatientVisibilityMode.MIXED.value:
            return base_query.where(
                or_(
                    Patient.assigned_doctor_id == self.user.id,
                    Patient.id.in_(appointment_patient_ids),
                )
            )
        return base_query.where(Patient.assigned_doctor_id == self.user.id)

    async def get_visible_patient_ids(self) -> Set[int]:
        if self._visible_ids_cache is None:
            query = await self.get_visible_patient_query()
            result = await self.db.execute(query)
            self._visible_ids_cache = {p.id for p in result.scalars().all()}
        return self._visible_ids_cache

    async def can_view_patient(self, patient_id: int) -> bool:
        query = await self.get_visible_patient_query()
        result = await self.db.execute(query.where(Patient.id == patient_id).limit(1))
        return result.scalars().first() is not None

    async def filter_patients(self, patients: List[Patient]) -> List[Patient]:
        visible_ids = await self.get_visible_patient_ids()
        return [p for p in patients if p.id in visible_ids]


def get_visibility_service(db: AsyncSession, user: User, tenant_id: int) -> PatientVisibilityService:
    return PatientVisibilityService(db, user, tenant_id)
