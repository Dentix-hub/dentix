from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
from backend.services.security_service import SecurityService
from backend.services.job_service import JobService
from backend.routers.auth import get_current_user
from backend.constants import ROLES

router = APIRouter(
    prefix="/admin/security",
    tags=["Admin Security"],
    responses={404: {"description": "Not found"}},
)

# --- Dependencies ---


def get_super_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Validate that the current user is a Super Admin (No Tenant ID)."""
    # Allow 'super_admin' OR 'admin' with no tenant (legacy compatibility)
    if current_user.role == ROLES.SUPER_ADMIN:
        return current_user

    if current_user.role == ROLES.ADMIN and current_user.tenant_id is None:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized: Super Admin access required",
    )


# --- Security Endpoints ---


@router.get("/stats", response_model=dict)
def get_security_stats(
    db: Session = Depends(get_db), _: models.User = Depends(get_super_admin)
):
    return SecurityService.get_security_stats(db)


@router.get("/blocked-ips", response_model=List[schemas.BlockedIP])
def get_blocked_ips(
    db: Session = Depends(get_db), _: models.User = Depends(get_super_admin)
):
    return db.query(models.BlockedIP).all()


@router.post("/ip-block", response_model=schemas.BlockedIP)
def block_ip(
    ip_data: schemas.BlockedIP,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin),
):
    return SecurityService.block_ip(
        db, ip_data.ip_address, ip_data.reason, current_user.username
    )


@router.delete("/ip-block/{ip_address}")
def unblock_ip(
    ip_address: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_super_admin),
):
    SecurityService.unblock_ip(db, ip_address)
    return {"message": "IP unblocked successfully"}


# --- System Health & Jobs ---


@router.get("/jobs", response_model=List[schemas.BackgroundJob])
def get_background_jobs(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_super_admin),
):
    return JobService.get_recent_jobs(db, limit)


@router.post("/jobs/trigger-test")
async def trigger_test_job(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_super_admin)
):
    """Trigger a dummy job asynchronously."""
    # Start job record
    job = JobService.start_job(
        db, "manual_test_job", triggered_by=current_user.username
    )

    # Simulate work without blocking main thread
    # In production, this should dispatch to Celery/ARQ
    # For now, we instantly complete it to avoid complexity
    JobService.complete_job(db, job.id, status="success")

    return {"message": "Test job executed successfully", "job_id": job.id}
