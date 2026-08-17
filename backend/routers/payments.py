"""
Payments Router
Handles billing, payments, and financial reporting.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import List, Optional

from .. import schemas, crud
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from backend.core.response import success_response, StandardResponse
from backend.core.idempotency import idempotent
from ..utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic")
from ..services.billing_service import BillingService

# Multi-Doctor Financial Visibility
from ..services.financial_visibility_service import get_financial_visibility_service

router = APIRouter(prefix="/payments", tags=["Payments"])


def _today_visibility_scope(current_user) -> tuple[int | None, bool]:
    """Mirror FinancialVisibilityService's established doctor visibility rule."""
    is_doctor = current_user.role == "doctor"
    can_view_all = bool(
        getattr(current_user, "can_view_other_doctors_history", False)
    )
    patient_scope_id = current_user.id if is_doctor and not can_view_all else None
    return patient_scope_id, is_doctor


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
    """Record a new payment."""
    service = BillingService(db, current_user.tenant_id)

    # Use current_user.id as default doctor_id if not provided
    doctor_id = payment.doctor_id if payment.doctor_id else current_user.id

    try:
        result = await service.create_payment(payment, doctor_id=doctor_id, commit=False)
        log_admin_action(
            db=db,
            admin_user=current_user,
            action="create",
            entity_type="payment",
            entity_id=result.id if hasattr(result, 'id') else None,
            details=f"Payment of {payment.amount} for patient {payment.patient_id}",
        )
        await db.commit()

        # Re-fetch with patient loaded to prevent MissingGreenlet on serialization
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
        raise HTTPException(status_code=404, detail=str(e))


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
    """Get payments for current user (filtered by role and optional criteria)."""
    from datetime import datetime
    from backend import models

    visibility = get_financial_visibility_service(
        db, current_user, current_user.tenant_id
    )
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

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(models.Payment.date >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.where(models.Payment.date <= end_dt)
        except ValueError:
            pass

    query = query.order_by(models.Payment.date.desc(), models.Payment.id.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    payments = result.scalars().all()
    return success_response(data=payments, message="Payments retrieved successfully")


@router.delete("/{payment_id}", response_model=StandardResponse[dict])
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Delete a payment record."""
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="payment",
        entity_id=payment_id,
        details=f"Deleted payment #{payment_id}",
    )
    await crud.delete_payment(db, payment_id, current_user.tenant_id)
    return success_response(
        data={"payment_id": payment_id},
        message="Payment deleted successfully",
    )


@router.get("/today/payments", response_model=StandardResponse[List[dict]])
async def get_today_payments_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get payments made in the current tenant business day."""
    patient_scope_id, is_doctor = _today_visibility_scope(current_user)
    service = BillingService(
        db,
        current_user.tenant_id,
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
    """Get positive same-day debtors in the current tenant business day."""
    patient_scope_id, is_doctor = _today_visibility_scope(current_user)
    service = BillingService(
        db,
        current_user.tenant_id,
        doctor_patient_scope_id=patient_scope_id,
        is_doctor=is_doctor,
    )
    debtors = await service.get_today_debtors_list()
    return success_response(data=debtors, message="Today's debtors retrieved")
