"""
Payments Router
Handles billing, payments, and financial reporting.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging
from typing import List

from .. import schemas, crud, models
from .auth import get_current_user, get_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from ..utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic")
from ..services.billing_service import BillingService

# Multi-Doctor Financial Visibility
from ..services.financial_visibility_service import get_financial_visibility_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/",
    response_model=schemas.Payment,
    summary="Record a payment",
    description="Record a new payment for a patient. Auto-assigns doctor if not provided. Audit logged.",
)
@limiter.limit("15/minute")
def create_payment(
    request: Request,
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Record a new payment."""
    service = BillingService(db, current_user.tenant_id)

    # Use current_user.id as default doctor_id if not provided
    doctor_id = payment.doctor_id if payment.doctor_id else current_user.id

    try:
        result = service.create_payment(payment, doctor_id=doctor_id)
        log_admin_action(
            db=db,
            admin_user=current_user,
            action="create",
            entity_type="payment",
            entity_id=result.id if hasattr(result, 'id') else None,
            details=f"Payment of {payment.amount} for patient {payment.patient_id}",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/",
    response_model=List[schemas.Payment],
    summary="List payments",
    description="Get payments visible to the current user based on their role.",
)
def read_payments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get payments for current user (filtered by role)."""
    visibility = get_financial_visibility_service(
        db, current_user, current_user.tenant_id
    )
    return visibility.get_visible_payments_query().offset(skip).limit(limit).all()


@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
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
    return crud.delete_payment(db, payment_id, current_user.tenant_id)


@router.get("/today/payments")
def get_today_payments_list(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get list of payments made today."""
    service = BillingService(db, current_user.tenant_id)
    return service.get_today_payments_list()


@router.get("/today/debtors")
def get_today_debtors_list(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get list of patients who incurred debt today."""
    service = BillingService(db, current_user.tenant_id)
    return service.get_today_debtors_list()
