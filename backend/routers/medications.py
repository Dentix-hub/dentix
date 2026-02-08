from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend import models, schemas
from backend.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/medications", tags=["Medications"])

@router.get("/saved", response_model=List[schemas.SavedMedication])
def get_saved_medications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")
    
    return db.query(models.SavedMedication).filter(
        models.SavedMedication.tenant_id == current_user.tenant_id
    ).all()

@router.post("/saved", response_model=schemas.SavedMedication)
def create_saved_medication(
    medication: schemas.SavedMedicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")
    
    db_med = models.SavedMedication(
        **medication.dict(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med

@router.delete("/saved/{med_id}")
def delete_saved_medication(
    med_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")
    
    med = db.query(models.SavedMedication).filter(
        models.SavedMedication.id == med_id,
        models.SavedMedication.tenant_id == current_user.tenant_id
    ).first()
    
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    db.delete(med)
    db.commit()
    return {"message": "Deleted successfully"}
