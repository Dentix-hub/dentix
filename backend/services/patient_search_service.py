"""Unified patient-directory search service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend import models
from backend.core.pagination import CursorParams, apply_cursor_pagination, build_cursor_response
from backend.core.response import cursor_paginated_response
from backend.services.visibility_service import get_visibility_service
from backend.utils.patient_search_normalization import (
    classify_patient_search_query,
    escaped_like_pattern,
    extract_file_number,
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)
from backend.utils.tenant_time import tenant_day_local_naive_bounds


def _current_age(patient: models.Patient) -> Optional[int]:
    """Return current display age without fabricating an exact birthday."""
    if patient.date_of_birth:
        today = date.today()
        return today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    age = patient.age if patient.age and patient.age > 0 else None
    if age is None or not patient.age_recorded_at:
        return age

    recorded = patient.age_recorded_at
    recorded_date = recorded.date() if isinstance(recorded, datetime) else recorded
    today = date.today()
    elapsed_years = today.year - recorded_date.year - (
        (today.month, today.day) < (recorded_date.month, recorded_date.day)
    )
    return max(0, age + max(0, elapsed_years))


class PatientSearchService:
    """Tenant- and visibility-aware patient search."""

    def __init__(self, db: AsyncSession, tenant_id: int, user):
        self.db = db
        self.tenant_id = tenant_id
        self.user = user

    async def _base_query(self):
        visibility = get_visibility_service(self.db, self.user, self.tenant_id)
        query = await visibility.get_visible_patient_query()
        return query.options(joinedload(models.Patient.assigned_doctor))

    async def _apply_scope(self, query, scope: str):
        if scope == "all":
            return query

        if scope == "mine":
            if self.user.role != "doctor":
                return query.where(models.Patient.id == -1)
            return query.where(models.Patient.assigned_doctor_id == self.user.id)

        if scope == "today":
            timezone_result = await self.db.execute(
                select(models.Tenant.timezone).where(models.Tenant.id == self.tenant_id)
            )
            timezone_name = timezone_result.scalar_one_or_none()
            day_start, day_end = tenant_day_local_naive_bounds(timezone_name)
            appointment_patient_ids = (
                select(models.Appointment.patient_id)
                .where(
                    models.Appointment.tenant_id == self.tenant_id,
                    models.Appointment.is_deleted == False,  # noqa: E712
                    models.Appointment.date_time >= day_start,
                    models.Appointment.date_time < day_end,
                )
                .distinct()
            )
            return query.where(models.Patient.id.in_(appointment_patient_ids))

        return query

    def _apply_search(self, query, q: str):
        query_type = classify_patient_search_query(q)

        if query_type == "empty":
            return query

        if query_type == "file_number":
            patient_id = extract_file_number(q)
            if patient_id is None:
                return query.where(models.Patient.id == -1)
            return query.where(models.Patient.id == patient_id)

        if query_type == "phone":
            phone_hash = patient_phone_search_hash(q)
            if not phone_hash:
                return query.where(models.Patient.id == -1)
            return query.where(models.Patient.phone_search_hash == phone_hash)

        normalized_name = normalize_patient_name_for_search(q)
        pattern = escaped_like_pattern(normalized_name)
        return query.where(
            or_(
                models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                (
                    models.Patient.name_search_normalized.is_(None)
                    & models.Patient.name.ilike(f"%{q.strip()}%")
                ),
            )
        )

    @staticmethod
    def _directory_item(patient: models.Patient) -> dict:
        doctor = getattr(patient, "assigned_doctor", None)
        doctor_name = None
        if doctor:
            doctor_name = getattr(doctor, "full_name", None) or getattr(doctor, "username", None)
        return {
            "id": patient.id,
            "file_number": patient.id,
            "name": patient.name,
            "age": _current_age(patient),
            "phone": patient.phone or None,
            "assigned_doctor_id": patient.assigned_doctor_id,
            "assigned_doctor_name": doctor_name,
            "date_of_birth": patient.date_of_birth,
            "date_of_birth_precision": patient.date_of_birth_precision,
            "age_recorded_at": patient.age_recorded_at,
            "created_at": patient.created_at,
        }

    async def get_directory(
        self,
        q: str = "",
        cursor: Optional[str] = None,
        limit: int = 30,
        scope: str = "all",
    ) -> dict:
        query = await self._base_query()
        query = await self._apply_scope(query, scope)
        query = self._apply_search(query, q)
        cursor_params = CursorParams(cursor=cursor, limit=limit)
        query = apply_cursor_pagination(
            query, models.Patient, cursor_params, sort_column_name="id", descending=True
        )
        result = await self.db.execute(query)
        patients = result.scalars().unique().all()
        items, next_cursor, has_more = build_cursor_response(patients, cursor_params.limit)
        return cursor_paginated_response(
            data=[self._directory_item(patient) for patient in items],
            limit=cursor_params.limit,
            next_cursor=next_cursor,
            has_more=has_more,
            message="Patients retrieved successfully",
        )

    async def get_recent(self, patient_ids: list[int]) -> list[dict]:
        ordered_ids = []
        seen = set()
        for patient_id in patient_ids:
            if patient_id > 0 and patient_id not in seen:
                seen.add(patient_id)
                ordered_ids.append(patient_id)
            if len(ordered_ids) == 10:
                break

        if not ordered_ids:
            return []

        query = await self._base_query()
        result = await self.db.execute(query.where(models.Patient.id.in_(ordered_ids)))
        patients = result.scalars().unique().all()
        by_id = {patient.id: patient for patient in patients}
        return [self._directory_item(by_id[patient_id]) for patient_id in ordered_ids if patient_id in by_id]

    async def legacy_search(self, q: str, limit: int = 50):
        query = await self._base_query()
        query = self._apply_search(query, q).order_by(models.Patient.id.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().unique().all()
