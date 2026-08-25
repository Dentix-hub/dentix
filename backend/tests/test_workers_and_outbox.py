"""
Tests for Phase P06: Background Worker Lifecycle, Outbox Processing, and Session Isolation.
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.event_service import event_service
from backend.workers.event_processor import process_event, process_pending_events
from backend.models.domain_event import DomainEvent
from backend.models import Tenant


@pytest.mark.asyncio
async def test_unknown_event_type_raises_and_marks_failed(async_db_session: AsyncSession):
    tenant = Tenant(name="Outbox Test Clinic", is_active=True, subscription_status="active")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    # 1. Emit an unknown event type
    event = event_service.emit_event(
        db=async_db_session,
        event_type="unknown.special.action",
        aggregate_type="Special",
        aggregate_id="999",
        payload={"foo": "bar"},
        tenant_id=tenant.id,
    )
    await async_db_session.commit()
    await async_db_session.refresh(event)

    # 2. process_event should raise ValueError for unknown event type
    with pytest.raises(ValueError, match="No handler registered"):
        await process_event(event)

    # 3. process_pending_events should handle the error and mark the event as failed
    await process_pending_events.fn(async_db_session)
    await async_db_session.refresh(event)

    assert event.attempts >= 1
    assert "No handler registered" in (event.error_message or "")


@pytest.mark.asyncio
async def test_known_event_processing(async_db_session: AsyncSession):
    tenant = Tenant(name="Outbox Known Clinic", is_active=True, subscription_status="active")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    event = event_service.emit_event(
        db=async_db_session,
        event_type="appointment.created",
        aggregate_type="Appointment",
        aggregate_id="101",
        payload={"patient_id": 5, "time": "2026-08-25T10:00:00Z"},
        tenant_id=tenant.id,
    )
    await async_db_session.commit()
    await async_db_session.refresh(event)

    await process_pending_events.fn(async_db_session)
    await async_db_session.refresh(event)

    assert event.status == "completed"
    assert event.processed_at is not None
