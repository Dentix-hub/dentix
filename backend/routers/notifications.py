from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .. import models, schemas
from .auth import get_current_user, get_db
from ..constants import ROLES

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def require_super_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


@router.get("/", response_model=List[schemas.Notification])
def get_notifications(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Fetch notifications for the current user's tenant or global ones."""
    """Fetch notifications for the current user's tenant or global ones."""
    # Get all potential notifications
    notifications = (
        db.query(models.Notification)
        .filter(
            (models.Notification.is_global == True)
            | (models.Notification.tenant_id == current_user.tenant_id)
        )
        .order_by(models.Notification.created_at.desc())
        .limit(50)
        .all()
    )

    # Get user's interaction records (Read/Deleted)
    user_interactions = (
        db.query(models.NotificationRead)
        .filter(models.NotificationRead.user_id == current_user.id)
        .all()
    )

    read_ids = {r.notification_id for r in user_interactions}
    deleted_ids = {r.notification_id for r in user_interactions if r.is_deleted}

    # Filter and Map
    result = []
    for n in notifications:
        if n.id in deleted_ids:
            continue

        n_dict = schemas.Notification.from_orm(n)
        n_dict.is_read = n.id in read_ids
        result.append(n_dict)

    return result


@router.post("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a notification as read for the current user."""
    existing = (
        db.query(models.NotificationRead)
        .filter(
            models.NotificationRead.user_id == current_user.id,
            models.NotificationRead.notification_id == notification_id,
        )
        .first()
    )

    if not existing:
        read_record = models.NotificationRead(
            user_id=current_user.id, notification_id=notification_id
        )
        db.add(read_record)
        db.commit()

    return {"message": "Marked as read"}


@router.post("/{notification_id}/dismiss")
def dismiss_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Dismiss (hide) a notification for the current user."""
    existing = (
        db.query(models.NotificationRead)
        .filter(
            models.NotificationRead.user_id == current_user.id,
            models.NotificationRead.notification_id == notification_id,
        )
        .first()
    )

    if existing:
        existing.is_deleted = True
        # Ensure it's marked as read too if we dismiss it
        if not existing.read_at:
            existing.read_at = datetime.utcnow()
    else:
        new_record = models.NotificationRead(
            user_id=current_user.id,
            notification_id=notification_id,
            is_deleted=True,
            read_at=datetime.utcnow(),
        )
        db.add(new_record)

    db.commit()
    return {"message": "Notification dismissed"}


@router.post("/broadcast", response_model=schemas.Notification)
def broadcast_notification(
    notification: schemas.NotificationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Broadcast a new notification (Super Admin only)."""
    db_notification = models.Notification(
        **notification.dict(), created_by_id=current_user.id
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Delete a notification (Super Admin only)."""
    db_notification = (
        db.query(models.Notification)
        .filter(models.Notification.id == notification_id)
        .first()
    )
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(db_notification)
    db.commit()
    return {"message": "Notification deleted"}
