"""Laboratory and lab-order management."""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models, schemas
from ..cache import cache_response, invalidate_cache
from backend.clinical.catalog import _PROCEDURE_DEFINITIONS
from backend.core.money import as_decimal, quantize_money
from backend.core.permissions import DOCTOR_ROLES, Permission, require_permission
from backend.core.response import success_response
from backend.database import get_async_db
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService
from backend.services.lab_service import (
    format_lab_order_dict,
    get_order_payment_map,
    get_unpaid_orders_count,
)
from backend.services.patient_access_service import (
    ensure_patient_visible,
    visible_patient_ids_query,
)
from backend.utils.tenant_time import utc_now_naive

router = APIRouter()
TREATMENT_LINK_PREFIX = "Link:LabOrder:"


def _get_lab_procedure_name(work_type: str, material: str = None) -> str:
    if material:
        return f"عمل معمل: {work_type} - {material}"
    return f"عمل معمل: {work_type}"


def _linked_treatment_stmt(tenant_id: int, order_id: int):
    """Return the exact treatment link query for one lab order."""
    return select(models.Treatment).where(
        models.Treatment.tenant_id == tenant_id,
        models.Treatment.notes == f"{TREATMENT_LINK_PREFIX}{order_id}",
    )


async def _valid_provider_id(db: AsyncSession, tenant_id: int, user_id: int | None):
    if not user_id:
        return None
    stmt = select(models.User.id).where(
        models.User.id == user_id,
        models.User.tenant_id == tenant_id,
        models.User.role.in_(DOCTOR_ROLES),
        models.User.is_active == True,  # noqa: E712
        models.User.is_deleted == False,  # noqa: E712
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _resolve_lab_provider_id(
    db: AsyncSession,
    current_user: models.User,
    patient: models.Patient,
):
    """Resolve the clinical provider without attributing nurse/staff activity as doctor revenue.

    Priority is the patient's explicit assigned provider, then a provider actor, then the
    most recent active treating provider. If none is trustworthy, leave attribution empty.
    """
    tenant_id = current_user.tenant_id

    assigned = await _valid_provider_id(db, tenant_id, patient.assigned_doctor_id)
    if assigned is not None:
        return assigned

    actor_role = str(getattr(current_user, "role", "")).lower()
    if actor_role in DOCTOR_ROLES:
        actor = await _valid_provider_id(db, tenant_id, current_user.id)
        if actor is not None:
            return actor

    stmt = (
        select(models.Treatment.doctor_id)
        .join(models.User, models.Treatment.doctor_id == models.User.id)
        .where(
            models.Treatment.patient_id == patient.id,
            models.Treatment.is_deleted == False,  # noqa: E712
            models.Treatment.doctor_id.isnot(None),
            models.User.tenant_id == tenant_id,
            models.User.role.in_(DOCTOR_ROLES),
            models.User.is_active == True,  # noqa: E712
            models.User.is_deleted == False,  # noqa: E712
        )
        .order_by(models.Treatment.date.desc(), models.Treatment.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


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

    order_ids = [o.id for o in orders]
    payment_map = await get_order_payment_map(db, current_user.tenant_id, order_ids)

    result = [
        format_lab_order_dict(
            order,
            paid_amount=payment_map.get(order.id, Decimal("0.00")),
            patient_name=order.patient.name if order.patient else None,
            laboratory_name=order.laboratory.name if order.laboratory else None,
        )
        for order in orders
    ]
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

    paid_now_d = quantize_money(as_decimal(getattr(order, "paid_now", 0)))
    cost_d = quantize_money(as_decimal(order.cost))
    if paid_now_d > 0 and paid_now_d > cost_d:
        raise HTTPException(
            status_code=400,
            detail="المبلغ المدفوع لا يمكن أن يتجاوز تكلفة الطلب",
        )

    if order.work_item_id is not None:
        if not await FeatureFlagService.is_feature_enabled(
            db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )
        work_item = (
            await db.execute(
                select(models.ClinicalWorkItem).where(
                    models.ClinicalWorkItem.id == order.work_item_id,
                    models.ClinicalWorkItem.tenant_id == current_user.tenant_id,
                    models.ClinicalWorkItem.patient_id == order.patient_id,
                )
            )
        ).scalars().first()
        if not work_item:
            raise HTTPException(status_code=404, detail="Clinical work item not found")

        # G12-M16: Handoff idempotency - return existing active lab order if present
        stmt_existing = (
            select(models.LabOrder)
            .options(
                selectinload(models.LabOrder.patient),
                selectinload(models.LabOrder.laboratory),
            )
            .where(
                models.LabOrder.tenant_id == current_user.tenant_id,
                models.LabOrder.work_item_id == order.work_item_id,
                models.LabOrder.status != "cancelled",
            )
            .order_by(models.LabOrder.id.desc())
        )
        existing_order = (await db.execute(stmt_existing)).scalars().first()
        if existing_order:
            payment_map = await get_order_payment_map(db, current_user.tenant_id, [existing_order.id])
            result = format_lab_order_dict(
                existing_order,
                paid_amount=payment_map.get(existing_order.id, Decimal("0.00")),
                patient_name=existing_order.patient.name if existing_order.patient else patient.name,
                laboratory_name=existing_order.laboratory.name if existing_order.laboratory else lab.name,
                is_existing=True,
            )
            return success_response(result)

    if order.treatment_id is not None:
        treatment = (
            await db.execute(
                select(models.Treatment).where(
                    models.Treatment.id == order.treatment_id,
                    models.Treatment.tenant_id == current_user.tenant_id,
                    models.Treatment.patient_id == order.patient_id,
                    models.Treatment.is_deleted == False,  # noqa: E712
                )
            )
        ).scalars().first()
        if not treatment:
            raise HTTPException(status_code=404, detail="Treatment not found")

        # D3 / Step 2: Idempotency - return existing active non-cancelled lab order if present
        stmt_existing = (
            select(models.LabOrder)
            .options(
                selectinload(models.LabOrder.patient),
                selectinload(models.LabOrder.laboratory),
            )
            .where(
                models.LabOrder.tenant_id == current_user.tenant_id,
                models.LabOrder.treatment_id == order.treatment_id,
                models.LabOrder.status != "cancelled",
            )
            .order_by(models.LabOrder.id.desc())
        )
        existing_order = (await db.execute(stmt_existing)).scalars().first()
        if existing_order:
            payment_map = await get_order_payment_map(db, current_user.tenant_id, [existing_order.id])
            result = format_lab_order_dict(
                existing_order,
                paid_amount=payment_map.get(existing_order.id, Decimal("0.00")),
                patient_name=existing_order.patient.name if existing_order.patient else patient.name,
                laboratory_name=existing_order.laboratory.name if existing_order.laboratory else lab.name,
                is_existing=True,
            )
            return success_response(result)

    provider_id = await _resolve_lab_provider_id(db, current_user, patient)
    db_order = models.LabOrder(
        **order.model_dump(exclude={"paid_now"}),
        tenant_id=current_user.tenant_id,
        doctor_id=provider_id,
    )
    db.add(db_order)
    await db.flush()

    if paid_now_d > 0:
        payment = models.LabPayment(
            laboratory_id=order.laboratory_id,
            lab_order_id=db_order.id,
            amount=paid_now_d,
            method="Cash",
            notes=f"دفعة طلب معمل #{db_order.id}",
            tenant_id=current_user.tenant_id,
        )
        db.add(payment)
        await db.flush()

    # G12-M08 & G12-M09 / R06 / D3: Decouple lab price from synthetic treatment creation.
    # When linked to a clinical work item or existing treatment, create 0 synthetic treatments!
    if order.work_item_id is None and order.treatment_id is None and db_order.price_to_patient and db_order.price_to_patient > 0:
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
                doctor_id=provider_id,
                cost=db_order.price_to_patient,
                discount=0.0,
                date=db_order.order_date,
                notes=f"{TREATMENT_LINK_PREFIX}{db_order.id}",
                tenant_id=current_user.tenant_id,
            )
        )

    await db.commit()
    await db.refresh(db_order)

    result = format_lab_order_dict(
        db_order,
        paid_amount=paid_now_d,
        patient_name=patient.name,
        laboratory_name=lab.name,
        is_existing=False,
    )
    return success_response(result)


# Register the static stats route before /lab-orders/{order_id}.
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
        select(func.coalesce(func.sum(models.LabOrder.cost), 0))
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.LabOrder.status != "cancelled",
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
    unpaid_orders_count = await get_unpaid_orders_count(db, current_user.tenant_id)
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
            "unpaid_orders_count": unpaid_orders_count,
        }
    )


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

    payment_map = await get_order_payment_map(db, current_user.tenant_id, [order.id])
    result = format_lab_order_dict(
        order,
        paid_amount=payment_map.get(order.id, Decimal("0.00")),
        patient_name=order.patient.name if order.patient else None,
        laboratory_name=order.laboratory.name if order.laboratory else None,
    )
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

    if update_data.get("work_item_id") is not None:
        if order.treatment_id is not None:
            raise HTTPException(
                status_code=400,
                detail="Cannot link work item to a treatment lab order",
            )
        if not await FeatureFlagService.is_feature_enabled(
            db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )
        work_item = (
            await db.execute(
                select(models.ClinicalWorkItem).where(
                    models.ClinicalWorkItem.id == update_data["work_item_id"],
                    models.ClinicalWorkItem.tenant_id == current_user.tenant_id,
                    models.ClinicalWorkItem.patient_id == order.patient_id,
                )
            )
        ).scalars().first()
        if not work_item:
            raise HTTPException(status_code=404, detail="Clinical work item not found")

    if update_data.get("treatment_id") is not None:
        if order.work_item_id is not None or update_data.get("work_item_id") is not None:
            raise HTTPException(
                status_code=400,
                detail="Cannot link treatment to a work item lab order",
            )
        treatment = (
            await db.execute(
                select(models.Treatment).where(
                    models.Treatment.id == update_data["treatment_id"],
                    models.Treatment.tenant_id == current_user.tenant_id,
                    models.Treatment.patient_id == order.patient_id,
                    models.Treatment.is_deleted == False,  # noqa: E712
                )
            )
        ).scalars().first()
        if not treatment:
            raise HTTPException(status_code=404, detail="Treatment not found")

        if update_data["treatment_id"] != order.treatment_id:
            stmt_conflict = select(models.LabOrder).where(
                models.LabOrder.tenant_id == current_user.tenant_id,
                models.LabOrder.treatment_id == update_data["treatment_id"],
                models.LabOrder.status != "cancelled",
                models.LabOrder.id != order.id,
            )
            conflict = (await db.execute(stmt_conflict)).scalars().first()
            if conflict:
                raise HTTPException(
                    status_code=409,
                    detail="An active lab order already exists for this treatment",
                )

    if update_data.get("status") == "completed" and order.status != "completed":
        update_data["received_date"] = utc_now_naive()

    if "cost" in update_data and update_data["cost"] is not None:
        total_paid = await db.scalar(
            select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
                models.LabPayment.tenant_id == current_user.tenant_id,
                models.LabPayment.lab_order_id == order.id,
            )
        )
        total_paid_d = quantize_money(as_decimal(total_paid))
        new_cost_d = quantize_money(as_decimal(update_data["cost"]))
        if new_cost_d < total_paid_d:
            raise HTTPException(
                status_code=400,
                detail=f"لا يمكن تقليل تكلفة الطلب ({new_cost_d}) إلى أقل من المبلغ المدفوع بالفعل ({total_paid_d})",
            )

    for key, value in update_data.items():
        setattr(order, key, value)

    valid_existing_provider = await _valid_provider_id(
        db, current_user.tenant_id, order.doctor_id
    )
    if valid_existing_provider is None:
        order.doctor_id = await _resolve_lab_provider_id(db, current_user, order.patient)

    # G12-M13: Sync shade/material updates to active care session observations
    if order.work_item_id and ("shade" in update_data or "material" in update_data):
        from backend.clinical.shade_material_sync import sync_lab_order_to_active_care_session_observations
        await sync_lab_order_to_active_care_session_observations(
            db, current_user.tenant_id, order, actor_user_id=current_user.id
        )

    await db.flush()

    linked_treatment = (
        await db.execute(_linked_treatment_stmt(current_user.tenant_id, order_id))
    ).scalars().first()
    active_lab = target_lab or order.laboratory
    patient_name = order.patient.name if order.patient else None
    lab_name = active_lab.name if active_lab else None

    if linked_treatment:
        linked_treatment.cost = order.price_to_patient or 0
        linked_treatment.procedure = _get_lab_procedure_name(order.work_type, order.material)
        linked_treatment.doctor_id = order.doctor_id
        if active_lab:
            linked_treatment.diagnosis = f"تركيبة معملية - {active_lab.name}"
    elif order.work_item_id is None and order.treatment_id is None and order.price_to_patient and order.price_to_patient > 0:
        tooth_num = None
        if order.tooth_number:
            try:
                tooth_num = int(order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass
        db_lab_name = active_lab.name if active_lab else "معمل"
        db.add(
            models.Treatment(
                patient_id=order.patient_id,
                tooth_number=tooth_num,
                diagnosis=f"تركيبة معملية - {db_lab_name}",
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

    payment_map = await get_order_payment_map(db, current_user.tenant_id, [order.id])
    result = format_lab_order_dict(
        order,
        paid_amount=payment_map.get(order.id, Decimal("0.00")),
        patient_name=patient_name,
        laboratory_name=lab_name,
    )
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

    has_payments = await db.scalar(
        select(func.count(models.LabPayment.id)).where(
            models.LabPayment.tenant_id == current_user.tenant_id,
            models.LabPayment.lab_order_id == order.id,
        )
    )
    if has_payments and has_payments > 0:
        raise HTTPException(
            status_code=409,
            detail="الطلب عليه دفعات، الغِ الطلب بدل حذفه",
        )

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

    order_ids = [o.id for o in orders]
    payment_map = await get_order_payment_map(db, current_user.tenant_id, order_ids)

    result = [
        format_lab_order_dict(
            order,
            paid_amount=payment_map.get(order.id, Decimal("0.00")),
            patient_name=patient.name,
            laboratory_name=order.laboratory.name if order.laboratory else None,
        )
        for order in orders
    ]
    return success_response(result)


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
            models.LabOrder.status != "cancelled",
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
    unpaid_orders_count = await get_unpaid_orders_count(db, current_user.tenant_id, lab_id)
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
        "unpaid_orders_count": unpaid_orders_count,
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

    if payment.lab_order_id is not None:
        stmt = select(models.LabOrder).where(
            models.LabOrder.id == payment.lab_order_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        bind = db.bind or db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()

        order = (await db.execute(stmt)).scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="طلب المعمل غير موجود")
        if order.laboratory_id != lab_id:
            raise HTTPException(status_code=400, detail="الطلب لا يتبع هذا المعمل")
        if (order.status or "").lower() == "cancelled":
            raise HTTPException(status_code=400, detail="لا يمكن تسجيل دفعة لطلب معمل ملغي")

        existing_paid = await db.scalar(
            select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
                models.LabPayment.tenant_id == current_user.tenant_id,
                models.LabPayment.lab_order_id == order.id,
            )
        )
        existing_paid_d = quantize_money(as_decimal(existing_paid))
        order_cost_d = quantize_money(as_decimal(order.cost))
        remaining_d = max(Decimal("0.00"), order_cost_d - existing_paid_d)

        payment_amount_d = quantize_money(as_decimal(payment.amount))
        if payment_amount_d > remaining_d:
            raise HTTPException(
                status_code=400,
                detail=f"المبلغ المدفوع ({payment_amount_d}) يتجاوز المبلغ المتبقي للطلب ({remaining_d})",
            )

    payload = payment.model_dump()
    payload["laboratory_id"] = lab_id
    db_payment = models.LabPayment(**payload, tenant_id=current_user.tenant_id)
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


@router.post(
    "/patients/{patient_id}/clinical-work-items/{work_item_id}/lab-handoff",
    summary="1-Tap Lab Handoff for Clinical Work Item (G12-M06)",
)
async def create_clinical_lab_handoff(
    patient_id: int,
    work_item_id: int,
    payload: schemas.LabHandoffCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """
    1-Tap Chairside Lab Handoff (Slice S28 / G12-M06).
    Dispatches a lab order linked directly to a clinical work item.
    - Decouples lab price from synthetic treatment creation (G12-M08, G12-M09, R06).
      Creates exactly 0 synthetic Treatment rows!
    - Enforces idempotency: repeated submissions return the existing order (G12-M16).
    - Fails closed (404) when clinical_vnext_native_writes is disabled.
    """
    native_writes = await FeatureFlagService.is_feature_enabled(
        db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, current_user.tenant_id
    )
    if not native_writes:
        raise HTTPException(
            status_code=404,
            detail="Clinical native writes are disabled",
        )

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

    work_item = (
        await db.execute(
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item_id,
                models.ClinicalWorkItem.tenant_id == current_user.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
            )
        )
    ).scalars().first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Clinical work item not found")

    lab = (
        await db.execute(
            select(models.Laboratory).where(
                models.Laboratory.id == payload.laboratory_id,
                models.Laboratory.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().first()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    # G12-M16: Handoff idempotency - return existing active lab order if present
    stmt_existing = (
        select(models.LabOrder)
        .options(
            selectinload(models.LabOrder.patient),
            selectinload(models.LabOrder.laboratory),
        )
        .where(
            models.LabOrder.tenant_id == current_user.tenant_id,
            models.LabOrder.work_item_id == work_item_id,
            models.LabOrder.status != "cancelled",
        )
        .order_by(models.LabOrder.id.desc())
    )
    existing_order = (await db.execute(stmt_existing)).scalars().first()
    if existing_order:
        payment_map = await get_order_payment_map(db, current_user.tenant_id, [existing_order.id])
        result = format_lab_order_dict(
            existing_order,
            paid_amount=payment_map.get(existing_order.id, Decimal("0.00")),
            patient_name=existing_order.patient.name if existing_order.patient else patient.name,
            laboratory_name=existing_order.laboratory.name if existing_order.laboratory else lab.name,
            is_existing=True,
        )
        return success_response(result)

    # Smart pre-population of tooth number and work type
    tooth_number = payload.tooth_number
    if not tooth_number and work_item.targets:
        teeth = sorted({str(t.tooth_key) for t in work_item.targets if t.tooth_key})
        tooth_number = ", ".join(teeth) if teeth else None

    work_type = payload.work_type
    if not work_type:
        proc = _PROCEDURE_DEFINITIONS.get(work_item.code)
        work_type = proc.display_name if proc else work_item.code

    provider_id = await _resolve_lab_provider_id(db, current_user, patient)

    db_order = models.LabOrder(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        laboratory_id=payload.laboratory_id,
        work_item_id=work_item_id,
        work_type=work_type,
        tooth_number=tooth_number,
        shade=payload.shade,
        material=payload.material,
        cost=payload.cost,
        price_to_patient=payload.price_to_patient,
        status="pending",
        notes=payload.notes,
        delivery_date=payload.delivery_date,
        doctor_id=provider_id,
    )
    db.add(db_order)

    # G12-M13: Sync shade/material updates to active care session observations
    if db_order.shade or db_order.material:
        from backend.clinical.shade_material_sync import sync_lab_order_to_active_care_session_observations
        await sync_lab_order_to_active_care_session_observations(
            db, current_user.tenant_id, db_order, actor_user_id=current_user.id
        )

    # G12-M08 & G12-M09 / R06: ZERO synthetic Treatment rows created!
    await db.commit()
    await db.refresh(db_order)

    result = format_lab_order_dict(
        db_order,
        paid_amount=Decimal("0.00"),
        patient_name=patient.name,
        laboratory_name=lab.name,
        is_existing=False,
    )
    return success_response(result)

