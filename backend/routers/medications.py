from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend import models, schemas
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.get("/saved", response_model=StandardResponse[List[schemas.SavedMedication]])
async def get_saved_medications(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    stmt = select(models.SavedMedication).where(models.SavedMedication.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    data = result.scalars().all()
    return success_response(data=data)


@router.post("/saved", response_model=StandardResponse[schemas.SavedMedication])
async def create_saved_medication(
    medication: schemas.SavedMedicationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    db_med = models.SavedMedication(
        **medication.dict(), tenant_id=current_user.tenant_id
    )
    db.add(db_med)
    await db.commit()
    await db.refresh(db_med)
    return success_response(data=db_med, message="Medication saved")


@router.delete("/saved/{med_id}", response_model=StandardResponse[dict])
async def delete_saved_medication(
    med_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    stmt = (
        select(models.SavedMedication)
        .where(
            models.SavedMedication.id == med_id,
            models.SavedMedication.tenant_id == current_user.tenant_id,
        )
    )
    result = await db.execute(stmt)
    med = result.scalars().first()

    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")

    await db.delete(med)
    await db.commit()
    return success_response(message="Deleted successfully")
