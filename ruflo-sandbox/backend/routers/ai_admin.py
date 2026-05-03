from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime

from sqlalchemy.orm import Session
from typing import Optional
from .. import models
from .auth import get_db
from ..ai.analytics.service import AIAnalyticsService
from ..core.permissions import Role, Permission, require_permission

router = APIRouter(prefix="/ai/admin", tags=["AI Admin"])


@router.get("/stats")
def get_ai_stats(
    period: str = "month",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get AI usage statistics for admin dashboard."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        )

    tenant_id = None  # Force Global View for Super Admin
    return AIAnalyticsService.get_stats(db, period, tenant_id)


@router.get("/logs")
def get_ai_logs(
    skip: int = 0,
    limit: int = 20,
    tool: Optional[str] = Query(None, description="Filter by tool name"),
    username: Optional[str] = Query(None, description="Filter by username"),
    success_status: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get paginated AI logs."""
    tenant_id = None  # Force Global View

    filters = {
        "tool": tool,
        "username": username,
        "status": success_status,
        "start_date": start_date,
        "end_date": end_date,
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    return AIAnalyticsService.get_logs(db, skip, limit, tenant_id, filters)
