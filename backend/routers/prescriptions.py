"""Prescriptions Router — patient visibility is enforced before every mutation."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, crud
from .auth import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse
from backend.services.patient_access_service import ensure_patient_visible, ensure_prescription_visible
from ..utils.audit_logger import log_admin_action

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("", response_model=StandardResponse[schemas.Prescription])
async def create_prescription(
    prescription: schemas.PrescriptionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    await ensure_patient_visible(db, current_user, prescription.patient_id)
    result = await crud.create_prescription(
        db=db,
        prescription=prescription,
        tenant_id=current_user.tenant_id,
    )
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="create",
        entity_type="prescription",
        entity_id=result.id if hasattr(result, "id") else None,
        details=f"Prescription for patient {prescription.patient_id}",
    )
    return success_response(data=result, message="Prescription created")


@router.get("/{prescription_id}/print", response_model=StandardResponse[schemas.PrescriptionPrint])
async def get_prescription_print(
    prescription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Tenant-scoped printable prescription DTO (replaces stale sessionStorage PHI)."""
    prescription = await ensure_prescription_visible(db, current_user, prescription_id)
    patient_result = await db.execute(
        select(models.Patient).where(models.Patient.id == prescription.patient_id)
    )
    patient = patient_result.scalars().first()
    if not patient:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Prescription not found")

    tenant = await db.get(models.Tenant, current_user.tenant_id)
    clinic = {
        "doctor_name": getattr(tenant, "doctor_name", None),
        "doctor_title": getattr(tenant, "doctor_title", None),
        "clinic_address": getattr(tenant, "clinic_address", None),
        "clinic_phone": getattr(tenant, "clinic_phone", None)
        or getattr(tenant, "contact_phone", None),
    }
    return success_response(
        data={
            "prescription": prescription,
            "patient": {"id": patient.id, "name": patient.name},
            "clinic": clinic,
        },
        message="Prescription print data retrieved",
    )


@router.delete("/{prescription_id}", response_model=StandardResponse[dict])
async def delete_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    await ensure_prescription_visible(db, current_user, prescription_id)
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="prescription",
        entity_id=prescription_id,
        details=f"Deleted prescription #{prescription_id}",
    )
    result = await crud.delete_prescription(db, prescription_id, current_user.tenant_id)
    return success_response(data=result, message="Prescription deleted")
