import asyncio
import logging
from typing import Callable, Dict, Awaitable
from backend.database import AsyncSessionLocal
from backend.services.event_service import event_service
from backend.models.domain_event import DomainEvent
import traceback

logger = logging.getLogger("smart_clinic.workers")

# Registry of event handlers
# Map of event_type -> async handler function
_handlers: Dict[str, Callable[[DomainEvent], Awaitable[None]]] = {}

def register_handler(event_type: str):
    """Decorator to register a handler for a specific event type."""
    def decorator(func: Callable[[DomainEvent], Awaitable[None]]):
        _handlers[event_type] = func
        return func
    return decorator

async def process_event(event: DomainEvent):
    """Process a single event using its registered handler."""
    handler = _handlers.get(event.event_type)
    if not handler:
        logger.warning(f"No handler registered for event type: {event.event_type}. Ignoring.")
        return

    try:
        await handler(event)
    except Exception as e:
        logger.error(f"Error processing event {event.id} ({event.event_type}): {e}\n{traceback.format_exc()}")
        raise e

from prefect import task, flow
from sqlalchemy.ext.asyncio import AsyncSession

@task(retries=3, retry_delay_seconds=60, log_prints=True)
async def process_pending_events(session: AsyncSession):
    """Prefect task to process pending outbox events."""
    # Import handlers to trigger @register_handler decorators
    import backend.workers.handlers  # noqa: F401
    events = await event_service.get_pending_events(session, limit=20)
    for event in events:
        try:
            await process_event(event)
            await event_service.mark_completed(session, event.id)
            logger.info(f"Successfully processed event {event.id} ({event.event_type})")
        except Exception as e:
            await event_service.mark_failed(session, event.id, str(e))

@flow(name="outbox-event-processor", log_prints=True)
async def event_processor_flow():
    """Prefect flow to run the outbox event processing cycle."""
    async with AsyncSessionLocal() as session:
        await process_pending_events(session)

async def poll_outbox(poll_interval: int = 5):
    """
    Loop runner that periodically triggers the Prefect flow.
    Runs as an asyncio task within the FastAPI lifespan.
    """
    logger.info("Event Processor daemon started. Registered handlers: %s", list(_handlers.keys()))
    while True:
        try:
            await event_processor_flow()
        except Exception as e:
            logger.error(f"Outbox polling flow failed: {e}")
        await asyncio.sleep(poll_interval)
