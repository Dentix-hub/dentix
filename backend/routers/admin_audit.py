"""
Admin Audit Router.

Handles audit log and system error log endpoints.
Split from admin_system.py (B3.1).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timedelta

from backend import models, schemas
from backend.core.response import success_response, StandardResponse
from backend.database import get_async_db
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
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = None,
    user_id: int = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get audit logs with optional filters (Super Admin only)."""
    stmt = select(models.AuditLog)

    if tenant_id:
        stmt = stmt.where(models.AuditLog.tenant_id == tenant_id)
    if user_id:
        stmt = stmt.where(models.AuditLog.performed_by_id == user_id)
    if action:
        stmt = stmt.where(models.AuditLog.action == action)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            stmt = stmt.where(models.AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            stmt = stmt.where(models.AuditLog.created_at < end_dt)
        except ValueError:
            pass

    stmt = stmt.order_by(models.AuditLog.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    results = res.scalars().all()
    return success_response(list(results))


# --- System Error Logs ---
@router.get("/system/logs", response_model=StandardResponse[List[schemas.SystemError]])
async def get_system_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve system error logs (Super Admin only)."""
    stmt = select(models.SystemError).order_by(models.SystemError.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    results = res.scalars().all()
    return success_response(list(results))
