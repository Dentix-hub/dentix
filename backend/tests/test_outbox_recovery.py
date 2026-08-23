"""Regression tests for outbox crash recovery (HIGH-10).

An event claimed as 'processing' whose worker crashed must be reclaimed and
redelivered once its lease expires — never lost forever.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.domain_event import DomainEvent
from backend.services.event_service import event_service


def _make_event(tenant_id=1, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        tenant_id=tenant_id,
        event_type="test.happened",
        aggregate_type="test",
        aggregate_id="1",
        payload={"k": "v"},
        status="pending",
        attempts=0,
        available_at=now,
        created_at=now,
    )
    defaults.update(overrides)
    return DomainEvent(**defaults)


async def _seed(session, *events):
    for event in events:
        session.add(event)
    await session.commit()


@pytest.mark.asyncio
async def test_claimed_event_stamps_lease(async_db_session):
    await _seed(async_db_session, _make_event())

    claimed = await event_service.get_pending_events(async_db_session, limit=10)

    assert len(claimed) == 1
    assert claimed[0].status == "processing"
    # Lease start stamped at claim time
    age = datetime.now(timezone.utc) - claimed[0].available_at
    assert age < timedelta(seconds=60)


@pytest.mark.asyncio
async def test_crashed_processing_event_is_recovered_after_lease(async_db_session):
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2)
    await _seed(
        async_db_session,
        _make_event(status="processing", available_at=stale_time),
    )

    events = await event_service.get_pending_events(async_db_session, limit=10)

    assert len(events) == 1
    assert events[0].status == "processing"


@pytest.mark.asyncio
async def test_fresh_processing_event_is_not_double_delivered(async_db_session):
    recent = datetime.now(timezone.utc) - timedelta(seconds=30)
    await _seed(
        async_db_session,
        _make_event(status="processing", available_at=recent),
    )

    events = await event_service.get_pending_events(async_db_session, limit=10)

    assert events == []


@pytest.mark.asyncio
async def test_failed_event_respects_max_attempts_before_recovery(async_db_session):
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2)
    await _seed(
        async_db_session,
        _make_event(status="failed", attempts=5, max_attempts=5, available_at=stale_time),
    )
    from backend.services.event_service import PROCESSING_LEASE_SECONDS

    recovered = await event_service.recover_stale_processing(
        async_db_session, lease_seconds=PROCESSING_LEASE_SECONDS
    )
    assert recovered == 0


@pytest.mark.asyncio
async def test_recover_returns_count(async_db_session):
    stale_time = datetime.now(timezone.utc) - timedelta(hours=3)
    await _seed(
        async_db_session,
        _make_event(status="processing", available_at=stale_time),
        _make_event(aggregate_id="2", status="processing", available_at=stale_time),
    )

    recovered = await event_service.recover_stale_processing(async_db_session)
    assert recovered == 2
