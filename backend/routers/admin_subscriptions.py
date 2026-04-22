from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
from backend.services.subscription_service import SubscriptionService
from backend.core.permissions import Role, Permission, require_permission
from backend.core.response import success_response, StandardResponse


router = APIRouter(
    prefix="/admin/subscriptions",
    tags=["Admin Subscriptions"],
    responses={404: {"description": "Not found"}},
)


# Dependency
def require_super_admin(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# Plans
@router.get("/plans", response_model=StandardResponse[List[schemas.SubscriptionPlan]])
def get_all_plans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = SubscriptionService.get_all_plans(db)
    return success_response(data=data)


@router.post("/plans", response_model=StandardResponse[schemas.SubscriptionPlan])
def create_plan(
    plan: schemas.SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = SubscriptionService.create_plan(db, plan)
    return success_response(data=data, message="Plan created successfully")


@router.put("/plans/{plan_id}", response_model=StandardResponse[schemas.SubscriptionPlan])
def update_plan(
    plan_id: int,
    plan_update: schemas.SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = SubscriptionService.update_plan(db, plan_id, plan_update)
    return success_response(data=data, message="Plan updated successfully")


@router.delete("/plans/{plan_id}", response_model=StandardResponse[dict])
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = SubscriptionService.delete_plan(db, plan_id)
    return success_response(data=data, message="Plan deleted successfully")


# Payments
@router.get("/payments", response_model=StandardResponse[List[schemas.SubscriptionPayment]])
def get_payments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = SubscriptionService.get_payments(db, skip, limit)
    return success_response(data=data)


@router.post("/payments", response_model=StandardResponse[schemas.SubscriptionPayment])
def record_payment(
    payment: schemas.SubscriptionPaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = SubscriptionService.record_payment(db, payment, current_user.username)
    return success_response(data=data, message="Payment recorded successfully")


@router.delete("/payments/{payment_id}", response_model=StandardResponse[dict])
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    SubscriptionService.delete_payment(db, payment_id)
    return success_response(message="Payment deleted successfully")
