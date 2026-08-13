import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend import models, schemas
from backend.database import get_async_db
from backend.services.subscription_service import SubscriptionService
from backend.core.permissions import Role, Permission, require_permission
from backend.core.response import success_response, StandardResponse
from backend.core.limiter import limiter


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
@limiter.limit("60/minute")
async def receive_provider_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET")
    if not secret or len(secret) < 32:
        raise HTTPException(status_code=503, detail="Payment webhook is not configured")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 65_536:
                raise HTTPException(
                    status_code=413, detail="Webhook payload is too large"
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid Content-Length header"
            ) from exc
    body = await request.body()
    if len(body) > 65_536:
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    timestamp = request.headers.get("X-Dentix-Timestamp", "")
    signature = request.headers.get("X-Dentix-Signature", "")
    if not SubscriptionService.verify_webhook_signature(
        body, timestamp, signature, secret
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        event = schemas.SubscriptionWebhookEvent.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    data = await SubscriptionService.handle_provider_webhook(db, event)
    return success_response(data=data, message="Subscription payment webhook processed")


@router.delete("/payments/{payment_id}", response_model=StandardResponse[dict])
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    await SubscriptionService.delete_payment(db, payment_id)
    return success_response(message="Payment deleted successfully")
