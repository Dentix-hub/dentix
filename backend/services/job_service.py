from datetime import datetime
from sqlalchemy.orm import Session
from backend import models

class JobService:
    
    @staticmethod
    def start_job(db: Session, job_name: str, triggered_by: str = "system", tenant_id: int = None):
        """Creates a new job record with status 'running'."""
        new_job = models.BackgroundJob(
            job_name=job_name,
            status="running",
            triggered_by=triggered_by,
            tenant_id=tenant_id,
            started_at=datetime.now(datetime.UTC)
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job

    @staticmethod
    def complete_job(db: Session, job_id: int, status: str = "success", error: str = None):
        """Marks a job as finished."""
        job = db.get(models.BackgroundJob, job_id)
        if not job:
            return None
            
        job.completed_at = datetime.now(datetime.UTC)
        duration = (job.completed_at - job.started_at).total_seconds()
        job.duration_seconds = duration
        job.status = status
        
        if error:
            job.error_message = error
            
        db.commit()
        return job

    @staticmethod
    def get_recent_jobs(db: Session, limit: int = 50):
        """Fetch recent job logs."""
        return db.query(models.BackgroundJob).order_by(models.BackgroundJob.started_at.desc()).limit(limit).all()
