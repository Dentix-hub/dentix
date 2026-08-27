from fastapi import APIRouter, Depends, HTTPException
from backend.core.permissions import Permission, require_permission
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timezone
from backend.core.response import success_response, StandardResponse

from .. import models, schemas
from .auth import get_async_db
from backend.core.permissions import Role

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def require_super_admin(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


async def _require_visible_notification(
    db: AsyncSession,
    current_user: models.User,
    notification_id: int,
) -> models.Notification:
    """Resolve an interaction target only from the user's visible notification set."""
    stmt = select(models.Notification).filter(
        models.Notification.id == notification_id,
        (models.Notification.is_global)
        | (models.Notification.tenant_id == current_user.tenant_id),
    )
    notification = (await db.execute(stmt)).scalars().first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.get("", response_model=StandardResponse[List[schemas.Notification]])
async def get_notifications(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.PATIENT_READ))
):
    """Fetch notifications for the current user's tenant or global ones."""
    stmt = (
        select(models.Notification)
        .filter(
            (models.Notification.is_global)
            | (models.Notification.tenant_id == current_user.tenant_id)
        )
        .order_by(models.Notification.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    stmt_read = (
        select(models.NotificationRead)
        .filter(models.NotificationRead.user_id == current_user.id)
    )
    result_read = await db.execute(stmt_read)
    user_interactions = result_read.scalars().all()

    read_ids = {r.notification_id for r in user_interactions}
    deleted_ids = {r.notification_id for r in user_interactions if r.is_deleted}

    final_result = []
    for n in notifications:
        if n.id in deleted_ids:
            continue

        n_dict = schemas.Notification.from_orm(n)
        n_dict.is_read = n.id in read_ids
        final_result.append(n_dict)

    return success_response(data=final_result)


@router.post("/{notification_id}/read", response_model=StandardResponse[dict])
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Mark a notification as read for the current user."""
    await _require_visible_notification(db, current_user, notification_id)

    stmt = (
        select(models.NotificationRead)
        .filter(
            models.NotificationRead.user_id == current_user.id,
            models.NotificationRead.notification_id == notification_id,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if not existing:
        read_record = models.NotificationRead(
            user_id=current_user.id, notification_id=notification_id
        )
        db.add(read_record)
        await db.commit()

    return success_response(message="Marked as read")


@router.post("/{notification_id}/dismiss", response_model=StandardResponse[dict])
async def dismiss_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Dismiss (hide) a notification for the current user."""
    await _require_visible_notification(db, current_user, notification_id)

    stmt = (
        select(models.NotificationRead)
        .filter(
            models.NotificationRead.user_id == current_user.id,
            models.NotificationRead.notification_id == notification_id,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if existing:
        existing.is_deleted = True
        if not existing.read_at:
            existing.read_at = datetime.now(timezone.utc)
    else:
        new_record = models.NotificationRead(
            user_id=current_user.id,
            notification_id=notification_id,
            is_deleted=True,
            read_at=datetime.now(timezone.utc),
        )
        db.add(new_record)

    await db.commit()
    return success_response(message="Notification dismissed")


@router.post("/broadcast", response_model=StandardResponse[schemas.Notification])
async def broadcast_notification(
    notification: schemas.NotificationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Broadcast a new notification (Super Admin only)."""
    if not notification.is_global:
        if notification.tenant_id is None:
            raise HTTPException(
                status_code=422,
                detail="tenant_id is required for targeted notifications",
            )
        stmt = select(models.Tenant).where(models.Tenant.id == notification.tenant_id)
        target_tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(status_code=404, detail="Targeted tenant not found")
    else:
        notification.tenant_id = None

    db_notification = models.Notification(
        **notification.model_dump(), created_by_id=current_user.id
    )
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return success_response(data=db_notification, message="Notification broadcasted")


@router.delete("/{notification_id}", response_model=StandardResponse[dict])
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Delete a notification (Super Admin only)."""
    stmt = select(models.Notification).filter(models.Notification.id == notification_id)
    result = await db.execute(stmt)
    db_notification = result.scalars().first()
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(db_notification)
    await db.commit()
    return success_response(message="Notification deleted")
