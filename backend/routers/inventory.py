import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import or_, select, delete
from typing import List

from .. import schemas, models
from ..database import get_async_db
from ..core.permissions import require_permission, Permission
from ..services.inventory_service import inventory_service
from backend.core.response import StandardResponse, success_response
from ..models import inventory as inv_models
from ..models import clinical as clinical_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# --- WAREHOUSES ---
@router.post("/warehouses", response_model=StandardResponse[schemas.inventory.WarehouseRead])
async def create_warehouse(
    warehouse: schemas.inventory.WarehouseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Create a new Warehouse"""
    res = await inventory_service.create_warehouse(
        warehouse, current_user.tenant_id or 1, db
    )
    return success_response(data=res, message="Warehouse created")


@router.get("/warehouses", response_model=StandardResponse[List[schemas.inventory.WarehouseRead]])
async def get_warehouses(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    res = await inventory_service.get_warehouses(current_user.tenant_id or 1, db)
    return success_response(data=res)


@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Delete a warehouse (must be empty)"""
    try:
        await inventory_service.delete_warehouse(
            warehouse_id, current_user.tenant_id or 1, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- MATERIAL CATEGORIES ---
@router.post("/categories", response_model=StandardResponse[schemas.inventory.MaterialCategoryOut])
async def create_material_category(
    category: schemas.inventory.MaterialCategoryCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Create a new material category"""
    new_cat = inv_models.MaterialCategory(**category.model_dump())
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return success_response(data=new_cat, message="Category created")


@router.get("/categories", response_model=StandardResponse[List[schemas.inventory.MaterialCategoryOut]])
async def get_material_categories(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all material categories (global list)"""
    stmt = select(inv_models.MaterialCategory)
    categories = (await db.execute(stmt)).scalars().all()
    return success_response(data=categories)


@router.get("/categories/{category_id}/materials", response_model=StandardResponse[List[schemas.inventory.MaterialRead]])
async def get_category_materials(
    category_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get clinic materials in a specific category"""
    tenant_id = current_user.tenant_id or 1
    stmt = (
        select(inv_models.Material)
        .where(
            inv_models.Material.category_id == category_id,
            inv_models.Material.tenant_id == tenant_id,
        )
    )
    materials = (await db.execute(stmt)).scalars().all()
    return success_response(data=materials)


# --- MATERIALS ---
@router.post("/materials", response_model=StandardResponse[schemas.inventory.MaterialRead])
async def create_material(
    material: schemas.inventory.MaterialCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    res = await inventory_service.create_material(material, current_user.tenant_id or 1, db)
    return success_response(data=res, message="Material created")


@router.get("/materials", response_model=StandardResponse[List[schemas.inventory.MaterialRead]])
async def get_materials(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    res = await inventory_service.get_materials(current_user.tenant_id or 1, db)
    return success_response(data=res)


@router.put("/materials/{material_id}", response_model=StandardResponse[schemas.inventory.MaterialRead])
async def update_material(
    material_id: int,
    data: schemas.inventory.MaterialUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Update material details"""
    try:
        res = await inventory_service.update_material(
            material_id, data, current_user.tenant_id or 1, db
        )
        return success_response(data=res, message="Material updated")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Delete material if no stock/history exists"""
    try:
        await inventory_service.delete_material(material_id, current_user.tenant_id or 1, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"delete_material failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# --- STOCK ---
@router.get("/stock", response_model=StandardResponse[List[schemas.inventory.MaterialStockSummary]])
async def get_stock_summary(
    warehouse_id: int = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get stock summary grouped by material"""
    res = await inventory_service.get_material_stock_summary(
        current_user.tenant_id or 1, warehouse_id, db
    )
    return success_response(data=res)


@router.post("/receive", response_model=StandardResponse[schemas.inventory.StockItemRead])
async def receive_stock(
    data: schemas.inventory.StockReceiveRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Receive new stock (Purchase)"""
    res = await inventory_service.add_stock(
        material_id=data.material_id,
        warehouse_id=data.warehouse_id,
        batch_data=data.batch,
        quantity=data.quantity,
        tenant_id=current_user.tenant_id or 1,
        user_id=current_user.id,
        db=db,
    )
    return success_response(data=res, message="Stock received")


@router.post("/consume", response_model=StandardResponse[dict])
async def consume_stock(
    items: List[schemas.inventory.ConsumptionItem],
    db: AsyncSession = Depends(get_async_db),
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
            movements = await inventory_service.consume_stock(
                material_id=item.material_id,
                quantity=item.quantity,
                tenant_id=tenant_id,
                user_id=current_user.id,
                batch_id=item.batch_id,
                patient_id=item.patient_id,
                db=db,
            )
            total_movements += len(movements)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return success_response(data={"movements_count": total_movements}, message="Stock consumed")


@router.get("/alerts/expiry", response_model=StandardResponse[List[dict]])
async def get_expiry_alerts(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """
    Get batches expiring within 'days' (default 30).
    """
    res = await inventory_service.get_expiry_alerts(
        current_user.tenant_id or 1, days=days, db=db
    )
    return success_response(data=res)


@router.post("/transfer", response_model=StandardResponse[schemas.inventory.StockMovementRead])
async def transfer_stock(
    data: schemas.inventory.StockTransferRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Transfer stock between warehouses"""
    try:
        move = await inventory_service.transfer_stock(
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
async def open_session(
    data: schemas.inventory.MaterialSessionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Open a new material session (Explicit Approval)"""
    try:
        session = await inventory_service.open_session(
            data.stock_item_id, current_user.id, db=db
        )
        return success_response(data=session, message="Session opened")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/close", response_model=StandardResponse[dict])
async def close_material_session(
    session_id: int,
    data: schemas.inventory.SessionCloseRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """
    Close a material session.
    """
    try:
        stmt_sess = (
            select(inv_models.MaterialSession)
            .options(
                joinedload(inv_models.MaterialSession.stock_item)
                .joinedload(inv_models.StockItem.batch)
                .joinedload(inv_models.Batch.material)
            )
            .where(inv_models.MaterialSession.id == session_id)
        )
        result = await db.execute(stmt_sess)
        session = result.scalars().first()

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
            total_consumed = data.total_consumed
            if total_consumed is None:
                total_consumed = material.packaging_ratio if material else 1.0

            session.stock_item.quantity = 0

            learning_service = InventoryLearningService(db)
            await learning_service.close_session(
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
            session.status = "CLOSED"
            session.closed_at = datetime.now(timezone.utc)

            remaining = session.stock_item.quantity if session.stock_item else 0
            await db.commit()

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
async def get_active_sessions(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all active sessions for current tenant"""
    tenant_id = current_user.tenant_id or 1

    stmt = (
        select(inv_models.MaterialSession)
        .options(
            joinedload(inv_models.MaterialSession.stock_item)
            .joinedload(inv_models.StockItem.batch)
            .joinedload(inv_models.Batch.material)
            .joinedload(inv_models.Material.category),
            joinedload(inv_models.MaterialSession.stock_item)
            .joinedload(inv_models.StockItem.warehouse)
        )
        .join(inv_models.StockItem)
        .where(
            inv_models.MaterialSession.status == "ACTIVE",
            inv_models.StockItem.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return success_response(data=sessions)


@router.delete("/weights/{weight_id}", status_code=204)
async def delete_procedure_weight(
    weight_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Delete a procedure material weight rule"""
    stmt = select(inv_models.ProcedureMaterialWeight).where(inv_models.ProcedureMaterialWeight.id == weight_id)
    result = await db.execute(stmt)
    weight = result.scalars().first()

    if not weight:
        raise HTTPException(status_code=404, detail="Weight not found")

    await db.delete(weight)
    await db.commit()
    return None


@router.post("/weights", response_model=StandardResponse[schemas.inventory.ProcedureWeightRead])
async def set_procedure_weight(
    data: schemas.inventory.ProcedureWeightUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
):
    """Set weight for a procedure/material pair"""
    tenant_id = current_user.tenant_id or 1

    # Resolve Procedure Name -> ID
    stmt_proc = select(clinical_models.Procedure).where(
        clinical_models.Procedure.name == data.procedure_name,
        or_(
            clinical_models.Procedure.tenant_id == tenant_id,
            clinical_models.Procedure.tenant_id.is_(None)
        )
    )
    proc = (await db.execute(stmt_proc)).scalars().first()

    if not proc:
        raise HTTPException(
            status_code=404, detail=f"Procedure '{data.procedure_name}' not found"
        )

    # Find existing weight or create
    stmt_weight = select(inv_models.ProcedureMaterialWeight).where(
        inv_models.ProcedureMaterialWeight.procedure_id == proc.id,
        inv_models.ProcedureMaterialWeight.material_id == data.material_id,
        inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
    ).options(
        selectinload(inv_models.ProcedureMaterialWeight.procedure),
        selectinload(inv_models.ProcedureMaterialWeight.category)
    )
    weight_obj = (await db.execute(stmt_weight)).scalars().first()

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

    await db.commit()
    # Explicitly load relationships to avoid lazy loading issues
    stmt_refreshed = select(inv_models.ProcedureMaterialWeight).where(
        inv_models.ProcedureMaterialWeight.id == weight_obj.id
    ).options(
        selectinload(inv_models.ProcedureMaterialWeight.procedure),
        selectinload(inv_models.ProcedureMaterialWeight.category)
    )
    weight_obj = (await db.execute(stmt_refreshed)).scalars().first()
    return success_response(data=weight_obj, message="Procedure weight updated")


@router.get("/weights", response_model=StandardResponse[List[schemas.inventory.ProcedureWeightRead]])
async def get_procedure_weights(
    material_id: int = None,
    procedure_id: int = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all procedure weights (filter by material OR procedure)"""
    tenant_id = current_user.tenant_id or 1
    stmt = select(inv_models.ProcedureMaterialWeight).where(
        or_(
            inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
            inv_models.ProcedureMaterialWeight.tenant_id.is_(None),  # Global defaults
        )
    ).options(
        selectinload(inv_models.ProcedureMaterialWeight.procedure),
        selectinload(inv_models.ProcedureMaterialWeight.category)
    )

    if material_id:
        stmt = stmt.where(
            inv_models.ProcedureMaterialWeight.material_id == material_id
        )

    if procedure_id:
        stmt = stmt.where(
            inv_models.ProcedureMaterialWeight.procedure_id == procedure_id
        )

    result = await db.execute(stmt)
    weights = result.scalars().all()
    return success_response(data=weights)


@router.get(
    "/materials/{material_id}/stock",
    response_model=StandardResponse[List[schemas.inventory.StockItemRead]],
)
async def get_material_stock(
    material_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.INVENTORY_READ)),
):
    """Get all stock items for a material"""
    tenant_id = current_user.tenant_id or 1

    subquery = select(inv_models.MaterialSession.stock_item_id).where(
        inv_models.MaterialSession.status == "ACTIVE"
    )

    stmt = (
        select(inv_models.StockItem)
        .join(inv_models.Batch)
        .where(
            inv_models.Batch.material_id == material_id,
            inv_models.StockItem.tenant_id == tenant_id,
            or_(
                inv_models.StockItem.quantity > 0,
                inv_models.StockItem.id.in_(subquery)
            )
        )
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return success_response(data=items)
