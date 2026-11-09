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
        Tenant.is_active.is_(True),
        Tenant.is_deleted.is_(False),
        Tenant.subscription_status.notin_(
            [
                SubscriptionState.SUSPENDED_ADMIN.value,
                SubscriptionState.CANCELLED.value,
            ]
        ),
        or_(
            Tenant.subscription_end_date <= now_naive,
            and_(
                Tenant.future_plan_id.is_not(None),
                Tenant.future_plan_start_date <= now_naive,
            ),
        ),
    )
    result = await db.execute(stmt.with_for_update(skip_locked=True))
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

        from backend.services.subscription_period import resolve_subscription_period

        period = resolve_subscription_period(tenant, now)
        target_status = period.status
        if period.future_started and mode == "enforce":
            future_plan = await db.get(models.SubscriptionPlan, tenant.future_plan_id)
            if future_plan:
                tenant.plan_id, tenant.plan = future_plan.id, future_plan.name
                tenant.future_plan_id = None
                tenant.future_plan_start_date = None
                tenant.scheduled_downgrade_plan_id = None
                count += 1

        if target_status != curr_status:
            if mode == "observe":
                logger.info(
                    f"[OBSERVE] Tenant {tenant.id} ({tenant.name}) status transition: {curr_status} -> {target_status}."
                )
            elif mode == "enforce":
                if curr_status == SubscriptionState.TRIAL.value and period.future_started:
                    validate_transition(curr_status, SubscriptionState.ACTIVE.value)
                    curr_status = SubscriptionState.ACTIVE.value
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
