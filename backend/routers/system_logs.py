from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_async_db
from backend import models
from backend.schemas import system_log as schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse
from backend.core.limiter import limiter

router = APIRouter()


from backend.core.logging_sanitizer import sanitize_text, sanitize_stack_trace

# --- Public Endpoint for Frontend Errors ---
@router.post("", response_model=StandardResponse[schemas.SystemError])
@limiter.limit("10/minute")
async def log_frontend_error(
    error: schemas.SystemErrorCreate, request: Request, db: AsyncSession = Depends(get_async_db)
):
    """
    Log an error from the frontend app.
    Does NOT require authentication to prevent losing errors during login failures.
    We capture IP/UserAgent from request and sanitize all content.
    """
    error_data = error.model_dump()
    error_data["message"] = sanitize_text(error_data.get("message"), max_length=4000) or "Frontend Error"
    error_data["stack_trace"] = sanitize_stack_trace(error_data.get("stack_trace"), max_length=12000)
    error_data["path"] = sanitize_text(error_data.get("path"), max_length=2048)

    error_data.update(
        {
            "source": "FRONTEND",
            "user_id": None,
            "tenant_id": None,
            "ip_address": request.client.host if request.client else None,
            "user_agent": sanitize_text(request.headers.get("user-agent"), max_length=512),
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
    limit: int = Query(default=100, ge=1, le=200),
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
