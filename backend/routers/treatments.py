"""
Treatments Router
Handles dental treatments and tooth status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import schemas, crud, models
from .auth import get_current_user, get_db
from ..services.inventory_service import inventory_service
from ..utils.audit_logger import log_admin_action
import logging

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/treatments", tags=["Treatments"])


@router.post("/", response_model=schemas.Treatment)
def create_treatment(
    treatment: schemas.TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new treatment record."""
    patient = crud.get_patient(db, treatment.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 0. Stock Validation (Pre-Check)
    # 0. Stock Validation (Pre-Check)
    if treatment.consumedMaterials:
        try:
            errors = []
            for item in treatment.consumedMaterials:
                is_valid, available, mat_name = inventory_service.validate_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=current_user.tenant_id,
                    db=db,
                )
                if not is_valid:
                    errors.append(
                        f"{mat_name} (Need: {item.quantity}, Available: {available})"
                    )

            if errors:
                raise HTTPException(
                    status_code=400,
                    detail="فشل حفظ العلاج بسبب نقص المخزون: " + " | ".join(errors),
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Stock Validation Error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Stock Validation Error: {str(e)}"
            )

    # Auto-assign doctor if not provided (use current_user.id as default)
    doctor_id = treatment.doctor_id if treatment.doctor_id else current_user.id

    # --- Multi Price List Logic ---
    from ..services.pricing_service import get_pricing_service

    pricing = get_pricing_service(db, current_user.tenant_id)

    # 1. Determine price list (from Appointment or Patient default)
    price_list_id = getattr(treatment, "price_list_id", None)
    if not price_list_id:
        patient_obj = crud.get_patient(db, treatment.patient_id, current_user.tenant_id)
        price_list_id = patient_obj.default_price_list_id if patient_obj else None

    # 2. Calculate Price
    procedure_name = treatment.procedure
    procedure_obj = (
        db.query(models.Procedure)
        .filter(
            models.Procedure.name == procedure_name,
            or_(
                models.Procedure.tenant_id == current_user.tenant_id,
                models.Procedure.tenant_id == None,
            ),
        )
        .first()
    )

    unit_price = 0.0
    price_snapshot = None

    if procedure_obj:
        unit_price = pricing.get_procedure_price(procedure_obj.id, price_list_id)

        # Create snapshot manually or via service helper
        import json
        from datetime import date

        pl = pricing.get_price_list(price_list_id)
        snapshot = {
            "list_id": price_list_id,
            "list_name": pl.name if pl else "Standard",
            "unit_price": unit_price,
            "date": date.today().isoformat(),
        }
        price_snapshot = json.dumps(snapshot)

    # 3. Create
    created_treatment = crud.create_treatment(
        db=db,
        treatment=treatment,
        tenant_id=current_user.tenant_id,
        doctor_id=doctor_id,
        price_list_id=price_list_id,
        unit_price=unit_price,
        price_snapshot=price_snapshot,
        commit=False,  # Defer commit until stock is consumed
    )

    # 4. Consume Stock (Post-Creation)
    # Since commit=False, if this block raises an exception, the transaction will rollback (or not be committed)
    if treatment.consumedMaterials:
        try:
            for item in treatment.consumedMaterials:
                inventory_service.consume_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id,
                    reference_id=f"TREATMENT:{created_treatment.id}",  # Link usage to treatment
                    db=db,
                )
        except Exception as e:
            logger.error(f"Stock Consumption Error: {e}", exc_info=True)
            error_msg = str(e)

            # Handle CONFIRM_OPEN_REQUIRED as business logic error (409), not server error (500)
            if error_msg.startswith("CONFIRM_OPEN_REQUIRED:"):
                parts = error_msg.split(":", 2)
                stock_item_id = int(parts[1]) if len(parts) > 1 else None
                material_info = parts[2] if len(parts) > 2 else "Unknown"
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "CONFIRM_OPEN_REQUIRED",
                        "stock_item_id": stock_item_id,
                        "material_info": material_info,
                        "message": f"يجب فتح عبوة جديدة قبل الاستخدام: {material_info}",
                    },
                )

            raise HTTPException(status_code=500, detail=f"Stock Error: {error_msg}")

    # If we got here, verification/consumption passed (or there were no materials)
    db.commit()
    db.refresh(created_treatment)

    log_admin_action(
        db=db,
        admin_user=current_user,
        action="create",
        entity_type="treatment",
        entity_id=created_treatment.id,
        details=f"Treatment '{treatment.procedure}' for patient {treatment.patient_id}",
    )

    return created_treatment


@router.put("/{treatment_id}", response_model=schemas.Treatment)
def update_treatment(
    treatment_id: int,
    treatment: schemas.TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Update a treatment record."""
    # 0. Stock Validation (Pre-Check)
    if treatment.consumedMaterials:
        errors = []
        for item in treatment.consumedMaterials:
            is_valid, available, mat_name = inventory_service.validate_stock(
                material_id=item.material_id,
                quantity=item.quantity,
                tenant_id=current_user.tenant_id,
                db=db,
            )
            if not is_valid:
                errors.append(
                    f"{mat_name} (Need: {item.quantity}, Available: {available})"
                )

        if errors:
            raise HTTPException(
                status_code=400,
                detail="فشل حفظ العلاج بسبب نقص المخزون: " + " | ".join(errors),
            )

    updated_treatment = crud.update_treatment(
        db, treatment_id, treatment, current_user.tenant_id, commit=False
    )

    # Post-Update Consume
    if treatment.consumedMaterials:
        try:
            for item in treatment.consumedMaterials:
                inventory_service.consume_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id,
                    reference_id=f"TREATMENT:{treatment_id}",  # Link usage to treatment
                    db=db,
                )
        except Exception as e:
            logger.error(f"Stock Consumption Error during update: {e}", exc_info=True)
            error_msg = str(e)

            # Handle CONFIRM_OPEN_REQUIRED as business logic error (409), not server error (500)
            if error_msg.startswith("CONFIRM_OPEN_REQUIRED:"):
                parts = error_msg.split(":", 2)
                stock_item_id = int(parts[1]) if len(parts) > 1 else None
                material_info = parts[2] if len(parts) > 2 else "Unknown"
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "CONFIRM_OPEN_REQUIRED",
                        "stock_item_id": stock_item_id,
                        "material_info": material_info,
                        "message": f"يجب فتح عبوة جديدة قبل الاستخدام: {material_info}",
                    },
                )

            raise HTTPException(status_code=500, detail=f"Stock Error: {error_msg}")

    # Commit after stock consumption
    db.commit()
    db.refresh(updated_treatment)

    return updated_treatment


@router.delete("/{treatment_id}")
def delete_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete a treatment record."""
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="treatment",
        entity_id=treatment_id,
        details=f"Deleted treatment #{treatment_id}",
    )
    return crud.delete_treatment(db, treatment_id, current_user.tenant_id)


# --- Tooth Status ---
@router.post("/tooth_status/", response_model=schemas.ToothStatus)
def update_tooth_status(
    status: schemas.ToothStatusCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Update tooth status in dental chart."""
    patient = crud.get_patient(db, status.patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.update_tooth_status(db, status, current_user.tenant_id)
