from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend import models, schemas
from backend.routers.auth import get_db
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.get("/saved", response_model=StandardResponse[List[schemas.SavedMedication]])
def get_saved_medications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    data = (
        db.query(models.SavedMedication)
        .filter(models.SavedMedication.tenant_id == current_user.tenant_id)
        .all()
    )
    return success_response(data=data)


@router.post("/saved", response_model=StandardResponse[schemas.SavedMedication])
def create_saved_medication(
    medication: schemas.SavedMedicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    db_med = models.SavedMedication(
        **medication.dict(), tenant_id=current_user.tenant_id
    )
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return success_response(data=db_med, message="Medication saved")


@router.delete("/saved/{med_id}", response_model=StandardResponse[dict])
def delete_saved_medication(
    med_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    med = (
        db.query(models.SavedMedication)
        .filter(
            models.SavedMedication.id == med_id,
            models.SavedMedication.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")

    db.delete(med)
    db.commit()
    return success_response(message="Deleted successfully")
