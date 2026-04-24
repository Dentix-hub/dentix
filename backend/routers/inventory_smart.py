import os
from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..database import get_db
from ..schemas import User
from ..core.permissions import require_permission, Permission
from ..services.inventory_learning_service import InventoryLearningService
from ..services.material_resolution_service import MaterialResolutionService
from ..models import inventory as inv_models
from backend.core.response import StandardResponse, success_response, error_response
from .auth import get_current_user

router = APIRouter(prefix="/inventory/smart", tags=["Inventory Smart"])


def _ensure_not_production():
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/suggestions/{procedure_id}")
def get_material_suggestions(
    procedure_id: int,
    patient_age: Optional[int] = None,
    doctor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """
    Get smart material suggestions for a procedure.
    """
    service = InventoryLearningService(db)

    # Use current doctor if not specified and user is a doctor
    effective_doctor_id = doctor_id
    if not effective_doctor_id and current_user.role == "doctor":
        effective_doctor_id = current_user.id

    suggestions = service.get_suggested_materials(
        procedure_id=procedure_id,
        tenant_id=current_user.tenant_id,
        doctor_id=effective_doctor_id,
    )
    return {"data": suggestions, "success": True}


@router.get("/suggestions-categories/{procedure_id}", response_model=StandardResponse[List[Dict]])
def get_category_based_suggestions(
    procedure_id: int,
    doctor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """
    Get category-based material suggestions for a procedure.
    Returns materials grouped by category with active session status.
    """
    try:
        service = MaterialResolutionService(db)
        if not current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant access required")
        tenant_id = current_user.tenant_id

        # Use current doctor if not specified and user is a doctor
        effective_doctor_id = doctor_id
        if not effective_doctor_id and current_user.role == "doctor":
            effective_doctor_id = current_user.id

        suggestions = service.resolve_materials_for_procedure(
            procedure_id=procedure_id,
            tenant_id=tenant_id,
        )
        return success_response(data=suggestions)
    except Exception:
        logging.exception("Failed to resolve materials")
        return error_response(
            message="Failed to resolve materials",
            status_code=500
        )


@router.post("/check-availability")
def check_availability(
    materials: List[Dict[str, Any]],  # [{material_id, quantity}]
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """
    Pre-flight check for materials availability.
    Returns warnings if stock is low or expired.
    FIXED: Includes items with Active Sessions (quantity may be 0 but usable)
    """
    results = []

    for item in materials:
        mat_id = item.get("material_id")
        qty_needed = item.get("quantity", 0)

        # First, get material info directly
        material = (
            db.query(inv_models.Material)
            .filter(inv_models.Material.id == mat_id)
            .first()
        )
        material_name = material.name if material else "Unknown Material"

        # Check for active sessions for this material (virtual stock for divisible items)
        has_active_session = (
            db.query(inv_models.MaterialSession)
            .join(inv_models.StockItem)
            .join(inv_models.Batch)
            .filter(
                inv_models.Batch.material_id == mat_id,
                inv_models.MaterialSession.status == "ACTIVE",
            )
            .count()
            > 0
        )

        # Get total available stock (include 0-quantity items if active session exists)
        if has_active_session:
            # If active session, we don't need to check quantity - it's virtual consumption
            total_available = float("inf")  # Virtually unlimited while session is open
        else:
            stock_items = (
                db.query(inv_models.StockItem)
                .join(inv_models.Batch)
                .filter(
                    inv_models.StockItem.tenant_id == current_user.tenant_id,
                    inv_models.Batch.material_id == mat_id,
                    inv_models.StockItem.quantity > 0,
                )
                .all()
            )
            total_available = sum(s.quantity for s in stock_items)

        status = "OK"
        message = ""

        if has_active_session:
            # Material has active session - always OK (virtual consumption)
            status = "OK"
            message = "جلسة مفتوحة (استهلاك افتراضي)"
        elif total_available == 0:
            status = "CRITICAL"
            message = "Out of stock"
        elif total_available < qty_needed:
            status = "WARNING"
            message = f"Insufficient stock (Available: {total_available})"

        results.append(
            {
                "material_id": mat_id,
                "material_name": material_name,
                "available": total_available
                if total_available != float("inf")
                else 999,
                "required": qty_needed,
                "status": status,
                "message": message,
                "has_active_session": has_active_session,
            }
        )

    return {"data": results, "success": True}
@router.get("/debug/logs", tags=["debug"])
def get_suggestion_logs():
    _ensure_not_production()
    """Debug endpoint to see what's happening with suggestions."""

    import os
    if not os.path.exists("suggestion_debug.log"):
        return {"message": "No logs found"}

    with open("suggestion_debug.log", "r", encoding="utf-8") as f:
        return {"logs": f.read().splitlines()[-100:]}  # Return last 100 lines
