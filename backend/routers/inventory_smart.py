import os
from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from ..database import get_async_db
from ..schemas import User
from ..core.permissions import require_permission, Permission
from ..core.tenant_context import require_tenant_id
from ..services.inventory_learning_service import InventoryLearningService
from ..services.material_resolution_service import MaterialResolutionService
from ..models import inventory as inv_models
from backend.core.response import StandardResponse, success_response, error_response

router = APIRouter(prefix="/inventory/smart", tags=["Inventory Smart"])


def _ensure_not_production():
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/suggestions/{procedure_id}")
async def get_material_suggestions(
    procedure_id: int,
    patient_age: Optional[int] = None,
    doctor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get smart material suggestions for a procedure."""
    tenant_id = require_tenant_id(current_user)
    service = InventoryLearningService(db)

    effective_doctor_id = doctor_id
    if not effective_doctor_id and current_user.role == "doctor":
        effective_doctor_id = current_user.id

    suggestions = await service.get_suggested_materials(
        procedure_id=procedure_id,
        tenant_id=tenant_id,
        doctor_id=effective_doctor_id,
    )
    return success_response(data=suggestions)


@router.get("/suggestions-categories/{procedure_id}", response_model=StandardResponse[List[Dict]])
async def get_category_based_suggestions(
    procedure_id: int,
    doctor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get category-based material suggestions for a procedure."""
    tenant_id = require_tenant_id(current_user)
    try:
        service = MaterialResolutionService(db)

        effective_doctor_id = doctor_id
        if not effective_doctor_id and current_user.role == "doctor":
            effective_doctor_id = current_user.id

        suggestions = await service.resolve_materials_for_procedure(
            procedure_id=procedure_id,
            tenant_id=tenant_id,
        )
        return success_response(data=suggestions)
    except HTTPException:
        raise
    except Exception:
        logging.exception("Failed to resolve materials")
        return error_response(
            message="Failed to resolve materials",
            status_code=500
        )


@router.post("/check-availability")
async def check_availability(
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Pre-flight check for tenant-owned materials availability."""
    tenant_id = require_tenant_id(current_user)
    materials = request_data.get("materials", [])
    patient_id = request_data.get("patient_id")
    results = []

    for item in materials:
        mat_id = item.get("material_id")
        qty_needed = item.get("quantity", 0)

        material_result = await db.execute(
            select(inv_models.Material).where(
                inv_models.Material.id == mat_id,
                inv_models.Material.tenant_id == tenant_id,
                inv_models.Material.is_deleted == False,  # noqa: E712
            )
        )
        material = material_result.scalars().first()
        if not material:
            results.append(
                {
                    "material_id": mat_id,
                    "material_name": "Unknown Material",
                    "material_type": "UNKNOWN",
                    "available": 0,
                    "required": qty_needed,
                    "status": "CRITICAL",
                    "message": "Material not found",
                    "has_active_session": False,
                    "current_uses": 0,
                    "session_id": None,
                }
            )
            continue

        material_name = material.name
        material_type = material.type

        session_base_query = (
            select(inv_models.MaterialSession)
            .join(inv_models.StockItem)
            .join(inv_models.Batch)
            .where(
                inv_models.Batch.material_id == mat_id,
                inv_models.StockItem.tenant_id == tenant_id,
                inv_models.MaterialSession.status == "ACTIVE",
            )
        )

        if patient_id:
            patient_session_res = await db.execute(
                session_base_query.where(inv_models.MaterialSession.patient_id == patient_id)
            )
            patient_session = patient_session_res.scalars().first()
            if patient_session:
                active_session = patient_session
            else:
                general_session_res = await db.execute(
                    session_base_query.where(inv_models.MaterialSession.patient_id.is_(None))
                )
                active_session = general_session_res.scalars().first()
        else:
            active_session_res = await db.execute(session_base_query)
            active_session = active_session_res.scalars().first()

        has_active_session = active_session is not None
        current_uses = active_session.current_uses if active_session else 0
        session_id = active_session.id if active_session else None

        if has_active_session:
            total_available = float("inf")
        else:
            stock_items_res = await db.execute(
                select(inv_models.StockItem)
                .join(inv_models.Batch)
                .where(
                    inv_models.StockItem.tenant_id == tenant_id,
                    inv_models.Batch.material_id == mat_id,
                    inv_models.StockItem.quantity > 0,
                )
            )
            stock_items = stock_items_res.scalars().all()
            total_available = sum(s.quantity for s in stock_items)

        status_value = "OK"
        message = ""

        if has_active_session:
            message = "جلسة مفتوحة (استهلاك افتراضي)"
            if patient_id and active_session.patient_id == patient_id:
                message = "جلسة نشطة لهذا المريض"
        elif total_available == 0:
            status_value = "CRITICAL"
            message = "Out of stock"
        elif total_available < qty_needed:
            status_value = "WARNING"
            message = f"Insufficient stock (Available: {total_available})"

        results.append(
            {
                "material_id": mat_id,
                "material_name": material_name,
                "material_type": material_type,
                "available": total_available if total_available != float("inf") else 999,
                "required": qty_needed,
                "status": status_value,
                "message": message,
                "has_active_session": has_active_session,
                "current_uses": current_uses,
                "session_id": session_id,
            }
        )

    return success_response(data=results)


@router.get("/debug/logs", tags=["debug"])
def get_suggestion_logs(
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    _ensure_not_production()
    """Debug endpoint to see what's happening with suggestions."""

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_path = os.path.join(project_root, "suggestion_debug.log")
    if not os.path.exists(log_path):
        return success_response(data={"message": "No logs found"})

    with open(log_path, "r", encoding="utf-8") as f:
        return success_response(data={"logs": f.read().splitlines()[-100:]})
