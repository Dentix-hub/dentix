"""Payments Router — billing, payments, and financial reporting."""

from datetime import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas, crud
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.tenant_context import require_tenant_id
from backend.core.limiter import limiter
from backend.core.response import success_response, StandardResponse
from backend.core.idempotency import idempotent
from ..utils.audit_logger import log_admin_action
from ..services.billing_service import BillingService
from ..services.financial_visibility_service import get_financial_visibility_service
from backend.services.tenant_time_service import get_tenant_timezone
from backend.utils.tenant_time import tenant_day_utc_bounds_naive

logger = logging.getLogger("smart_clinic")
router = APIRouter(prefix="/payments", tags=["Payments"])


def _today_visibility_scope(current_user) -> tuple[int | None, bool]:
    is_doctor = current_user.role == "doctor"
    can_view_all = bool(getattr(current_user, "can_view_other_doctors_history", False))
    patient_scope_id = current_user.id if is_doctor and not can_view_all else None
    return patient_scope_id, is_doctor


def _parse_date(value: str, field_name: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}; expected YYYY-MM-DD",
        ) from exc


@router.post(
    "",
    response_model=StandardResponse[schemas.Payment],
    summary="Record a payment",
    description="Record a new payment for a patient. Auto-assigns doctor if not provided. Audit logged.",
)
@limiter.limit("15/minute")
@idempotent(expire=120)
async def create_payment(
    request: Request,
    payment: schemas.PaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    tenant_id = require_tenant_id(current_user)
    service = BillingService(db, tenant_id)
    # The user recording cash is not necessarily the treating doctor. Preserve an
    # explicit doctor selection; otherwise resolve the latest active provider.
    doctor_id = payment.doctor_id
    try:
        result = await service.create_payment(payment, doctor_id=doctor_id, commit=False)
        log_admin_action(
            db=db,
            admin_user=current_user,
            action="create",
            entity_type="payment",
            entity_id=result.id if hasattr(result, "id") else None,
            details=f"Payment of {payment.amount} for patient {payment.patient_id}",
        )
        await db.commit()

        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        from backend import models

        stmt = (
            select(models.Payment)
            .where(models.Payment.id == result.id)
            .options(joinedload(models.Payment.patient))
        )
        db_res = await db.execute(stmt)
        result = db_res.scalars().first()
        return success_response(data=result, message="Payment recorded successfully")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "",
    response_model=StandardResponse[List[schemas.Payment]],
    summary="List payments",
    description="Get payments visible to the current user based on their role with optional filtering and pagination.",
)
async def read_payments(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    from backend import models

    tenant_id = require_tenant_id(current_user)
    visibility = get_financial_visibility_service(db, current_user, tenant_id)
    query = visibility.get_visible_payments_query()

    if patient_id:
        query = query.where(models.Payment.patient_id == patient_id)
    if doctor_id:
        query = query.where(models.Payment.doctor_id == doctor_id)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (models.Patient.name.ilike(search_pattern))
            | (models.Payment.notes.ilike(search_pattern))
        )

    timezone_name = None
    if start_date or end_date:
        timezone_name = await get_tenant_timezone(db, tenant_id)

    parsed_start = _parse_date(start_date, "start_date") if start_date else None
    parsed_end = _parse_date(end_date, "end_date") if end_date else None
    if parsed_start and parsed_end and parsed_end < parsed_start:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    if parsed_start:
        utc_start, _ = tenant_day_utc_bounds_naive(
            timezone_name, local_date=parsed_start
        )
        query = query.where(models.Payment.date >= utc_start)
    if parsed_end:
        _, utc_end_exclusive = tenant_day_utc_bounds_naive(
            timezone_name, local_date=parsed_end
        )
        query = query.where(models.Payment.date < utc_end_exclusive)

    query = (
        query.order_by(models.Payment.date.desc(), models.Payment.id.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return success_response(
        data=result.scalars().all(), message="Payments retrieved successfully"
    )


@router.delete("/{payment_id}", response_model=StandardResponse[dict])
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    tenant_id = require_tenant_id(current_user)
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="payment",
        entity_id=payment_id,
        details=f"Deleted payment #{payment_id}",
    )
    deleted = await crud.delete_payment(db, payment_id, tenant_id)
    if not deleted:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Payment not found")
    return success_response(
        data={"payment_id": payment_id},
        message="Payment deleted successfully",
    )


@router.get("/today/payments", response_model=StandardResponse[List[dict]])
async def get_today_payments_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    patient_scope_id, is_doctor = _today_visibility_scope(current_user)
    service = BillingService(
        db,
        tenant_id,
        doctor_patient_scope_id=patient_scope_id,
        is_doctor=is_doctor,
    )
    payments = await service.get_today_payments_list()
    return success_response(data=payments, message="Today's payments retrieved")


@router.get("/today/debtors", response_model=StandardResponse[List[dict]])
async def get_today_debtors_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    patient_scope_id, is_doctor = _today_visibility_scope(current_user)
    service = BillingService(
        db,
        tenant_id,
        doctor_patient_scope_id=patient_scope_id,
        is_doctor=is_doctor,
    )
    debtors = await service.get_today_debtors_list()
    return success_response(data=debtors, message="Today's debtors retrieved")
