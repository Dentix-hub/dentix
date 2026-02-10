from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from backend.database import get_db  # Fixed import path
from backend import models
from backend.schemas import system_log as schemas
from backend.routers.auth import get_current_user

router = APIRouter()


# --- Public Endpoint for Frontend Errors ---
@router.post("", response_model=schemas.SystemError)
def log_frontend_error(
    error: schemas.SystemErrorCreate, request: Request, db: Session = Depends(get_db)
):
    """
    Log an error from the frontend app.
    Does NOT require authentication to prevent losing errors during login failures.
    We capture IP/UserAgent from request.
    """
    db_error = models.SystemError(
        **error.model_dump(),
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(db_error)
    db.commit()
    db.refresh(db_error)
    return db_error


# --- Admin Endpoint for Viewing Errors ---
@router.get("", response_model=List[schemas.SystemError])
def get_system_errors(
    skip: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(
        get_current_user
    ),  # Only admins should see this, refined later
):
    query = db.query(models.SystemError)

    if level:
        query = query.filter(models.SystemError.level == level)
    if source:
        query = query.filter(models.SystemError.source == source)

    return (
        query.order_by(models.SystemError.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
