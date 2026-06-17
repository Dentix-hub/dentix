import json
import logging
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from backend.models.domain_event import DomainEvent

logger = logging.getLogger(__name__)

class EventService:
    @staticmethod
    def emit_event(
        db: AsyncSession,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        tenant_id: int = None
    ) -> DomainEvent:
        """
        Emits a domain event using the Transactional Outbox pattern.
        The event is saved in the same database transaction as the business operation.
        """
        event = DomainEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc)
        )
        db.add(event)
        # We DO NOT commit here. The caller (service) must commit the transaction.
        return event

    @staticmethod
    async def get_pending_events(db: AsyncSession, limit: int = 50) -> list[DomainEvent]:
        """
        Fetch pending events that are ready to be processed.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(DomainEvent)
            .filter(
                DomainEvent.status == "pending",
                DomainEvent.available_at <= now
            )
            .order_by(DomainEvent.created_at.asc())
            .with_for_update(skip_locked=True) # Prevent concurrent workers from picking the same events
            .limit(limit)
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        # Mark them as processing
        for event in events:
            event.status = "processing"

        await db.commit()
        return events

    @staticmethod
    async def mark_completed(db: AsyncSession, event_id: int):
        """Mark an event as successfully processed."""
        stmt = select(DomainEvent).filter(DomainEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalars().first()
        if event:
            event.status = "completed"
            event.processed_at = datetime.now(timezone.utc)
            await db.commit()

    @staticmethod
    async def mark_failed(db: AsyncSession, event_id: int, error_message: str):
        """Mark an event as failed. Handle retries if max_attempts not reached."""
        stmt = select(DomainEvent).filter(DomainEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalars().first()
        if event:
            event.attempts += 1
            event.error_message = str(error_message)[:2000] # Limit size

            if event.attempts >= event.max_attempts:
                event.status = "failed"
            else:
                event.status = "pending"
                # Simple exponential backoff for next attempt
                backoff_seconds = 2 ** event.attempts * 60 # 2m, 4m, 8m, etc.
                event.available_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)

            await db.commit()

event_service = EventService()
