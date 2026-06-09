import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.tenant import Tenant
import traceback

logger = logging.getLogger("smart_clinic.workers")

def check_expired_subscriptions(db: Session):
    """
    Finds all active tenants whose subscription_end_date has passed
    and sets them to inactive.
    """
    now = datetime.now(timezone.utc)
    expired_tenants = db.query(Tenant).filter(
        Tenant.is_active == True,
        Tenant.subscription_end_date != None,
        Tenant.subscription_end_date < now,
        # Allow grace period if defined
        (Tenant.grace_period_until == None) | (Tenant.grace_period_until < now)
    ).all()

    if not expired_tenants:
        return 0

    count = 0
    for tenant in expired_tenants:
        tenant.is_active = False
        tenant.subscription_status = "expired"
        logger.info(f"Tenant {tenant.id} ({tenant.name}) subscription expired. Access revoked.")
        count += 1
    
    db.commit()
    return count

async def start_subscription_checker_loop(interval_hours: int = 12):
    """
    Infinite loop to periodically check for expired subscriptions.
    Runs as an asyncio task within the FastAPI lifespan.
    """
    logger.info(f"Subscription Checker started. Will run every {interval_hours} hours.")
    
    while True:
        try:
            with SessionLocal() as db:
                count = check_expired_subscriptions(db)
                if count > 0:
                    logger.info(f"Suspended {count} expired tenants during this cycle.")
        except Exception as e:
            logger.error(f"Subscription checker encountered an error: {e}\n{traceback.format_exc()}")
            
        # Sleep for the configured interval (convert hours to seconds)
        await asyncio.sleep(interval_hours * 3600)
