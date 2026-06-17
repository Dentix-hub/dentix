from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models


class JobService:
    @staticmethod
    async def start_job(
        db: AsyncSession, job_name: str, triggered_by: str = "system", tenant_id: int = None
    ):
        """Creates a new job record with status 'running'."""
        new_job = models.BackgroundJob(
            job_name=job_name,
            status="running",
            triggered_by=triggered_by,
            tenant_id=tenant_id,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        return new_job

    @staticmethod
    async def complete_job(
        db: AsyncSession, job_id: int, status: str = "success", error: str = None
    ):
        """Marks a job as finished."""
        job = await db.get(models.BackgroundJob, job_id)
        if not job:
            return None

        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        duration = (job.completed_at - job.started_at).total_seconds()
        job.duration_seconds = duration
        job.status = status

        if error:
            job.error_message = error

        await db.commit()
        return job

    @staticmethod
    async def get_recent_jobs(db: AsyncSession, limit: int = 50):
        """Fetch recent job logs."""
        stmt = (
            select(models.BackgroundJob)
            .order_by(models.BackgroundJob.started_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())
