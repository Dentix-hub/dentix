from fastapi import APIRouter, Depends, HTTPException, status
from ..core.response import success_response, error_response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend import models, schemas
from backend.database import get_async_db
from backend.services.security_service import SecurityService
from backend.services.job_service import JobService
from backend.core.permissions import Role
from backend.core.permissions import Permission, require_permission


router = APIRouter(
    prefix="/admin/security",
    tags=["Admin Security"],
    responses={404: {"description": "Not found"}},
)

# --- Dependencies ---


def get_super_admin(
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> models.User:
    """Validate that the current user is a Super Admin (No Tenant ID)."""
    # Allow 'super_admin' OR 'admin' with no tenant (legacy compatibility)
    if current_user.role == Role.SUPER_ADMIN.value:
        return current_user

    if current_user.role == Role.ADMIN.value and current_user.tenant_id is None:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized: Super Admin access required",
    )


# --- Security Endpoints ---


@router.get("/stats", response_model=dict)
async def get_security_stats(
    db: AsyncSession = Depends(get_async_db), _: models.User = Depends(get_super_admin)
):
    return await SecurityService.get_security_stats(db)


# --- System Health & Jobs ---


@router.get("/jobs", response_model=List[schemas.BackgroundJob])
async def get_background_jobs(
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    _: models.User = Depends(get_super_admin),
):
    return await JobService.get_recent_jobs(db, limit)


@router.post("/jobs/trigger-test")
async def trigger_test_job(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(get_super_admin)
):
    """Trigger a dummy job asynchronously."""
    # Start job record
    job = await JobService.start_job(
        db, "manual_test_job", triggered_by=current_user.username
    )

    # Simulate work without blocking main thread
    # In production, this should dispatch to Celery/ARQ
    # For now, we instantly complete it to avoid complexity
    await JobService.complete_job(db, job.id, status="success")

    return success_response(data={"message": "Test job executed successfully", "job_id": job.id})
