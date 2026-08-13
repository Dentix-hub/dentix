from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import math
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from backend import models, schemas
from fastapi import HTTPException


class SubscriptionService:
    DEFAULT_GRACE_PERIOD_DAYS = 7
    CHECKOUT_TTL_MINUTES = 30
    WEBHOOK_TOLERANCE_SECONDS = 300

    @staticmethod
    def verify_webhook_signature(
        body: bytes, timestamp: str, signature: str, secret: str
    ) -> bool:
        """Verify signed raw request body and reject replayed requests."""
        try:
            event_time = int(timestamp)
        except (TypeError, ValueError):
            return False

        now = int(datetime.now(timezone.utc).timestamp())
        if abs(now - event_time) > SubscriptionService.WEBHOOK_TOLERANCE_SECONDS:
            return False

        signed_payload = timestamp.encode("ascii") + b"." + body
        expected = hmac.new(
            secret.encode("utf-8"), signed_payload, hashlib.sha256
        ).hexdigest()
        supplied = signature.removeprefix("sha256=").strip().lower()
        return hmac.compare_digest(expected, supplied)

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
        if float(plan.price or 0) <= 0:
            raise HTTPException(
                status_code=400,
                detail="Free plans do not require a provider checkout",
            )

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
        db: AsyncSession,
        payment_data: schemas.SubscriptionPaymentCreate,
        created_by: str,
        *,
        commit: bool = True,
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

        if commit:
            await db.commit()
            await db.refresh(payment)
        else:
            await db.flush()
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
            models.SubscriptionPlan.is_active.is_(True)
        )
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        provider = checkout.provider.strip().lower()
        if provider == "manual":
            raise HTTPException(
                status_code=400,
                detail="Manual payments must use the authenticated payments endpoint",
            )

        provider_reference = f"sub_{tenant.id}_{plan.id}_{uuid4().hex[:20]}"
        currency = checkout.currency.upper()
        pending_checkout = models.SubscriptionCheckout(
            provider_reference=provider_reference,
            tenant_id=tenant.id,
            plan_id=plan.id,
            provider=provider,
            expected_amount=float(plan.price or 0),
            currency=currency,
            status="pending",
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=SubscriptionService.CHECKOUT_TTL_MINUTES),
        )
        db.add(pending_checkout)
        await db.commit()

        # Keep the returned destination server-owned. Provider integrations may
        # replace this internal route with their own verified hosted URL later.
        checkout_url = f"/billing/checkout/{provider}/{provider_reference}"
        return schemas.SubscriptionCheckoutSession(
            provider=provider,
            provider_reference=provider_reference,
            checkout_url=checkout_url,
            amount=float(plan.price or 0),
            currency=currency,
        )

    @staticmethod
    async def handle_provider_webhook(
        db: AsyncSession, event: schemas.SubscriptionWebhookEvent
    ) -> models.SubscriptionPayment:
        if event.provider_status.lower() not in {"paid", "succeeded", "success", "completed"}:
            raise HTTPException(status_code=202, detail="Payment event ignored until it is paid")

        stmt = (
            select(models.SubscriptionCheckout)
            .where(
                models.SubscriptionCheckout.provider_reference
                == event.provider_reference
            )
            .with_for_update()
        )
        checkout = (await db.execute(stmt)).scalar_one_or_none()
        if not checkout:
            raise HTTPException(status_code=404, detail="Unknown checkout reference")

        if checkout.provider != event.provider.strip().lower():
            raise HTTPException(status_code=400, detail="Payment provider mismatch")

        expires_at = checkout.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            checkout.status = "expired"
            await db.commit()
            raise HTTPException(status_code=410, detail="Checkout has expired")

        if checkout.status == "processed":
            existing_stmt = select(models.SubscriptionPayment).where(
                models.SubscriptionPayment.provider == checkout.provider,
                models.SubscriptionPayment.provider_payment_id
                == checkout.provider_payment_id,
            )
            existing = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                return existing
            raise HTTPException(status_code=409, detail="Checkout already processed")

        if checkout.status != "pending":
            raise HTTPException(status_code=409, detail="Checkout is not payable")

        if event.currency.upper() != checkout.currency:
            raise HTTPException(status_code=400, detail="Payment currency mismatch")
        if not math.isclose(
            event.amount, checkout.expected_amount, rel_tol=0, abs_tol=0.01
        ):
            raise HTTPException(status_code=400, detail="Payment amount mismatch")

        payment = schemas.SubscriptionPaymentCreate(
            tenant_id=checkout.tenant_id,
            plan_id=checkout.plan_id,
            amount=checkout.expected_amount,
            payment_method=checkout.provider,
            paid_by=event.paid_by,
            notes=event.notes,
            provider=checkout.provider,
            provider_payment_id=event.provider_payment_id,
            provider_status=event.provider_status,
        )
        try:
            result = await SubscriptionService.record_payment(
                db,
                payment,
                created_by=f"{checkout.provider}:webhook",
                commit=False,
            )
            checkout.status = "processed"
            checkout.provider_payment_id = event.provider_payment_id
            checkout.processed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(result)
            return result
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def delete_payment(db: AsyncSession, payment_id: int):
        stmt = select(models.SubscriptionPayment).where(models.SubscriptionPayment.id == payment_id)
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        await db.delete(payment)
        await db.commit()
