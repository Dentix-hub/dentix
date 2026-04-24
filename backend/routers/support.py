import logging
from fastapi import APIRouter, Depends, HTTPException
from ..core.response import success_response, error_response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from .. import models, schemas
from ..tasks.email_tasks import send_connection_email
from .auth import get_current_user, get_db
from ..core.permissions import Permission, require_permission

router = APIRouter(prefix="/support", tags=["Support & Feedback"])


@router.post("/feedback", response_model=schemas.SupportMessage)
def create_feedback(
    message: schemas.SupportMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Submit a feedback/support message."""
    db_message = models.SupportMessage(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        subject=message.subject,
        message=message.message,
        priority=message.priority,
        status="unread",
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # Manually attach names for the response
    db_message.username = current_user.username
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.id == current_user.tenant_id)
        .first()
    )
    db_message.clinic_name = tenant.name if tenant else "Unknown"

    # Trigger Background Task
    try:
        send_connection_email.delay(
            email=current_user.email,
            subject=f"New Support Message: {message.subject}",
            message=message.message,
        )
    except Exception as e:
        # Don't fail the request if Celery is down, just log it
        logger.warning("Failed to trigger background email: %s", e)

    return db_message


@router.get("/messages", response_model=List[schemas.SupportMessage])
def get_feedback_messages(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))
):
    """Retrieve feedback messages (Admin+ only)."""

    messages = (
        db.query(models.SupportMessage)
        .order_by(models.SupportMessage.created_at.desc())
        .all()
    )

    # Attach names for display
    for msg in messages:
        user = db.query(models.User).filter(models.User.id == msg.user_id).first()
        tenant = (
            db.query(models.Tenant).filter(models.Tenant.id == msg.tenant_id).first()
        )
        msg.username = user.username if user else "Deleted User"
        msg.clinic_name = tenant.name if tenant else "Deleted Clinic"

    return messages


@router.put("/messages/{msg_id}/status")
def update_message_status(
    msg_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update message status (read/archived)."""

    db_msg = (
        db.query(models.SupportMessage)
        .filter(models.SupportMessage.id == msg_id)
        .first()
    )
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    db_msg.status = status
    db.commit()
    return success_response(data={"message": "Status updated"})


@router.delete("/messages/{msg_id}")
def delete_support_message(
    msg_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a support message (Admin+ only)."""

    db_msg = (
        db.query(models.SupportMessage)
        .filter(models.SupportMessage.id == msg_id)
        .first()
    )
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(db_msg)
    db.commit()
    return success_response(data={"message": "Message deleted"})
