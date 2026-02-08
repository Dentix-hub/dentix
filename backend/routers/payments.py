"""
Payments Router
Handles billing, payments, and financial reporting.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, crud
from .auth import get_current_user, get_db
from ..services.billing_service import BillingService
# Multi-Doctor Financial Visibility
from ..services.financial_visibility_service import get_financial_visibility_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=schemas.Payment)
def create_payment(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Record a new payment."""
    service = BillingService(db, current_user.tenant_id)
    
    # Use current_user.id as default doctor_id if not provided
    doctor_id = payment.doctor_id if payment.doctor_id else current_user.id
    
    try:
        return service.create_payment(payment, doctor_id=doctor_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=List[schemas.Payment])
def read_payments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get payments for current user (filtered by role)."""
    visibility = get_financial_visibility_service(db, current_user, current_user.tenant_id)
    return visibility.get_visible_payments_query().offset(skip).limit(limit).all()


@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete a payment record."""
    return crud.delete_payment(db, payment_id, current_user.tenant_id)


# --- Financial Stats ---
    """Get financial statistics for current tenant."""
    service = BillingService(db, current_user.tenant_id)
    return service.get_financial_stats()


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
