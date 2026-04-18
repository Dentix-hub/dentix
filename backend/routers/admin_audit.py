"""
Admin Audit Router.

Handles audit log and system error log endpoints.
Split from admin_system.py (B3.1).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from backend import models, schemas
from backend.core.response import success_response, StandardResponse
from backend.database import get_db
from backend.core.permissions import Role, Permission, require_permission

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/admin",
    tags=["Admin — Audit"],
    responses={404: {"description": "Not found"}},
)


def require_super_admin(
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# --- Audit Logs ---
@router.get("/audit-logs", response_model=StandardResponse[List[schemas.AuditLog]])
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = None,
    user_id: int = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get audit logs with optional filters (Super Admin only)."""
    query = db.query(models.AuditLog)

    if tenant_id:
        query = query.filter(models.AuditLog.tenant_id == tenant_id)
    if user_id:
        query = query.filter(models.AuditLog.performed_by_id == user_id)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(models.AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(models.AuditLog.created_at < end_dt)
        except ValueError:
            pass

    results = (
        query.order_by(models.AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return success_response(results)


# --- System Error Logs ---
@router.get("/system/logs", response_model=StandardResponse[List[schemas.SystemError]])
def get_system_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Retrieve system error logs (Super Admin only)."""
    results = (
        db.query(models.SystemError)
        .order_by(models.SystemError.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return success_response(results)
