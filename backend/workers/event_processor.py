import asyncio
import logging
from typing import Callable, Dict, Awaitable
from backend.database import SessionLocal
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

async def poll_outbox(poll_interval: int = 5):
    """
    Infinite loop that polls the domain_events table for pending events.
    Runs as an asyncio task within the FastAPI lifespan.
    """
    # Import handlers to trigger @register_handler decorators
    import backend.workers.handlers  # noqa: F401
    logger.info("Event Processor started polling. Registered handlers: %s", list(_handlers.keys()))
    while True:
        try:
            with SessionLocal() as db:
                events = event_service.get_pending_events(db, limit=20)
                if not events:
                    pass # Nothing to do

                for event in events:
                    try:
                        await process_event(event)
                        event_service.mark_completed(db, event.id)
                        logger.info(f"Successfully processed event {event.id} ({event.event_type})")
                    except Exception as e:
                        event_service.mark_failed(db, event.id, str(e))
                        
        except Exception as e:
            logger.error(f"Outbox polling encountered a critical error: {e}")
            
        await asyncio.sleep(poll_interval)
