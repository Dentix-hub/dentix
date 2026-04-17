"""
Treatments Router
Handles dental treatments and tooth status.

Thin router layer - all business logic delegated to TreatmentService.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import schemas, crud
from .auth import get_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from backend.services.treatment_service import get_treatment_service
from backend.core.response import StandardResponse, success_response

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/treatments", tags=["Treatments"])


@router.post(
    "/",
    response_model=StandardResponse[schemas.Treatment],
    summary="Create treatment",
    description="Create a new dental treatment record. Auto-calculates price from price list and deducts stock for consumed materials. Requires TREATMENT_PLAN_WRITE permission.",
)
@limiter.limit("10/minute")
def create_treatment(
    request: Request,
    treatment: schemas.TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    """Create a new treatment record."""
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    return success_response(data=treatment_svc.create_treatment(treatment), message="Treatment created successfully")


@router.put(
    "/{treatment_id}",
    response_model=StandardResponse[schemas.Treatment],
    summary="Update treatment",
    description="Update an existing treatment. Re-validates stock and re-consumes materials. Requires TREATMENT_PLAN_WRITE permission.",
)
def update_treatment(
    treatment_id: int,
    treatment: schemas.TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    """Update a treatment record."""
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    return success_response(data=treatment_svc.update_treatment(treatment_id, treatment), message="Treatment updated successfully")


@router.delete(
    "/{treatment_id}",
    response_model=StandardResponse[schemas.Treatment],
    summary="Delete treatment",
    description="Delete a treatment record. Logs the action for audit trail. Requires CLINICAL_WRITE permission.",
)
def delete_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Delete a treatment record."""
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    return success_response(data=treatment_svc.delete_treatment(treatment_id), message="Treatment deleted successfully")


# --- Tooth Status ---
@router.post(
    "/tooth_status/",
    response_model=StandardResponse[schemas.ToothStatus],
    summary="Update tooth status",
    description="Update or create a tooth status entry in the dental chart. Requires CLINICAL_WRITE permission.",
)
def update_tooth_status(
    status: schemas.ToothStatusCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Update tooth status in dental chart."""
    patient = crud.get_patient(db, status.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return success_response(data=crud.update_tooth_status(db, status, current_user.tenant_id), message="Tooth status updated")
