import re
from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_async_db
from backend import models
from backend.schemas import system_log as schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse
from backend.core.limiter import limiter

router = APIRouter()


# --- Public Endpoint for Frontend Errors ---
@router.post("", response_model=StandardResponse[schemas.SystemError])
@limiter.limit("5/minute")
async def log_frontend_error(
    error: schemas.SystemErrorCreate, request: Request, db: AsyncSession = Depends(get_async_db)
):
    """
    Log an error from the frontend app.
    Does NOT require authentication to prevent losing errors during login failures.
    We capture IP/UserAgent from request.
    """
    error_data = error.model_dump()
    # Prevent credentials and bearer tokens from being persisted in telemetry.
    secret_pattern = re.compile(
        r"(?i)(authorization|cookie|password|secret|token|api[-_]?key)(\s*[:=]\s*)([^\s,;]+)"
    )
    for field in ("message", "stack_trace"):
        value = error_data.get(field)
        if value:
            error_data[field] = secret_pattern.sub(r"\1\2[REDACTED]", value)

    error_data.update(
        {
            "source": "FRONTEND",
            "user_id": None,
            "tenant_id": None,
            "ip_address": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:500] or None,
        }
    )

    db_error = models.SystemError(**error_data)
    db.add(db_error)
    await db.commit()
    await db.refresh(db_error)
    return success_response(data=db_error)


# --- Admin Endpoint for Viewing Errors ---
@router.get("", response_model=StandardResponse[List[schemas.SystemError]])
async def get_system_errors(
    skip: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(
        require_permission(Permission.SYSTEM_CONFIG)
    ),
):
    stmt = select(models.SystemError)

    if level:
        stmt = stmt.filter(models.SystemError.level == level)
    if source:
        stmt = stmt.filter(models.SystemError.source == source)

    stmt = stmt.order_by(models.SystemError.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    results = result.scalars().all()
    return success_response(data=results)
