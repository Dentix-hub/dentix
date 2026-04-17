"""
Dashboard Router
Handles dashboard statistics.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models, schemas, crud
from .auth import get_db
from backend.services.cache_service import cached
from backend.core.limiter import limiter
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/stats", tags=["Dashboard"])


@router.get("/dashboard", response_model=StandardResponse[schemas.DashboardStats])
@limiter.limit("30/minute")  # Tighter limit for heavy endpoint
@cached(key_prefix="dashboard_stats", expire=60)  # Cache for 60 seconds
def get_dashboard_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    """Get dashboard statistics for current tenant."""
    doctor_id = current_user.id if current_user.role == "doctor" else None
    data = crud.get_dashboard_stats(db, current_user.tenant_id, doctor_id=doctor_id)
    return success_response(data=data)


@router.get("/finance", response_model=StandardResponse[schemas.FinancialStats])
@limiter.limit("30/minute")  # Tighter limit for heavy endpoint
@cached(key_prefix="finance_stats", expire=60)  # Cache for 60 seconds
def get_finance_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get financial statistics for current tenant."""
    doctor_id = current_user.id if current_user.role == "doctor" else None
    data = crud.get_financial_stats(db, current_user.tenant_id, doctor_id=doctor_id)
    return success_response(data=data)
