"""
Treatments Router
Handles dental treatments and tooth status.

Thin router layer - all business logic delegated to TreatmentService.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .. import schemas
from backend.database import get_async_db
from backend.models import inventory as inv_models
from backend.core.permissions import Permission, require_permission
from backend.services.treatment_service import get_treatment_service
from backend.services.inventory_service import inventory_service
from backend.services.patient_access_service import (
    ensure_patient_visible,
    ensure_treatment_visible,
)
from backend.core.response import StandardResponse, success_response

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/treatments", tags=["Treatments"])


@router.post(
    "",
    response_model=StandardResponse[schemas.Treatment],
    summary="Create treatment",
    description="Create a new dental treatment record. Auto-calculates price from price list and deducts stock for consumed materials. Requires TREATMENT_PLAN_WRITE permission. Field 'cost' represents total before discount; 'tooth_number' is mandatory for dental procedures.",
)
async def create_treatment(
    request: Request,
    treatment: schemas.TreatmentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    await ensure_patient_visible(db, current_user, treatment.patient_id)
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    result = await treatment_svc.create_treatment(treatment)
    return success_response(data=result, message="Treatment created successfully")


@router.put("/{treatment_id}", response_model=StandardResponse[schemas.Treatment], summary="Update treatment")
async def update_treatment(
    treatment_id: int,
    treatment: schemas.TreatmentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    await ensure_treatment_visible(db, current_user, treatment_id)
    await ensure_patient_visible(db, current_user, treatment.patient_id)
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    result = await treatment_svc.update_treatment(treatment_id, treatment)
    return success_response(data=result, message="Treatment updated successfully")


@router.delete("/{treatment_id}", response_model=StandardResponse[schemas.Treatment], summary="Delete treatment")
async def delete_treatment(
    treatment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    await ensure_treatment_visible(db, current_user, treatment_id)
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    result = await treatment_svc.delete_treatment(treatment_id)
    return success_response(data=result, message="Treatment deleted successfully")


@router.post("/{treatment_id}/sessions", response_model=StandardResponse[schemas.TreatmentSession], summary="Add treatment session")
async def add_treatment_session(
    treatment_id: int,
    session: schemas.TreatmentSessionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    if session.treatment_id != treatment_id:
        raise HTTPException(status_code=400, detail="Treatment ID mismatch")
    await ensure_treatment_visible(db, current_user, treatment_id)
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    result = await treatment_svc.add_session(session)
    return success_response(data=result, message="Session added successfully")


@router.post("/tooth_status", response_model=StandardResponse[schemas.ToothStatus], summary="Update tooth status")
async def update_tooth_status(
    status: schemas.ToothStatusCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    await ensure_patient_visible(db, current_user, status.patient_id)
    from .. import crud
    result = await crud.update_tooth_status(db, status, current_user.tenant_id)
    return success_response(data=result, message="Tooth status updated")


@router.get("/{treatment_id}/materials", response_model=StandardResponse[List[schemas.inventory.TreatmentMaterialUsageOut]], summary="Get treatment materials")
async def get_treatment_materials(
    treatment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    await ensure_treatment_visible(db, current_user, treatment_id)
    stmt = select(inv_models.TreatmentMaterialUsage).where(
        inv_models.TreatmentMaterialUsage.treatment_id == treatment_id,
        inv_models.TreatmentMaterialUsage.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(stmt)
    return success_response(data=result.scalars().all())


@router.post("/{treatment_id}/materials", response_model=StandardResponse[List[schemas.inventory.TreatmentMaterialUsageOut]], summary="Save treatment materials")
async def save_treatment_materials(
    treatment_id: int,
    materials: List[schemas.inventory.TreatmentMaterialUsageCreate],
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    tenant_id = current_user.tenant_id
    treatment = await ensure_treatment_visible(db, current_user, treatment_id)
    results = []

    reference_id = f"TREATMENT_MATERIALS:{treatment_id}"
    await inventory_service.reverse_stock_by_reference(reference_id=reference_id, user_id=current_user.id, db=db)
    await db.execute(delete(inv_models.TreatmentMaterialUsage).where(
        inv_models.TreatmentMaterialUsage.treatment_id == treatment_id,
        inv_models.TreatmentMaterialUsage.tenant_id == tenant_id,
    ))

    for item in materials:
        material = (await db.execute(select(inv_models.Material).where(
            inv_models.Material.id == item.material_id,
            inv_models.Material.tenant_id == tenant_id,
            inv_models.Material.is_deleted == False,  # noqa: E712
        ))).scalars().first()
        if not material:
            continue
        if material.type == "NON_DIVISIBLE" and item.quantity_used:
            try:
                await inventory_service.consume_stock(
                    material_id=item.material_id,
                    quantity=item.quantity_used,
                    tenant_id=tenant_id,
                    user_id=current_user.id,
                    patient_id=treatment.patient_id,
                    reference_id=reference_id,
                    db=db,
                    commit=False,
                )
            except ValueError as exc:
                logger.error("Stock consumption failed for treatment material")
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        usage = inv_models.TreatmentMaterialUsage(
            treatment_id=treatment_id,
            material_id=item.material_id,
            session_id=item.session_id,
            weight_score=item.weight_score,
            quantity_used=item.quantity_used,
            is_manual_override=item.is_manual_override,
            tenant_id=tenant_id,
        )
        db.add(usage)
        results.append(usage)

    await db.commit()
    for usage in results:
        await db.refresh(usage)
    return success_response(data=results, message="Materials saved successfully")
