from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from backend.database import get_db  # Fixed import path
from backend import models
from backend.schemas import system_log as schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse

router = APIRouter()


# --- Public Endpoint for Frontend Errors ---
@router.post("", response_model=StandardResponse[schemas.SystemError])
def log_frontend_error(
    error: schemas.SystemErrorCreate, request: Request, db: Session = Depends(get_db)
):
    """
    Log an error from the frontend app.
    Does NOT require authentication to prevent losing errors during login failures.
    We capture IP/UserAgent from request.
    """
    # Extract data to avoid duplicate key issues if schema already has keys
    error_data = error.model_dump()
    # Prioritize request context for security/reliability
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        error_data["ip_address"] = forwarded_for.split(",")[0].strip()
    else:
        error_data["ip_address"] = request.client.host if request.client else None

    if not error_data.get("user_agent"):
        error_data["user_agent"] = request.headers.get("user-agent")

    db_error = models.SystemError(**error_data)
    db.add(db_error)
    db.commit()
    db.refresh(db_error)
    return success_response(data=db_error)


# --- Admin Endpoint for Viewing Errors ---
@router.get("", response_model=StandardResponse[List[schemas.SystemError]])
def get_system_errors(
    skip: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(Permission.SYSTEM_CONFIG)
    ),
):
    query = db.query(models.SystemError)

    if level:
        query = query.filter(models.SystemError.level == level)
    if source:
        query = query.filter(models.SystemError.source == source)

    results = (
        query.order_by(models.SystemError.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return success_response(data=results)
