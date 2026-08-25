import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import system_session_scope
from backend.models.tenant import Tenant
from sqlalchemy import select, or_
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
    stmt = select(Tenant).where(
        Tenant.is_active == True,
        Tenant.subscription_end_date != None,
        Tenant.subscription_end_date < now,
        or_(Tenant.grace_period_until == None, Tenant.grace_period_until < now),
    )
    result = await db.execute(stmt)
    expired_tenants = result.scalars().all()

    if not expired_tenants:
        return 0

    count = 0
    for tenant in expired_tenants:
        if mode == "observe":
            logger.info(
                f"[OBSERVE] Tenant {tenant.id} ({tenant.name}) subscription is past expiry date."
            )
        elif mode == "enforce":
            # Update subscription status, but NEVER set is_active = False!
            tenant.subscription_status = "expired"
            logger.info(
                f"[ENFORCE] Tenant {tenant.id} ({tenant.name}) subscription marked expired (read-only clinical history preserved)."
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
