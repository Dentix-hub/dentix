"""P08-04 durable backup scheduler and worker behavior."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.services import backup_scheduler_service as scheduler
from backend.services.event_service import event_service


@pytest.mark.asyncio
async def test_backup_scheduler_disabled_by_default(
    async_db_session: AsyncSession, monkeypatch
):
    monkeypatch.delenv("BACKUP_SCHEDULER_ENABLED", raising=False)
    result = await scheduler.schedule_due_backup(async_db_session)
    assert result.status == "disabled"
    assert (
        await async_db_session.scalar(select(func.count(models.DomainEvent.id)))
    ) == 0


@pytest.mark.asyncio
async def test_backup_scheduler_creates_due_event(
    async_db_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("BACKUP_SCHEDULER_ENABLED", "true")
    now = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
    result = await scheduler.schedule_due_backup(async_db_session, now=now)
    assert result.status == "scheduled"
    event = await async_db_session.get(models.DomainEvent, result.event_id)
    assert event.event_type == scheduler.BACKUP_EVENT_TYPE
    assert event.payload["scheduled_for"] == now.isoformat()
    assert event.payload["missed_run"] is False


@pytest.mark.asyncio
async def test_backup_scheduler_rejects_duplicate_pending_event(
    async_db_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("BACKUP_SCHEDULER_ENABLED", "true")
    first = await scheduler.schedule_due_backup(async_db_session)
    second = await scheduler.schedule_due_backup(async_db_session)
    assert first.status == "scheduled"
    assert second.status == "duplicate"
    assert second.event_id == first.event_id


@pytest.mark.asyncio
async def test_backup_scheduler_reports_overlap(
    async_db_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("BACKUP_SCHEDULER_ENABLED", "true")

    async def locked(_db):
        return False

    monkeypatch.setattr(scheduler, "_try_scheduler_lock", locked)
    result = await scheduler.schedule_due_backup(async_db_session)
    assert result.status == "overlap"


@pytest.mark.asyncio
async def test_backup_scheduler_skips_not_due_run(
    async_db_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("BACKUP_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("BACKUP_SCHEDULER_INTERVAL_SECONDS", "3600")
    now = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
    async_db_session.add(
        models.BackgroundJob(
            job_name=scheduler.BACKUP_JOB_NAME,
            status="success",
            completed_at=(now - timedelta(minutes=30)).replace(tzinfo=None),
        )
    )
    await async_db_session.commit()
    result = await scheduler.schedule_due_backup(async_db_session, now=now)
    assert result.status == "not_due"


@pytest.mark.asyncio
async def test_backup_scheduler_marks_missed_run(
    async_db_session: AsyncSession, monkeypatch
):
    monkeypatch.setenv("BACKUP_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("BACKUP_SCHEDULER_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("BACKUP_MISSED_RUN_GRACE_SECONDS", "300")
    now = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
    async_db_session.add(
        models.BackgroundJob(
            job_name=scheduler.BACKUP_JOB_NAME,
            status="success",
            completed_at=(now - timedelta(hours=2)).replace(tzinfo=None),
        )
    )
    await async_db_session.commit()
    result = await scheduler.schedule_due_backup(async_db_session, now=now)
    assert result.status == "scheduled"
    assert result.missed_run is True


@pytest.mark.asyncio
async def test_backup_worker_records_failure(
    async_db_session: AsyncSession, monkeypatch, tmp_path
):
    monkeypatch.setenv("BACKUP_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("SYSTEM_DATABASE_URL", "sqlite:///dentix_test.db")

    def fail_backup(_output_dir, _database_url):
        raise RuntimeError("synthetic backup failure")

    event = models.DomainEvent(
        event_type=scheduler.BACKUP_EVENT_TYPE,
        aggregate_type="SystemBackup",
        aggregate_id="failure",
        payload={},
    )
    with pytest.raises(RuntimeError, match="synthetic backup failure"):
        await scheduler.execute_backup_event(
            async_db_session, event, backup_callable=fail_backup
        )
    job = (
        await async_db_session.execute(
            select(models.BackgroundJob).order_by(models.BackgroundJob.id.desc())
        )
    ).scalars().first()
    assert job.status == "failed"
    assert "synthetic backup failure" in (job.error_message or "")


@pytest.mark.asyncio
async def test_backup_worker_uses_privileged_source_and_records_success(
    async_db_session: AsyncSession, monkeypatch, tmp_path
):
    monkeypatch.setenv("BACKUP_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "postgresql://app@db/dentix_test")
    monkeypatch.setenv(
        "SYSTEM_DATABASE_URL", "postgresql://system@db/dentix_test"
    )
    artifact = tmp_path / "backup.dump.enc"

    def succeed_backup(output_dir, database_url):
        assert output_dir == tmp_path
        assert database_url == "postgresql://system@db/dentix_test"
        return artifact

    event = models.DomainEvent(
        event_type=scheduler.BACKUP_EVENT_TYPE,
        aggregate_type="SystemBackup",
        aggregate_id="success",
        payload={},
    )
    assert await scheduler.execute_backup_event(
        async_db_session, event, backup_callable=succeed_backup
    ) == artifact
    job = (
        await async_db_session.execute(
            select(models.BackgroundJob).order_by(models.BackgroundJob.id.desc())
        )
    ).scalars().first()
    assert job.status == "success"


@pytest.mark.asyncio
async def test_backup_failure_requeues_outbox_event_for_retry(
    async_db_session: AsyncSession, monkeypatch, tmp_path
):
    monkeypatch.setenv("BACKUP_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("SYSTEM_DATABASE_URL", "sqlite:///dentix_test.db")

    event = event_service.emit_event(
        db=async_db_session,
        event_type=scheduler.BACKUP_EVENT_TYPE,
        aggregate_type="SystemBackup",
        aggregate_id="retry",
        payload={},
    )
    event.max_attempts = 2
    await async_db_session.commit()
    await async_db_session.refresh(event)

    def fail_backup(_output_dir, _database_url):
        raise RuntimeError("retry me")

    with pytest.raises(RuntimeError, match="retry me"):
        await scheduler.execute_backup_event(
            async_db_session, event, backup_callable=fail_backup
        )
    await event_service.mark_failed(async_db_session, event.id, "retry me")
    await async_db_session.refresh(event)
    assert event.status == "pending"
    assert event.attempts == 1
    assert event.available_at is not None
