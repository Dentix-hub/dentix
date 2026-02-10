"""
Prescriptions Router
Handles prescription management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, crud
from .auth import get_current_user, get_db

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("/", response_model=schemas.Prescription)
def create_prescription(
    prescription: schemas.PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new prescription."""
    patient = crud.get_patient(db, prescription.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.create_prescription(db=db, prescription=prescription)


@router.delete("/{prescription_id}")
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete a prescription."""
    return crud.delete_prescription(db, prescription_id, current_user.tenant_id)
