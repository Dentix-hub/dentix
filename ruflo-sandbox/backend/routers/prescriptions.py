"""
Prescriptions Router
Handles prescription management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, crud
from .auth import get_db
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse
from ..utils.audit_logger import log_admin_action

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("", response_model=StandardResponse[schemas.Prescription])
def create_prescription(
    prescription: schemas.PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Create a new prescription."""
    patient = crud.get_patient(db, prescription.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = crud.create_prescription(db=db, prescription=prescription)
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="create",
        entity_type="prescription",
        entity_id=result.id if hasattr(result, 'id') else None,
        details=f"Prescription for patient {prescription.patient_id}",
    )
    return success_response(data=result, message="Prescription created")


@router.delete("/{prescription_id}", response_model=StandardResponse[dict])
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Delete a prescription."""
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="prescription",
        entity_id=prescription_id,
        details=f"Deleted prescription #{prescription_id}",
    )
    result = crud.delete_prescription(db, prescription_id, current_user.tenant_id)
    return success_response(data=result, message="Prescription deleted")
