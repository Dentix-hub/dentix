"""Laboratory and lab-order management."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models, schemas
from ..cache import cache_response, invalidate_cache
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response
from backend.database import get_async_db
from backend.services.patient_access_service import (
    ensure_patient_visible,
    visible_patient_ids_query,
)

router = APIRouter()
TREATMENT_LINK_PREFIX = "Link:LabOrder:"


def _get_lab_procedure_name(work_type: str, material: str = None) -> str:
    if material:
        return f"عمل معمل: {work_type} - {material}"
    return f"عمل معمل: {work_type}"


def _linked_treatment_stmt(tenant_id: int, order_id: int):
    """Return the exact treatment link query for one lab order.

    Link notes are stored as a dedicated marker, so substring matching is unsafe:
    order 1 must never match the marker for order 10 or 11.
    """
    link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
    return select(models.Treatment).where(
        models.Treatment.tenant_id == tenant_id,
        models.Treatment.notes == link_note,
    )


@cache_response(ttl_seconds=300)
async def _get_cached_laboratories(db: AsyncSession, tenant_id: int):
    stmt = (
        select(models.Laboratory)
        .where(models.Laboratory.tenant_id == tenant_id)
        .order_by(models.Laboratory.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/laboratories")
async def get_laboratories(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    labs = await _get_cached_laboratories(db, current_user.tenant_id)
    return success_response(labs)


@router.post("/laboratories")
async def create_laboratory(
    lab: schemas.LaboratoryCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    db_lab = models.Laboratory(**lab.model_dump(), tenant_id=current_user.tenant_id)
    db.add(db_lab)
    await db.commit()
    await db.refresh(db_lab)
    invalidate_cache("_get_cached_laboratories")
    return success_response(db_lab)


@router.get("/laboratories/{lab_id}")
async def get_laboratory(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
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
    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")
    for key, value in lab_update.model_dump(exclude_unset=True).items():
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
    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")
    await db.delete(lab)
    await db.commit()
    invalidate_cache("_get_cached_laboratories")
    return success_response(message="Laboratory deleted successfully")


@router.get("/lab-orders")
async def get_lab_orders(
    laboratory_id: int = None,
    status: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    visible_ids = await visible_patient_ids_query(db, current_user)
    stmt = (
        select(models.LabOrder)
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .options(
            selectinload(models.LabOrder.patient),
            selectinload(models.LabOrder.laboratory),
        )
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.LabOrder.patient_id.in_(visible_ids),
        )
    )
    if laboratory_id:
        stmt = stmt.where(models.LabOrder.laboratory_id == laboratory_id)
    if status:
        stmt = stmt.where(models.LabOrder.status == status)
    stmt = stmt.order_by(models.LabOrder.order_date.desc())
    orders = (await db.execute(stmt)).scalars().all()

    result = []
    for order in orders:
        order_dict = schemas.LabOrder.model_validate(order).model_dump()
        order_dict["patient_name"] = order.patient.name if order.patient else None
        order_dict["laboratory_name"] = order.laboratory.name if order.laboratory else None
        result.append(order_dict)
    return success_response(result)


@router.post("/lab-orders")
async def create_lab_order(
    order: schemas.LabOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    if not order.patient_id:
        raise HTTPException(status_code=400, detail="Patient is required")
    await ensure_patient_visible(db, current_user, order.patient_id)

    patient = (
        await db.execute(
            select(models.Patient).where(
                models.Patient.id == order.patient_id,
                models.Patient.tenant_id == current_user.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
    ).scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == order.laboratory_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    db_order = models.LabOrder(
        **order.model_dump(),
        tenant_id=current_user.tenant_id,
        doctor_id=current_user.id,
    )
    db.add(db_order)
    # Generate the order id without persisting a half-complete order/treatment pair.
    await db.flush()

    if db_order.price_to_patient and db_order.price_to_patient > 0:
        tooth_num = None
        if db_order.tooth_number:
            try:
                tooth_num = int(db_order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass
        db.add(
            models.Treatment(
                patient_id=db_order.patient_id,
                tooth_number=tooth_num,
                diagnosis=f"تركيبة معملية - {lab.name}",
                procedure=_get_lab_procedure_name(db_order.work_type, db_order.material),
                doctor_id=db_order.doctor_id,
                cost=db_order.price_to_patient,
                discount=0.0,
                date=db_order.order_date,
                notes=f"{TREATMENT_LINK_PREFIX}{db_order.id}",
                tenant_id=current_user.tenant_id,
            )
        )

    await db.commit()
    await db.refresh(db_order)

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
    order = (
        await db.execute(
            select(models.LabOrder)
            .options(
                selectinload(models.LabOrder.patient),
                selectinload(models.LabOrder.laboratory),
            )
            .where(
                models.LabOrder.id == order_id,
                models.LabOrder.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    await ensure_patient_visible(db, current_user, order.patient_id, detail="Lab order not found")

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
    order = (
        await db.execute(
            select(models.LabOrder)
            .options(
                selectinload(models.LabOrder.patient),
                selectinload(models.LabOrder.laboratory),
            )
            .where(
                models.LabOrder.id == order_id,
                models.LabOrder.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    await ensure_patient_visible(db, current_user, order.patient_id, detail="Lab order not found")

    update_data = order_update.model_dump(exclude_unset=True)
    target_lab = None
    if update_data.get("laboratory_id"):
        target_lab = (
            await db.execute(
                select(models.Laboratory).where(
                    models.Laboratory.id == update_data["laboratory_id"],
                    models.Laboratory.tenant_id == current_user.tenant_id,
                )
            )
        ).scalars().first()
        if not target_lab:
            raise HTTPException(status_code=404, detail="Laboratory not found")

    if update_data.get("status") == "completed" and order.status != "completed":
        update_data["received_date"] = datetime.now(timezone.utc)
    for key, value in update_data.items():
        setattr(order, key, value)
    if not order.doctor_id:
        order.doctor_id = current_user.id

    # Keep the order and its linked treatment in one database transaction.
    await db.flush()

    linked_treatment = (
        await db.execute(_linked_treatment_stmt(current_user.tenant_id, order_id))
    ).scalars().first()
    active_lab = target_lab or order.laboratory

    if linked_treatment:
        linked_treatment.cost = order.price_to_patient or 0
        linked_treatment.procedure = _get_lab_procedure_name(order.work_type, order.material)
        linked_treatment.doctor_id = order.doctor_id
        if active_lab:
            linked_treatment.diagnosis = f"تركيبة معملية - {active_lab.name}"
    elif order.price_to_patient and order.price_to_patient > 0:
        tooth_num = None
        if order.tooth_number:
            try:
                tooth_num = int(order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass
        lab_name = active_lab.name if active_lab else "معمل"
        db.add(
            models.Treatment(
                patient_id=order.patient_id,
                tooth_number=tooth_num,
                diagnosis=f"تركيبة معملية - {lab_name}",
                procedure=_get_lab_procedure_name(order.work_type, order.material),
                doctor_id=order.doctor_id,
                cost=order.price_to_patient,
                discount=0.0,
                date=order.order_date,
                notes=f"{TREATMENT_LINK_PREFIX}{order_id}",
                tenant_id=current_user.tenant_id,
            )
        )

    await db.commit()
    await db.refresh(order)

    result = schemas.LabOrder.model_validate(order).model_dump()
    result["patient_name"] = order.patient.name if order.patient else None
    result["laboratory_name"] = active_lab.name if active_lab else None
    return success_response(result)


@router.delete("/lab-orders/{order_id}")
async def delete_lab_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    order = (
        await db.execute(
            select(models.LabOrder).where(
                models.LabOrder.id == order_id,
                models.LabOrder.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    await ensure_patient_visible(db, current_user, order.patient_id, detail="Lab order not found")

    linked_treatment = (
        await db.execute(_linked_treatment_stmt(current_user.tenant_id, order_id))
    ).scalars().first()
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
    await ensure_patient_visible(db, current_user, patient_id)
    patient = (
        await db.execute(
            select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.tenant_id == current_user.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
    ).scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    orders = (
        await db.execute(
            select(models.LabOrder)
            .options(selectinload(models.LabOrder.laboratory))
            .where(
                models.LabOrder.patient_id == patient_id,
                models.LabOrder.tenant_id == current_user.tenant_id,
            )
            .order_by(models.LabOrder.order_date.desc())
        )
    ).scalars().all()

    result = []
    for order in orders:
        order_dict = schemas.LabOrder.model_validate(order).model_dump()
        order_dict["patient_name"] = patient.name
        order_dict["laboratory_name"] = order.laboratory.name if order.laboratory else None
        result.append(order_dict)
    return success_response(result)


@router.get("/lab-orders/stats/summary")
async def get_lab_orders_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    base_query_stmt = (
        select(models.LabOrder)
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    total_orders = await db.scalar(select(func.count()).select_from(base_query_stmt.subquery())) or 0
    pending_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "pending").subquery()
        )
    ) or 0
    in_progress_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "in_progress").subquery()
        )
    ) or 0
    completed_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "completed").subquery()
        )
    ) or 0
    total_cost = await db.scalar(
        select(func.sum(models.LabOrder.cost))
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    ) or 0
    total_revenue = await db.scalar(
        select(func.sum(models.LabOrder.price_to_patient))
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    ) or 0
    total_labs = await db.scalar(
        select(func.count(models.Laboratory.id)).where(
            models.Laboratory.tenant_id == current_user.tenant_id,
            models.Laboratory.is_active == True,  # noqa: E712
        )
    ) or 0
    return success_response(
        {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "in_progress_orders": in_progress_orders,
            "completed_orders": completed_orders,
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "profit": total_revenue - total_cost,
            "total_labs": total_labs,
        }
    )


@router.get("/laboratories/{lab_id}/stats")
async def get_lab_stats(
    lab_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    base_query_stmt = select(models.LabOrder).where(
        models.LabOrder.laboratory_id == lab_id,
        models.LabOrder.tenant_id == current_user.tenant_id,
    )
    total_orders = await db.scalar(select(func.count()).select_from(base_query_stmt.subquery())) or 0
    pending_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "pending").subquery()
        )
    ) or 0
    completed_orders = await db.scalar(
        select(func.count()).select_from(
            base_query_stmt.where(models.LabOrder.status == "completed").subquery()
        )
    ) or 0
    total_cost = await db.scalar(
        select(func.sum(models.LabOrder.cost)).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    ) or 0.0
    total_revenue = await db.scalar(
        select(func.sum(models.LabOrder.price_to_patient)).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
    ) or 0.0
    total_paid = await db.scalar(
        select(func.sum(models.LabPayment.amount)).where(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == current_user.tenant_id,
        )
    ) or 0.0
    return {
        "lab_id": lab_id,
        "lab_name": lab.name,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "balance": total_cost - total_paid,
    }


@router.post("/laboratories/{lab_id}/payments")
async def create_lab_payment(
    lab_id: int,
    payment: schemas.LabPaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")
    db_payment = models.LabPayment(**payment.model_dump(), tenant_id=current_user.tenant_id)
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
    payments = (
        await db.execute(
            select(models.LabPayment)
            .where(
                models.LabPayment.laboratory_id == lab_id,
                models.LabPayment.tenant_id == current_user.tenant_id,
            )
            .order_by(models.LabPayment.date.desc())
        )
    ).scalars().all()
    return success_response(payments)
