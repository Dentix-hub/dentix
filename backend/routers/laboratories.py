"""
Router for Laboratory and Lab Order management
إدارة المعامل وطلبات التحاليل
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.core.response import success_response, StandardResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, delete
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone
from typing import List

from .. import models, schemas
from ..cache import cache_response, invalidate_cache
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission

router = APIRouter()

# Prefix for linking lab orders to treatments
TREATMENT_LINK_PREFIX = "Link:LabOrder:"


def _get_lab_procedure_name(work_type: str, material: str = None) -> str:
    """Generate procedure name for lab work treatment"""
    if material:
        return f"عمل معمل: {work_type} - {material}"
    return f"عمل معمل: {work_type}"


# Helper function with caching
@cache_response(ttl_seconds=300)  # Cache for 5 minutes
async def _get_cached_laboratories(db: AsyncSession, tenant_id: int):
    stmt = (
        select(models.Laboratory)
        .where(models.Laboratory.tenant_id == tenant_id)
        .order_by(models.Laboratory.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ==================== Laboratory Endpoints ====================


@router.get("/laboratories")
async def get_laboratories(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ))
):
    """Get all laboratories for current tenant (Cached for 5 min)"""
    labs = await _get_cached_laboratories(db, current_user.tenant_id)
    return success_response(labs)


@router.post("/laboratories")
async def create_laboratory(
    lab: schemas.LaboratoryCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Create a new laboratory"""
    db_lab = models.Laboratory(**lab.model_dump(), tenant_id=current_user.tenant_id)
    db.add(db_lab)
    await db.commit()
    await db.refresh(db_lab)
    # Invalidate cache
    invalidate_cache("_get_cached_laboratories")
    return success_response(db_lab)


@router.get("/laboratories/{lab_id}")
async def get_laboratory(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get a single laboratory by ID"""
    stmt = select(models.Laboratory).where(
        models.Laboratory.id == lab_id,
        models.Laboratory.tenant_id == current_user.tenant_id,
    )
    lab = (await db.execute(stmt)).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")
    return success_response(lab)


@router.put("/laboratories/{lab_id}")
async def update_laboratory(
    lab_id: int,
    lab_update: schemas.LaboratoryUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Update a laboratory"""
    stmt = select(models.Laboratory).where(
        models.Laboratory.id == lab_id,
        models.Laboratory.tenant_id == current_user.tenant_id,
    )
    lab = (await db.execute(stmt)).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    update_data = lab_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lab, key, value)

    await db.commit()
    await db.refresh(lab)
    invalidate_cache("_get_cached_laboratories")
    return success_response(lab)


@router.delete("/laboratories/{lab_id}")
async def delete_laboratory(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Delete a laboratory"""
    stmt = select(models.Laboratory).where(
        models.Laboratory.id == lab_id,
        models.Laboratory.tenant_id == current_user.tenant_id,
    )
    lab = (await db.execute(stmt)).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    await db.delete(lab)
    await db.commit()
    invalidate_cache("_get_cached_laboratories")
    return success_response(message="Laboratory deleted successfully")


# ==================== Lab Order Endpoints ====================


@router.get("/lab-orders")
async def get_lab_orders(
    laboratory_id: int = None,
    status: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all lab orders for current tenant with optional filtering"""
    stmt = (
        select(models.LabOrder)
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .options(selectinload(models.LabOrder.patient), selectinload(models.LabOrder.laboratory))
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False
        )
    )

    if laboratory_id:
        stmt = stmt.where(models.LabOrder.laboratory_id == laboratory_id)

    if status:
        stmt = stmt.where(models.LabOrder.status == status)

    stmt = stmt.order_by(models.LabOrder.order_date.desc())
    result = await db.execute(stmt)
    orders = result.scalars().all()

    # Add patient and lab names
    res_list = []
    for order in orders:
        order_dict = schemas.LabOrder.model_validate(order).model_dump()
        order_dict["patient_name"] = order.patient.name if order.patient else None
        order_dict["laboratory_name"] = (
            order.laboratory.name if order.laboratory else None
        )
        res_list.append(order_dict)
    return success_response(res_list)


@router.post("/lab-orders")
async def create_lab_order(
    order: schemas.LabOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Create a new lab order and automatically create linked treatment for billing"""
    # Verify patient exists and belongs to tenant
    stmt_patient = select(models.Patient).where(
        models.Patient.id == order.patient_id,
        models.Patient.tenant_id == current_user.tenant_id,
    )
    patient = (await db.execute(stmt_patient)).scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Verify laboratory exists and belongs to tenant
    stmt_lab = select(models.Laboratory).where(
        models.Laboratory.id == order.laboratory_id,
        models.Laboratory.tenant_id == current_user.tenant_id,
    )
    lab = (await db.execute(stmt_lab)).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    db_order = models.LabOrder(
        **order.model_dump(),
        tenant_id=current_user.tenant_id,
        doctor_id=current_user.id,  # Assign current user as the doctor
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)

    # === Auto-create linked Treatment for billing ===
    if db_order.price_to_patient and db_order.price_to_patient > 0:
        # Parse tooth_number to int if possible
        tooth_num = None
        if db_order.tooth_number:
            try:
                # Take first tooth if multiple (e.g., "11,12,13" -> 11)
                tooth_num = int(db_order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass

        linked_treatment = models.Treatment(
            patient_id=db_order.patient_id,
            tooth_number=tooth_num,
            diagnosis=f"تركيبة معملية - {lab.name}",
            procedure=_get_lab_procedure_name(db_order.work_type, db_order.material),
            doctor_id=db_order.doctor_id,
            cost=db_order.price_to_patient,
            discount=0.0,
            date=db_order.order_date,
            notes=f"{TREATMENT_LINK_PREFIX}{db_order.id}",
        )
        db.add(linked_treatment)
        await db.commit()

    # Return with names
    result = schemas.LabOrder.model_validate(db_order).model_dump()
    result["patient_name"] = patient.name
    result["laboratory_name"] = lab.name
    return success_response(result)


@router.get("/lab-orders/{order_id}")
async def get_lab_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get a single lab order by ID"""
    stmt = (
        select(models.LabOrder)
        .options(selectinload(models.LabOrder.patient), selectinload(models.LabOrder.laboratory))
        .where(
            models.LabOrder.id == order_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    )
    order = (await db.execute(stmt)).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    result = schemas.LabOrder.model_validate(order).model_dump()
    result["patient_name"] = order.patient.name if order.patient else None
    result["laboratory_name"] = order.laboratory.name if order.laboratory else None
    return success_response(result)


@router.put("/lab-orders/{order_id}")
async def update_lab_order(
    order_id: int,
    order_update: schemas.LabOrderUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Update a lab order and sync linked treatment"""
    stmt = (
        select(models.LabOrder)
        .options(selectinload(models.LabOrder.patient), selectinload(models.LabOrder.laboratory))
        .where(
            models.LabOrder.id == order_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    )
    order = (await db.execute(stmt)).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    update_data = order_update.model_dump(exclude_unset=True)

    # If status is changing to completed, set received_date
    if update_data.get("status") == "completed" and order.status != "completed":
        update_data["received_date"] = datetime.now(timezone.utc)

    for key, value in update_data.items():
        setattr(order, key, value)

    # Self-heal: If doctor_id is missing, assign current user
    if not order.doctor_id:
        order.doctor_id = current_user.id

    await db.commit()
    await db.refresh(order)

    # === Sync linked Treatment for billing ===
    link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
    stmt_treatment = select(models.Treatment).where(models.Treatment.notes.contains(link_note))
    linked_treatment = (await db.execute(stmt_treatment)).scalars().first()

    if linked_treatment:
        # Update existing linked treatment
        linked_treatment.cost = order.price_to_patient or 0
        linked_treatment.procedure = _get_lab_procedure_name(
            order.work_type, order.material
        )
        linked_treatment.doctor_id = order.doctor_id  # Ensure doctor_id is synced
        if order.laboratory:
            linked_treatment.diagnosis = f"تركيبة معملية - {order.laboratory.name}"
        await db.commit()
    elif order.price_to_patient and order.price_to_patient > 0:
        # Create new linked treatment if price was added
        tooth_num = None
        if order.tooth_number:
            try:
                tooth_num = int(order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass

        lab_name = order.laboratory.name if order.laboratory else "معمل"
        new_treatment = models.Treatment(
            patient_id=order.patient_id,
            tooth_number=tooth_num,
            diagnosis=f"تركيبة معملية - {lab_name}",
            procedure=_get_lab_procedure_name(order.work_type, order.material),
            doctor_id=order.doctor_id,
            cost=order.price_to_patient,
            discount=0.0,
            date=order.order_date,
            notes=link_note,
        )
        db.add(new_treatment)
        await db.commit()

    result = schemas.LabOrder.model_validate(order).model_dump()
    result["patient_name"] = order.patient.name if order.patient else None
    result["laboratory_name"] = order.laboratory.name if order.laboratory else None
    return success_response(result)


@router.delete("/lab-orders/{order_id}")
async def delete_lab_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Delete a lab order and its linked treatment"""
    stmt = select(models.LabOrder).where(
        models.LabOrder.id == order_id,
        models.LabOrder.tenant_id == current_user.tenant_id,
    )
    order = (await db.execute(stmt)).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    # === Delete linked Treatment ===
    link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
    stmt_treatment = select(models.Treatment).where(models.Treatment.notes.contains(link_note))
    linked_treatment = (await db.execute(stmt_treatment)).scalars().first()
    if linked_treatment:
        await db.delete(linked_treatment)

    await db.delete(order)
    await db.commit()
    return success_response(message="Lab order deleted successfully")


@router.get("/patients/{patient_id}/lab_orders")
async def get_patient_lab_orders(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all lab orders for a specific patient"""
    # Verify patient exists and belongs to tenant
    stmt_patient = select(models.Patient).where(
        models.Patient.id == patient_id,
        models.Patient.tenant_id == current_user.tenant_id,
    )
    patient = (await db.execute(stmt_patient)).scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    stmt_orders = (
        select(models.LabOrder)
        .options(selectinload(models.LabOrder.laboratory))
        .where(models.LabOrder.patient_id == patient_id)
        .order_by(models.LabOrder.order_date.desc())
    )
    orders = (await db.execute(stmt_orders)).scalars().all()

    result = []
    for order in orders:
        order_dict = schemas.LabOrder.model_validate(order).model_dump()
        order_dict["patient_name"] = patient.name
        order_dict["laboratory_name"] = (
            order.laboratory.name if order.laboratory else None
        )
        result.append(order_dict)
    return success_response(result)


@router.get("/lab-orders/stats/summary")
async def get_lab_orders_stats(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ))
):
    """Get lab orders statistics"""
    base_query_stmt = (
        select(models.LabOrder)
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False
        )
    )

    total_orders = await db.scalar(select(func.count()).select_from(base_query_stmt.subquery())) or 0
    pending_orders = await db.scalar(
        select(func.count())
        .select_from(base_query_stmt.where(models.LabOrder.status == "pending").subquery())
    ) or 0
    in_progress_orders = await db.scalar(
        select(func.count())
        .select_from(base_query_stmt.where(models.LabOrder.status == "in_progress").subquery())
    ) or 0
    completed_orders = await db.scalar(
        select(func.count())
        .select_from(base_query_stmt.where(models.LabOrder.status == "completed").subquery())
    ) or 0

    stmt_cost = (
        select(func.sum(models.LabOrder.cost))
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False
        )
    )
    total_cost = await db.scalar(stmt_cost) or 0

    stmt_rev = (
        select(func.sum(models.LabOrder.price_to_patient))
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False
        )
    )
    total_revenue = await db.scalar(stmt_rev) or 0

    stmt_labs = (
        select(func.count(models.Laboratory.id))
        .where(
            models.Laboratory.tenant_id == current_user.tenant_id,
            models.Laboratory.is_active == True,
        )
    )
    total_labs = await db.scalar(stmt_labs) or 0

    return success_response({
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "in_progress_orders": in_progress_orders,
        "completed_orders": completed_orders,
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "profit": total_revenue - total_cost,
        "total_labs": total_labs,
    })


# ==================== Lab Financials & Stats ====================


@router.get("/laboratories/{lab_id}/stats")
async def get_lab_stats(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get detailed statistics for a specific laboratory including balance"""
    # Verify lab exists
    stmt_lab = select(models.Laboratory).where(
        models.Laboratory.id == lab_id,
        models.Laboratory.tenant_id == current_user.tenant_id,
    )
    lab = (await db.execute(stmt_lab)).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    # 1. Orders Stats
    base_query_stmt = select(models.LabOrder).where(
        models.LabOrder.laboratory_id == lab_id,
        models.LabOrder.tenant_id == current_user.tenant_id,
    )

    total_orders = await db.scalar(select(func.count()).select_from(base_query_stmt.subquery())) or 0
    pending_orders = await db.scalar(
        select(func.count())
        .select_from(base_query_stmt.where(models.LabOrder.status == "pending").subquery())
    ) or 0
    completed_orders = await db.scalar(
        select(func.count())
        .select_from(base_query_stmt.where(models.LabOrder.status == "completed").subquery())
    ) or 0

    # Financials from Orders
    stmt_cost = (
        select(func.sum(models.LabOrder.cost))
        .where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    )
    total_cost = await db.scalar(stmt_cost) or 0.0

    stmt_rev = (
        select(func.sum(models.LabOrder.price_to_patient))
        .where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    )
    total_revenue = await db.scalar(stmt_rev) or 0.0

    # 2. Payments Stats
    stmt_paid = (
        select(func.sum(models.LabPayment.amount))
        .where(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == current_user.tenant_id,
        )
    )
    total_paid = await db.scalar(stmt_paid) or 0.0

    balance = total_cost - total_paid

    return {
        "lab_id": lab_id,
        "lab_name": lab.name,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "balance": balance,
    }


@router.post("/laboratories/{lab_id}/payments")
async def create_lab_payment(
    lab_id: int,
    payment: schemas.LabPaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Record a payment to a laboratory"""
    # Verify lab exists
    stmt_lab = select(models.Laboratory).where(
        models.Laboratory.id == lab_id,
        models.Laboratory.tenant_id == current_user.tenant_id,
    )
    lab = (await db.execute(stmt_lab)).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    db_payment = models.LabPayment(
        **payment.model_dump(), tenant_id=current_user.tenant_id
    )
    # Ensure lab_id matches URL
    db_payment.laboratory_id = lab_id

    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    return success_response(db_payment)


@router.get("/laboratories/{lab_id}/payments")
async def get_lab_payments(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get payment history for a laboratory"""
    stmt = (
        select(models.LabPayment)
        .where(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == current_user.tenant_id,
        )
        .order_by(models.LabPayment.date.desc())
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()
    return success_response(payments)
