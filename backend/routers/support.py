from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .. import models, schemas
from ..tasks.email_tasks import send_connection_email
from .auth import get_current_user, get_db
from ..constants import ROLES

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
        created_at=datetime.utcnow(),
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
        print(f"[WARNING] Failed to trigger background email: {e}")

    return db_message


@router.get("/messages", response_model=List[schemas.SupportMessage])
def get_feedback_messages(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Retrieve feedback messages (Super Admin only)."""
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view feedback messages",
        )

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
    current_user: models.User = Depends(get_current_user),
):
    """Update message status (read/archived)."""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    db_msg = (
        db.query(models.SupportMessage)
        .filter(models.SupportMessage.id == msg_id)
        .first()
    )
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    db_msg.status = status
    db.commit()
    return {"message": "Status updated"}


@router.delete("/messages/{msg_id}")
def delete_support_message(
    msg_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a support message (Super Admin only)."""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    db_msg = (
        db.query(models.SupportMessage)
        .filter(models.SupportMessage.id == msg_id)
        .first()
    )
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(db_msg)
    db.commit()
    return {"message": "Message deleted"}
