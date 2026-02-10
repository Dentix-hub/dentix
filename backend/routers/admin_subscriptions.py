from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
from backend.services.subscription_service import SubscriptionService
from backend.routers.auth.dependencies import get_current_user
from backend.constants import ROLES

router = APIRouter(
    prefix="/admin",
    tags=["Admin Subscriptions"],
    responses={404: {"description": "Not found"}},
)


# Dependency
def require_super_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# Plans
@router.get("/plans", response_model=List[schemas.SubscriptionPlan])
def get_all_plans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    return SubscriptionService.get_all_plans(db)


@router.post("/plans", response_model=schemas.SubscriptionPlan)
def create_plan(
    plan: schemas.SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    return SubscriptionService.create_plan(db, plan)


@router.put("/plans/{plan_id}", response_model=schemas.SubscriptionPlan)
def update_plan(
    plan_id: int,
    plan_update: schemas.SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    return SubscriptionService.update_plan(db, plan_id, plan_update)


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    return SubscriptionService.delete_plan(db, plan_id)


# Payments
@router.get("/payments", response_model=List[schemas.SubscriptionPayment])
def get_payments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    return SubscriptionService.get_payments(db, skip, limit)


@router.post("/payments", response_model=schemas.SubscriptionPayment)
def record_payment(
    payment: schemas.SubscriptionPaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    return SubscriptionService.record_payment(db, payment, current_user.username)


@router.delete("/payments/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    SubscriptionService.delete_payment(db, payment_id)
    return {"message": "Payment deleted successfully"}
