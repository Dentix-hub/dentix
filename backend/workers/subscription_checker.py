import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import system_session_scope
from backend.models.tenant import Tenant
from backend import models
from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
    validate_transition,
)
from sqlalchemy import select, or_, and_
import traceback

from prefect import task, flow
from prefect.cache_policies import NO_CACHE
from backend.core.config import is_subscription_worker_enabled, get_subscription_enforcement_mode

logger = logging.getLogger("smart_clinic.workers")


@task(retries=3, retry_delay_seconds=300, log_prints=True, cache_policy=NO_CACHE)
async def check_expired_subscriptions(db: AsyncSession):
    """
    Finds all active tenants whose subscription_end_date has passed.
    INVARIANTS:
    - Never runs if SUBSCRIPTION_WORKER_ENABLED is false.
    - In 'off' mode: does nothing.
    - In 'observe' mode: logs count, mutates nothing.
    - In 'enforce' mode: updates subscription_status to 'expired', but NEVER sets is_active = False.
    """
    if not is_subscription_worker_enabled():
        logger.info("Subscription worker is disabled via SUBSCRIPTION_WORKER_ENABLED=false.")
        return 0

    mode = get_subscription_enforcement_mode()
    if mode == "off":
        logger.info("Subscription enforcement mode is 'off'. Expiry check skipped.")
        return 0

    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)

    stmt = select(Tenant).where(
        Tenant.is_active == True,
        Tenant.is_deleted == False,
        Tenant.subscription_status.notin_(
            [
                SubscriptionState.SUSPENDED_ADMIN.value,
                SubscriptionState.CANCELLED.value,
            ]
        ),
        or_(
            Tenant.subscription_end_date < now,
            Tenant.subscription_end_date < now_naive,
            and_(
                Tenant.future_plan_id != None,
                Tenant.future_plan_start_date <= now_naive,
            ),
        ),
    )
    result = await db.execute(stmt)
    expired_tenants = result.scalars().all()

    if not expired_tenants:
        return 0

    count = 0
    for tenant in expired_tenants:
        curr_status = normalize_state(tenant.subscription_status or "trial")
        # Defensive check: worker never overwrites security suspension or cancellation
        if curr_status in {
            SubscriptionState.SUSPENDED_ADMIN.value,
            SubscriptionState.CANCELLED.value,
        }:
            continue

        # Check if a future plan (e.g. bought during trial) starts now
        if tenant.future_plan_id and tenant.future_plan_start_date:
            f_start = tenant.future_plan_start_date
            if f_start.tzinfo is None:
                f_start = f_start.replace(tzinfo=timezone.utc)
            if now >= f_start:
                if mode == "enforce":
                    future_plan = await db.get(models.SubscriptionPlan, tenant.future_plan_id)
                    if future_plan:
                        tenant.plan_id = future_plan.id
                        tenant.plan = future_plan.name
                    tenant.future_plan_id = None
                    tenant.future_plan_start_date = None
                    tenant.subscription_status = SubscriptionState.ACTIVE.value
                    logger.info(
                        f"[ENFORCE] Tenant {tenant.id} activated future paid plan {tenant.plan}."
                    )
                    count += 1
                continue

        # Otherwise evaluate expiry / grace
        sub_end = tenant.subscription_end_date
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)

        grace_end = tenant.grace_period_until
        if grace_end and grace_end.tzinfo is None:
            grace_end = grace_end.replace(tzinfo=timezone.utc)

        if curr_status == SubscriptionState.TRIAL.value:
            # Trial has no grace period
            target_status = SubscriptionState.EXPIRED_READ_ONLY.value
        else:
            # Paid subscription: allow 7 grace days
            if grace_end and now <= grace_end:
                target_status = SubscriptionState.GRACE.value
            else:
                target_status = SubscriptionState.EXPIRED_READ_ONLY.value

        if target_status != curr_status:
            if mode == "observe":
                logger.info(
                    f"[OBSERVE] Tenant {tenant.id} ({tenant.name}) status transition: {curr_status} -> {target_status}."
                )
            elif mode == "enforce":
                new_status = validate_transition(curr_status, target_status)
                tenant.subscription_status = new_status
                logger.info(
                    f"[ENFORCE] Tenant {tenant.id} ({tenant.name}) transitioned from '{curr_status}' to '{new_status}' (read-only clinical history preserved, is_active unmodified)."
                )
                count += 1

    if mode == "enforce" and count > 0:
        await db.commit()

    return count if mode == "enforce" else len(expired_tenants)


@flow(name="subscription-checker", log_prints=True)
async def subscription_checker_flow():
    """Prefect flow to run the subscription checker cycle."""
    async with system_session_scope() as db:
        count = await check_expired_subscriptions(db)
        if count > 0:
            logger.info(f"Processed {count} expired tenants during this cycle.")


async def start_subscription_checker_loop(interval_hours: int = 12):
    """
    Loop runner that periodically triggers the subscription check flow.
    Runs as an asyncio task within the FastAPI lifespan.
    """
    logger.info(f"Subscription Checker daemon started. Will run every {interval_hours} hours.")

    while True:
        try:
            await subscription_checker_flow()
        except asyncio.CancelledError:
            logger.info("Subscription checker received cancellation signal. Stopping.")
            break
        except Exception as e:
            logger.error(f"Subscription checker flow failed: {e}\n{traceback.format_exc()}")

        try:
            # Sleep for the configured interval (convert hours to seconds)
            await asyncio.sleep(interval_hours * 3600)
        except asyncio.CancelledError:
            logger.info("Subscription checker sleep cancelled. Exiting cleanly.")
            break
