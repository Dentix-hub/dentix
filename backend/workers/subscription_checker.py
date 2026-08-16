import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import AsyncSessionLocal
from backend.models.tenant import Tenant
from sqlalchemy import select, or_
import traceback

from prefect import task, flow
from prefect.cache_policies import NO_CACHE

logger = logging.getLogger("smart_clinic.workers")

@task(retries=3, retry_delay_seconds=300, log_prints=True, cache_policy=NO_CACHE)
async def check_expired_subscriptions(db: AsyncSession):
    """
    Finds all active tenants whose subscription_end_date has passed
    and sets them to inactive.
    """
    now = datetime.now(timezone.utc)
    # Using sqlalchemy select
    stmt = select(Tenant).where(
        Tenant.is_active == True,
        Tenant.subscription_end_date != None,
        Tenant.subscription_end_date < now,
        or_(Tenant.grace_period_until == None, Tenant.grace_period_until < now)
    )
    result = await db.execute(stmt)
    expired_tenants = result.scalars().all()

    if not expired_tenants:
        return 0

    count = 0
    for tenant in expired_tenants:
        tenant.is_active = False
        tenant.subscription_status = "expired"
        logger.info(f"Tenant {tenant.id} ({tenant.name}) subscription expired. Access revoked.")
        count += 1

    await db.commit()
    return count

@flow(name="subscription-checker", log_prints=True)
async def subscription_checker_flow():
    """Prefect flow to run the subscription checker cycle."""
    async with AsyncSessionLocal() as db:
        count = await check_expired_subscriptions(db)
        if count > 0:
            logger.info(f"Suspended {count} expired tenants during this cycle.")

async def start_subscription_checker_loop(interval_hours: int = 12):
    """
    Loop runner that periodically triggers the subscription check flow.
    Runs as an asyncio task within the FastAPI lifespan.
    """
    logger.info(f"Subscription Checker daemon started. Will run every {interval_hours} hours.")

    while True:
        try:
            await subscription_checker_flow()
        except Exception as e:
            logger.error(f"Subscription checker flow failed: {e}\n{traceback.format_exc()}")

        # Sleep for the configured interval (convert hours to seconds)
        await asyncio.sleep(interval_hours * 3600)
