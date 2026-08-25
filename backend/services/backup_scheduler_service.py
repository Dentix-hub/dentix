"""Durable disabled-by-default scheduling and execution for offline backups."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.config import (
    get_backup_missed_run_grace_seconds,
    get_backup_schedule_interval_seconds,
    is_backup_scheduler_enabled,
)
from backend.core.logging_sanitizer import sanitize_text
from backend.services.event_service import event_service
from backend.services.job_service import JobService
from scripts.ops.guarded_backup import create_backup


BACKUP_EVENT_TYPE = "system.backup.requested"
BACKUP_JOB_NAME = "system_backup"
BACKUP_ADVISORY_LOCK_KEY = 0x44454E544958  # ASCII-ish stable DENTIX key


@dataclass(frozen=True)
class BackupScheduleResult:
    status: str
    event_id: int | None = None
    missed_run: bool = False


async def _try_scheduler_lock(db: AsyncSession) -> bool:
    if db.get_bind().dialect.name != "postgresql":
        return True
    return bool(
        (
            await db.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": BACKUP_ADVISORY_LOCK_KEY},
            )
        ).scalar_one()
    )


async def schedule_due_backup(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> BackupScheduleResult:
    """Create at most one durable backup event when the configured run is due."""
    if not is_backup_scheduler_enabled():
        return BackupScheduleResult("disabled")
    if not await _try_scheduler_lock(db):
        return BackupScheduleResult("overlap")

    current = now or datetime.now(timezone.utc)
    active = (
        await db.execute(
            select(models.DomainEvent)
            .where(
                models.DomainEvent.event_type == BACKUP_EVENT_TYPE,
                models.DomainEvent.status.in_(("pending", "processing")),
            )
            .order_by(models.DomainEvent.created_at.desc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
    ).scalars().first()
    if active is not None:
        return BackupScheduleResult("duplicate", event_id=active.id)

    last_success = (
        await db.execute(
            select(models.BackgroundJob)
            .where(
                models.BackgroundJob.job_name == BACKUP_JOB_NAME,
                models.BackgroundJob.status == "success",
            )
            .order_by(models.BackgroundJob.completed_at.desc())
            .limit(1)
        )
    ).scalars().first()

    interval = timedelta(seconds=get_backup_schedule_interval_seconds())
    grace = timedelta(seconds=get_backup_missed_run_grace_seconds())
    missed_run = False
    if last_success is not None and last_success.completed_at is not None:
        completed_at = last_success.completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        elapsed = current - completed_at
        if elapsed < interval:
            return BackupScheduleResult("not_due")
        missed_run = elapsed > interval + grace

    bucket = int(current.timestamp()) // max(
        get_backup_schedule_interval_seconds(), 1
    )
    event = event_service.emit_event(
        db=db,
        event_type=BACKUP_EVENT_TYPE,
        aggregate_type="SystemBackup",
        aggregate_id=str(bucket),
        tenant_id=None,
        payload={
            "scheduled_for": current.isoformat(),
            "missed_run": missed_run,
        },
    )
    await db.commit()
    await db.refresh(event)
    return BackupScheduleResult("scheduled", event_id=event.id, missed_run=missed_run)


async def execute_backup_event(
    db: AsyncSession,
    event: models.DomainEvent,
    *,
    backup_callable: Callable[[Path, str | None], Path] = create_backup,
) -> Path:
    """Execute one backup event and retain success/failure job evidence."""
    job = await JobService.start_job(db, BACKUP_JOB_NAME, triggered_by="outbox")
    output_dir = Path(os.getenv("BACKUP_OUTPUT_DIR", "backups/offline"))
    try:
        # Full-platform backups must not use the tenant-restricted application
        # role, which would silently produce an incomplete dump without context.
        database_url = os.getenv("BACKUP_SOURCE_DATABASE_URL") or os.getenv(
            "SYSTEM_DATABASE_URL"
        )
        if not database_url:
            raise RuntimeError(
                "BACKUP_SOURCE_DATABASE_URL or SYSTEM_DATABASE_URL is required"
            )
        artifact = await asyncio.to_thread(
            backup_callable,
            output_dir,
            database_url,
        )
    except Exception as exc:
        safe_error = sanitize_text(str(exc), max_length=1000) or "backup failed"
        await JobService.complete_job(db, job.id, status="failed", error=safe_error)
        raise

    await JobService.complete_job(db, job.id, status="success")
    return artifact
