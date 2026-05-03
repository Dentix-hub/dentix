"""
Treatments Router
Handles dental treatments and tooth status.

Thin router layer - all business logic delegated to TreatmentService.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import schemas, crud, models
from .auth import get_db
from backend.models import inventory as inv_models
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from backend.services.treatment_service import get_treatment_service
from backend.services.inventory_service import inventory_service
from backend.core.response import StandardResponse, success_response

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/treatments", tags=["Treatments"])


@router.post(
    "",
    response_model=StandardResponse[schemas.Treatment],
    summary="Create treatment",
    description="Create a new dental treatment record. Auto-calculates price from price list and deducts stock for consumed materials. Requires TREATMENT_PLAN_WRITE permission. Field 'cost' represents total before discount; 'tooth_number' is mandatory for dental procedures.",
)
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


@router.post(
    "/{treatment_id}/sessions",
    response_model=StandardResponse[schemas.TreatmentSession],
    summary="Add treatment session",
    description="Add a new session log to an existing treatment (e.g., RCT visit). Requires TREATMENT_PLAN_WRITE permission.",
)
def add_treatment_session(
    treatment_id: int,
    session: schemas.TreatmentSessionCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    """Add a session to a treatment."""
    if session.treatment_id != treatment_id:
        raise HTTPException(status_code=400, detail="Treatment ID mismatch")
    treatment_svc = get_treatment_service(db, current_user.tenant_id, current_user)
    return success_response(data=treatment_svc.add_session(session), message="Session added successfully")


# --- Tooth Status ---
@router.post(
    "/tooth_status",
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


# --- Treatment Material Usage ---
@router.get(
    "/{treatment_id}/materials",
    response_model=StandardResponse[List[schemas.inventory.TreatmentMaterialUsageOut]],
    summary="Get treatment materials",
    description="Get all material usage records for a treatment. Requires TREATMENT_PLAN_READ permission.",
)
def get_treatment_materials(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    """Get material usage for a treatment."""
    usages = (
        db.query(inv_models.TreatmentMaterialUsage)
        .filter(
            inv_models.TreatmentMaterialUsage.treatment_id == treatment_id,
            inv_models.TreatmentMaterialUsage.tenant_id == (current_user.tenant_id or 1),
        )
        .all()
    )
    return success_response(data=usages)


@router.post(
    "/{treatment_id}/materials",
    response_model=StandardResponse[List[schemas.inventory.TreatmentMaterialUsageOut]],
    summary="Save treatment materials",
    description="Save material usage for a treatment. For DIVISIBLE materials: links to active session with weight. For NON_DIVISIBLE: deducts stock immediately. Requires TREATMENT_PLAN_WRITE permission.",
)
def save_treatment_materials(
    treatment_id: int,
    materials: List[schemas.inventory.TreatmentMaterialUsageCreate],
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    """Save material usage for a treatment."""
    tenant_id = current_user.tenant_id or 1
    results = []

    # Verify treatment exists
    treatment = db.query(models.Treatment).filter(
        models.Treatment.id == treatment_id,
        models.Treatment.tenant_id == tenant_id,
    ).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")

    # Clear existing materials for this treatment
    db.query(inv_models.TreatmentMaterialUsage).filter(
        inv_models.TreatmentMaterialUsage.treatment_id == treatment_id,
        inv_models.TreatmentMaterialUsage.tenant_id == tenant_id,
    ).delete()

    for item in materials:
        # Get material details
        material = db.query(inv_models.Material).filter(
            inv_models.Material.id == item.material_id,
            inv_models.Material.tenant_id == tenant_id,
        ).first()
        if not material:
            continue

        # For NON_DIVISIBLE: deduct stock immediately
        if material.type == "NON_DIVISIBLE" and item.quantity_used:
            try:
                inventory_service.consume_stock(
                    material_id=item.material_id,
                    quantity=item.quantity_used,
                    tenant_id=tenant_id,
                    user_id=current_user.id,
                    db=db,
                )
            except ValueError as e:
                logger.error(f"Stock consumption failed: {e}")
                raise HTTPException(status_code=400, detail=str(e))

        # Create usage record
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

    db.commit()
    for r in results:
        db.refresh(r)

    return success_response(data=results, message="Materials saved successfully")
