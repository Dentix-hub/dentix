import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List

from .. import schemas, models
from ..database import get_db
from ..core.permissions import require_permission, Permission
from ..services.inventory_service import inventory_service
from backend.core.response import StandardResponse, success_response
from ..models import inventory as inv_models
from ..models import clinical as clinical_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# --- WAREHOUSES ---
@router.post("/warehouses", response_model=StandardResponse[schemas.inventory.WarehouseRead])
def create_warehouse(
    warehouse: schemas.inventory.WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Create a new Warehouse"""
    return success_response(data=inventory_service.create_warehouse(
        warehouse, current_user.tenant_id or 1, db
    ), message="Warehouse created")


@router.get("/warehouses", response_model=StandardResponse[List[schemas.inventory.WarehouseRead]])
def get_warehouses(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    return success_response(data=inventory_service.get_warehouses(current_user.tenant_id or 1, db))


@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Delete a warehouse (must be empty)"""

    try:
        inventory_service.delete_warehouse(
            warehouse_id, current_user.tenant_id or 1, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- MATERIAL CATEGORIES ---
@router.get("/categories", response_model=StandardResponse[List[schemas.inventory.MaterialCategoryOut]])
def get_material_categories(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all material categories (global list)"""
    categories = db.query(inv_models.MaterialCategory).all()
    return success_response(data=categories)


@router.get("/categories/{category_id}/materials", response_model=StandardResponse[List[schemas.inventory.MaterialRead]])
def get_category_materials(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get clinic materials in a specific category"""
    tenant_id = current_user.tenant_id or 1
    materials = (
        db.query(inv_models.Material)
        .filter(
            inv_models.Material.category_id == category_id,
            inv_models.Material.tenant_id == tenant_id,
        )
        .all()
    )
    return success_response(data=materials)


# --- MATERIALS ---
@router.post("/materials", response_model=StandardResponse[schemas.inventory.MaterialRead])
def create_material(
    material: schemas.inventory.MaterialCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    return success_response(data=inventory_service.create_material(material, current_user.tenant_id or 1, db), message="Material created")


@router.get("/materials", response_model=StandardResponse[List[schemas.inventory.MaterialRead]])
def get_materials(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    return success_response(data=inventory_service.get_materials(current_user.tenant_id or 1, db))


@router.put("/materials/{material_id}", response_model=StandardResponse[schemas.inventory.MaterialRead])
def update_material(
    material_id: int,
    data: schemas.inventory.MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Update material details"""

    try:
        return success_response(data=inventory_service.update_material(
            material_id, data, current_user.tenant_id or 1, db
        ), message="Material updated")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Delete material if no stock/history exists"""

    try:
        inventory_service.delete_material(material_id, current_user.tenant_id or 1, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"delete_material failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# --- STOCK ---
@router.get("/stock", response_model=StandardResponse[List[schemas.inventory.MaterialStockSummary]])
def get_stock_summary(
    warehouse_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get stock summary grouped by material"""
    return success_response(data=inventory_service.get_material_stock_summary(
        current_user.tenant_id or 1, warehouse_id, db
    ))


@router.post("/receive", response_model=StandardResponse[schemas.inventory.StockItemRead])
def receive_stock(
    data: schemas.inventory.StockReceiveRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Receive new stock (Purchase)"""
    return success_response(data=inventory_service.add_stock(
        material_id=data.material_id,
        warehouse_id=data.warehouse_id,
        batch_data=data.batch,
        quantity=data.quantity,
        tenant_id=current_user.tenant_id or 1,
        user_id=current_user.id,
        db=db,
    ), message="Stock received")


@router.post("/consume", response_model=StandardResponse[dict])
def consume_stock(
    items: List[schemas.inventory.ConsumptionItem],
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """
    Consumes multiple items.
    """
    total_movements = 0
    tenant_id = current_user.tenant_id or 1

    # Process sequentially
    for item in items:
        try:
            movements = inventory_service.consume_stock(
                material_id=item.material_id,
                quantity=item.quantity,
                tenant_id=tenant_id,
                user_id=current_user.id,
                batch_id=item.batch_id,
                db=db,
            )
            total_movements += len(movements)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return success_response(data={"movements_count": total_movements}, message="Stock consumed")


@router.get("/alerts/expiry", response_model=StandardResponse[List[dict]])
def get_expiry_alerts(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """
    Get batches expiring within 'days' (default 30).
    """
    return success_response(data=inventory_service.get_expiry_alerts(
        current_user.tenant_id or 1, days=days, db=db
    ))


@router.post("/transfer", response_model=StandardResponse[schemas.inventory.StockMovementRead])
def transfer_stock(
    data: schemas.inventory.StockTransferRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Transfer stock between warehouses"""

    try:
        move = inventory_service.transfer_stock(
            stock_item_id=data.stock_item_id,
            target_warehouse_id=data.target_warehouse_id,
            quantity=data.quantity,
            tenant_id=current_user.tenant_id or 1,
            user_id=current_user.id,
            db=db,
        )
        return success_response(data=move, message="Stock transferred")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


from ..services.inventory_learning_service import InventoryLearningService


@router.post("/sessions", response_model=StandardResponse[schemas.inventory.MaterialSessionRead])
def open_session(
    data: schemas.inventory.MaterialSessionCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Open a new material session (Explicit Approval)"""
    try:
        session = inventory_service.open_session(
            data.stock_item_id, current_user.id, db
        )
        return success_response(data=session, message="Session opened")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/close", response_model=StandardResponse[dict])
def close_material_session(
    session_id: int,
    data: schemas.inventory.SessionCloseRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """
    Close a material session.
    - DIVISIBLE: Package is fully consumed, stock zeroes out
    - NON_DIVISIBLE: Remaining quantity stays, session just closes
    """
    try:
        session = (
            db.query(inv_models.MaterialSession)
            .options(
                joinedload(inv_models.MaterialSession.stock_item)
                .joinedload(inv_models.StockItem.batch)
                .joinedload(inv_models.Batch.material)
            )
            .filter(inv_models.MaterialSession.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status == "CLOSED":
            return success_response(data={
                "success": True,
                "message": "Session already closed",
                "already_closed": True,
            })

        # Get material type
        material = (
            session.stock_item.batch.material
            if session.stock_item and session.stock_item.batch
            else None
        )
        material_type = material.type if material else "NON_DIVISIBLE"

        if material_type == "DIVISIBLE":
            # DIVISIBLE: Package is fully consumed
            # Calculate consumption from packaging_ratio
            total_consumed = data.total_consumed
            if total_consumed is None:
                total_consumed = material.packaging_ratio if material else 1.0

            # Zero out stock (package depleted)
            session.stock_item.quantity = 0

            # Close session and trigger learning
            learning_service = InventoryLearningService(db)
            learning_service.close_session(
                session_id, float(total_consumed), current_user.id
            )

            return success_response(data={
                "success": True,
                "message": "جلسة المادة القابلة للتجزئة تم إغلاقها - العبوة استهلكت بالكامل",
                "material_type": "DIVISIBLE",
                "total_consumed": total_consumed,
                "remaining": 0,
            })
        else:
            # NON_DIVISIBLE: Just close session, keep remaining quantity
            session.status = "CLOSED"
            session.closed_at = datetime.utcnow()

            remaining = session.stock_item.quantity if session.stock_item else 0
            db.commit()

            return success_response(data={
                "success": True,
                "message": f"تم إغلاق الجلسة - المتبقي: {remaining} وحدة",
                "material_type": "NON_DIVISIBLE",
                "remaining": remaining,
            })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("An exception occurred", exc_info=True)
        raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")


@router.get(
    "/sessions/active", response_model=StandardResponse[List[schemas.inventory.MaterialSessionRead]]
)
def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all active sessions for current tenant"""
    tenant_id = current_user.tenant_id or 1

    # We join StockItem to filter by tenant
    # Use joinedload to ensure nested batch/material info is available for frontend
    sessions = (
        db.query(inv_models.MaterialSession)
        .options(
            joinedload(inv_models.MaterialSession.stock_item)
            .joinedload(inv_models.StockItem.batch)
            .joinedload(inv_models.Batch.material)
        )
        .join(inv_models.StockItem)
        .filter(
            inv_models.MaterialSession.status == "ACTIVE",
            inv_models.StockItem.tenant_id == tenant_id,
        )
        .all()
    )
    return success_response(data=sessions)


@router.delete("/weights/{weight_id}", status_code=204)
def delete_procedure_weight(
    weight_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Delete a procedure material weight rule"""

    weight = (
        db.query(inv_models.ProcedureMaterialWeight)
        .filter(inv_models.ProcedureMaterialWeight.id == weight_id)
        .first()
    )
    if not weight:
        raise HTTPException(status_code=404, detail="Weight not found")

    db.delete(weight)
    db.commit()
    return None


@router.post("/weights", response_model=StandardResponse[schemas.inventory.ProcedureWeightRead])
def set_procedure_weight(
    data: schemas.inventory.ProcedureWeightUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Set weight for a procedure/material pair"""

    tenant_id = current_user.tenant_id or 1

    # Resolve Procedure Name -> ID
    proc = (
        db.query(clinical_models.Procedure)
        .filter(
            clinical_models.Procedure.name == data.procedure_name,
            (clinical_models.Procedure.tenant_id == tenant_id)
            | (clinical_models.Procedure.tenant_id is None),
        )
        .first()
    )

    if not proc:
        raise HTTPException(
            status_code=404, detail=f"Procedure '{data.procedure_name}' not found"
        )

    # Find existing weight or create
    weight_obj = (
        db.query(inv_models.ProcedureMaterialWeight)
        .filter(
            inv_models.ProcedureMaterialWeight.procedure_id == proc.id,
            inv_models.ProcedureMaterialWeight.material_id == data.material_id,
            inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
        )
        .first()
    )

    if weight_obj:
        weight_obj.weight = data.weight
    else:
        weight_obj = inv_models.ProcedureMaterialWeight(
            tenant_id=tenant_id,
            procedure_id=proc.id,
            material_id=data.material_id,
            weight=data.weight,
        )
        db.add(weight_obj)

    db.commit()
    db.refresh(weight_obj)
    return success_response(data=weight_obj, message="Procedure weight updated")


@router.get("/weights", response_model=StandardResponse[List[schemas.inventory.ProcedureWeightRead]])
def get_procedure_weights(
    material_id: int = None,
    procedure_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all procedure weights (filter by material OR procedure)"""
    tenant_id = current_user.tenant_id or 1  # Safe-dev fallback
    query = db.query(inv_models.ProcedureMaterialWeight).filter(
        or_(
            inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
            inv_models.ProcedureMaterialWeight.tenant_id.is_(None),  # Global defaults
        )
    )

    if material_id:
        query = query.filter(
            inv_models.ProcedureMaterialWeight.material_id == material_id
        )

    if procedure_id:
        query = query.filter(
            inv_models.ProcedureMaterialWeight.procedure_id == procedure_id
        )

    return success_response(data=query.all())


@router.get(
    "/materials/{material_id}/stock",
    response_model=StandardResponse[List[schemas.inventory.StockItemRead]],
)
def get_material_stock(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all stock items for a material"""
    tenant_id = current_user.tenant_id or 1

    # Return available stock items (quantity > 0) OR items that have an ACTIVE session
    # We join StockItem to filter by tenant

    # Subquery for active session stock IDs
    subquery = db.query(inv_models.MaterialSession.stock_item_id).filter(
        inv_models.MaterialSession.status == "ACTIVE"
    )

    items = (
        db.query(inv_models.StockItem)
        .join(inv_models.Batch)
        .filter(
            inv_models.Batch.material_id == material_id,
            inv_models.StockItem.tenant_id == tenant_id,
            (inv_models.StockItem.quantity > 0)
            | (inv_models.StockItem.id.in_(subquery)),
        )
        .all()
    )
    return success_response(data=items)
