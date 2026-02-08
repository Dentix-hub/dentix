from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
from backend.services.subscription_service import SubscriptionService
from backend.routers.auth import get_current_user
from backend.constants import ROLES

router = APIRouter(
    prefix="/admin/subscriptions",
    tags=["Admin Subscriptions"],
    responses={404: {"description": "Not found"}},
)

# Dependency to check for super admin
def get_super_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role == ROLES.SUPER_ADMIN:
        return current_user
    if current_user.role == ROLES.ADMIN and current_user.tenant_id is None:
        return current_user
    raise HTTPException(status_code=403, detail="Not authorized")

@router.get("/plans", response_model=List[schemas.SubscriptionPlan])
def get_all_plans(db: Session = Depends(get_db), current_user: models.User = Depends(get_super_admin)):
    """List all active subscription plans."""
    return SubscriptionService.get_all_plans(db)

@router.post("/plans", response_model=schemas.SubscriptionPlan)
def create_plan(
    plan: schemas.SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin)
):
    """Create a new subscription plan."""
    return SubscriptionService.create_plan(db, plan)

@router.put("/plans/{plan_id}", response_model=schemas.SubscriptionPlan)
def update_plan(
    plan_id: int,
    plan_update: schemas.SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin)
):
    """Update an existing subscription plan."""
    return SubscriptionService.update_plan(db, plan_id, plan_update)

@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin)
):
    """Soft delete (deactivate) a plan."""
    return SubscriptionService.delete_plan(db, plan_id)
