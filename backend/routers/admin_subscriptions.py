from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend import models, schemas
from backend.database import get_async_db
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
async def get_all_plans(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.get_all_plans(db)
    return success_response(data=data)


@router.post("/plans", response_model=StandardResponse[schemas.SubscriptionPlan])
async def create_plan(
    plan: schemas.SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.create_plan(db, plan)
    return success_response(data=data, message="Plan created successfully")


@router.put("/plans/{plan_id}", response_model=StandardResponse[schemas.SubscriptionPlan])
async def update_plan(
    plan_id: int,
    plan_update: schemas.SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.update_plan(db, plan_id, plan_update)
    return success_response(data=data, message="Plan updated successfully")


@router.delete("/plans/{plan_id}", response_model=StandardResponse[dict])
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.delete_plan(db, plan_id)
    return success_response(data=data, message="Plan deleted successfully")


# Payments
@router.get("/payments", response_model=StandardResponse[List[schemas.SubscriptionPayment]])
async def get_payments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.get_payments(db, skip, limit)
    return success_response(data=data)


@router.post("/payments", response_model=StandardResponse[schemas.SubscriptionPayment])
async def record_payment(
    payment: schemas.SubscriptionPaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.record_payment(db, payment, current_user.username)
    return success_response(data=data, message="Payment recorded successfully")


@router.post("/checkout", response_model=StandardResponse[schemas.SubscriptionCheckoutSession])
async def create_checkout_session(
    checkout: schemas.SubscriptionCheckoutCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    data = await SubscriptionService.create_checkout_session(db, checkout)
    return success_response(data=data, message="Checkout session created successfully")


@router.post("/webhooks/provider", response_model=StandardResponse[schemas.SubscriptionPayment])
async def receive_provider_webhook(
    request: Request,
    event: schemas.SubscriptionWebhookEvent,
    x_webhook_signature: str = Header(..., alias="X-Webhook-Signature"),
    x_webhook_timestamp: str = Header(..., alias="X-Webhook-Timestamp"),
    db: AsyncSession = Depends(get_async_db),
):
    raw_payload = await request.body()
    data = await SubscriptionService.handle_provider_webhook(
        db,
        event,
        raw_payload=raw_payload,
        timestamp=x_webhook_timestamp,
        signature=x_webhook_signature,
    )
    return success_response(data=data, message="Subscription payment webhook processed")


@router.delete("/payments/{payment_id}", response_model=StandardResponse[dict])
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    await SubscriptionService.delete_payment(db, payment_id)
    return success_response(message="Payment deleted successfully")
