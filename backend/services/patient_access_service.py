"""Central helpers for patient-scoped authorization at domain boundaries."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.services.visibility_service import get_visibility_service


async def ensure_patient_visible(
    db: AsyncSession,
    current_user,
    patient_id: int,
    *,
    detail: str = "Patient not found",
) -> None:
    """Return 404 unless the current user may view the patient."""
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    if not await visibility.can_view_patient(patient_id):
        raise HTTPException(status_code=404, detail=detail)


async def ensure_treatment_visible(
    db: AsyncSession,
    current_user,
    treatment_id: int,
    *,
    detail: str = "Treatment not found",
):
    """Load a tenant treatment and enforce visibility of its patient."""
    result = await db.execute(
        select(models.Treatment).where(
            models.Treatment.id == treatment_id,
            models.Treatment.tenant_id == current_user.tenant_id,
        )
    )
    treatment = result.scalars().first()
    if not treatment:
        raise HTTPException(status_code=404, detail=detail)
    await ensure_patient_visible(db, current_user, treatment.patient_id, detail=detail)
    return treatment


async def ensure_prescription_visible(
    db: AsyncSession,
    current_user,
    prescription_id: int,
    *,
    detail: str = "Prescription not found",
):
    """Load a tenant prescription and enforce visibility of its patient."""
    result = await db.execute(
        select(models.Prescription)
        .join(models.Patient, models.Prescription.patient_id == models.Patient.id)
        .where(
            models.Prescription.id == prescription_id,
            models.Patient.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    prescription = result.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail=detail)
    await ensure_patient_visible(db, current_user, prescription.patient_id, detail=detail)
    return prescription


async def visible_patient_ids_query(db: AsyncSession, current_user):
    """Return a SELECT of patient IDs already scoped by tenant + visibility."""
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    query = await visibility.get_visible_patient_query()
    return query.with_only_columns(models.Patient.id)
