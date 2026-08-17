"""Unified patient-directory search service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import or_
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

    async def get_directory(self, q: str = "", cursor: Optional[str] = None, limit: int = 30) -> dict:
        query = await self._base_query()
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

    async def legacy_search(self, q: str, limit: int = 50):
        query = await self._base_query()
        query = self._apply_search(query, q).order_by(models.Patient.id.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().unique().all()
