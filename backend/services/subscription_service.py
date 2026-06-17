from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from backend import models, schemas
from fastapi import HTTPException


class SubscriptionService:
    DEFAULT_GRACE_PERIOD_DAYS = 7

    @staticmethod
    async def check_subscription_status(db: AsyncSession, tenant_id: int):
        """
        Evaluates the current status of a tenant subscription.
        Returns: 'active', 'grace_period', 'expired', 'suspended'
        """
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            return None

        # 1. Check Forced Suspension
        # If manually set to inactive? The model has is_active.
        if not tenant.is_active:
            return "suspended"

        # 2. Check Expiry
        if not tenant.subscription_end_date:
            return "active"  # Assuming permanent/trial if no date? Or indefinite.

        now = datetime.now(timezone.utc)

        sub_end = tenant.subscription_end_date
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        if now <= sub_end:
            return "active"

        # 3. Check Grace Period
        grace_end = tenant.grace_period_until
        if grace_end and grace_end.tzinfo is None:
            grace_end = grace_end.replace(tzinfo=timezone.utc)

        if grace_end and now <= grace_end:
            return "grace_period"

        return "expired"

    @staticmethod
    async def extend_grace_period(db: AsyncSession, tenant_id: int, days: int, reason: str):
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.grace_period_until = datetime.now(timezone.utc) + timedelta(days=days)
        tenant.manual_override_reason = reason
        tenant.is_active = True

        await db.commit()
        return tenant

    @staticmethod
    async def manual_suspend(db: AsyncSession, tenant_id: int, reason: str):
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_active = False
        tenant.manual_override_reason = f"Suspended: {reason}"
        await db.commit()
        return tenant

    @staticmethod
    async def get_subscription_details(db: AsyncSession, tenant_id: int):
        """Get full subscription details for UI/AI."""
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            return None

        plan = None
        if tenant.plan_id:
            stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == tenant.plan_id)
            plan = (await db.execute(stmt)).scalar_one_or_none()

        plan_name = plan.display_name_ar if plan else (tenant.plan or "مجاني")
        plan_price = plan.price if plan else 0

        return {
            "plan_name": plan_name,
            "plan_price": plan_price,
            "status": tenant.subscription_status or "active",
            "start_date": None,
            "end_date": str(tenant.subscription_end_date)
            if tenant.subscription_end_date
            else None,
            "is_active": tenant.subscription_status == "active",
        }

    @staticmethod
    async def get_all_plans(db: AsyncSession):
        """List all active subscription plans."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.is_active == True)  # noqa: E712
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_plan(db: AsyncSession, plan_data: schemas.SubscriptionPlanCreate):
        """Create a new subscription plan."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.name == plan_data.name)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400, detail="Plan with this name already exists"
            )

        if getattr(plan_data, "is_default", False):
            stmt = update(models.SubscriptionPlan).values(is_default=False)
            await db.execute(stmt)
            await db.commit()

        new_plan = models.SubscriptionPlan(
            name=plan_data.name,
            display_name_ar=plan_data.display_name_ar,
            price=plan_data.price,
            duration_days=plan_data.duration_days,
            max_users=plan_data.max_users,
            max_patients=plan_data.max_patients,
            features=plan_data.features,
            is_ai_enabled=plan_data.is_ai_enabled,
            ai_daily_limit=plan_data.ai_daily_limit,
            ai_features=plan_data.ai_features,
            is_default=getattr(plan_data, "is_default", False),
            is_active=True,
        )
        db.add(new_plan)
        await db.commit()
        await db.refresh(new_plan)
        return new_plan

    @staticmethod
    async def update_plan(
        db: AsyncSession, plan_id: int, update_data: schemas.SubscriptionPlanUpdate
    ):
        """Update an existing plan."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == plan_id)
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        update_dict = update_data.model_dump(exclude_unset=True)

        if update_dict.get("is_default") is True:
            stmt = update(models.SubscriptionPlan).where(
                models.SubscriptionPlan.id != plan_id
            ).values(is_default=False)
            await db.execute(stmt)

        for key, value in update_dict.items():
            setattr(plan, key, value)

        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def delete_plan(db: AsyncSession, plan_id: int):
        """Soft delete a plan (set is_active=False)."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == plan_id)
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        plan.is_active = False
        await db.commit()
        return {"success": True, "message": "Plan deactivated successfully"}

    # --- Payment Methods ---
    @staticmethod
    async def get_payments(db: AsyncSession, skip: int = 0, limit: int = 100):
        stmt = (
            select(models.SubscriptionPayment)
            .options(selectinload(models.SubscriptionPayment.tenant))
            .order_by(models.SubscriptionPayment.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def record_payment(
        db: AsyncSession, payment_data: schemas.SubscriptionPaymentCreate, created_by: str
    ):
        if payment_data.provider_payment_id:
            stmt = select(models.SubscriptionPayment).where(
                models.SubscriptionPayment.provider == payment_data.provider,
                models.SubscriptionPayment.provider_payment_id == payment_data.provider_payment_id,
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                return existing

        stmt = select(models.Tenant).where(models.Tenant.id == payment_data.tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == payment_data.plan_id)
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        payment = models.SubscriptionPayment(
            **payment_data.model_dump(exclude={"payment_date"}),
            payment_date=payment_data.payment_date or datetime.now(timezone.utc),
            created_by=created_by,
        )
        db.add(payment)

        # Update tenant subscription
        now = datetime.now(timezone.utc)
        sub_end = tenant.subscription_end_date
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        target_date = (
            tenant.subscription_end_date
            if tenant.subscription_end_date
            and sub_end > now
            else now
        )
        tenant.subscription_end_date = target_date + timedelta(days=plan.duration_days)
        tenant.plan = plan.name
        tenant.plan_id = plan.id
        tenant.is_active = True
        tenant.subscription_status = "active"

        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def create_checkout_session(
        db: AsyncSession, checkout: schemas.SubscriptionCheckoutCreate
    ) -> schemas.SubscriptionCheckoutSession:
        stmt = select(models.Tenant).where(models.Tenant.id == checkout.tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        stmt = select(models.SubscriptionPlan).where(
            models.SubscriptionPlan.id == checkout.plan_id,
            models.SubscriptionPlan.is_active == True
        )
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        provider_reference = f"sub_{tenant.id}_{plan.id}_{uuid4().hex[:12]}"
        checkout_url = (
            checkout.success_url
            or f"/billing/checkout/{checkout.provider}/{provider_reference}"
        )
        return schemas.SubscriptionCheckoutSession(
            provider=checkout.provider,
            provider_reference=provider_reference,
            checkout_url=checkout_url,
            amount=float(plan.price or 0),
        )

    @staticmethod
    async def handle_provider_webhook(
        db: AsyncSession, event: schemas.SubscriptionWebhookEvent
    ) -> models.SubscriptionPayment:
        if event.provider_status.lower() not in {"paid", "succeeded", "success", "completed"}:
            raise HTTPException(status_code=202, detail="Payment event ignored until it is paid")

        payment = schemas.SubscriptionPaymentCreate(
            tenant_id=event.tenant_id,
            plan_id=event.plan_id,
            amount=event.amount,
            payment_method=event.provider,
            paid_by=event.paid_by,
            notes=event.notes,
            provider=event.provider,
            provider_payment_id=event.provider_payment_id,
            provider_status=event.provider_status,
        )
        return await SubscriptionService.record_payment(db, payment, created_by=f"{event.provider}:webhook")

    @staticmethod
    async def delete_payment(db: AsyncSession, payment_id: int):
        stmt = select(models.SubscriptionPayment).where(models.SubscriptionPayment.id == payment_id)
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        await db.delete(payment)
        await db.commit()
