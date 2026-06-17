import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from ..core.response import success_response, error_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from .. import models, schemas
from ..tasks.email_flows import send_connection_email_flow
from .auth import get_current_user, get_async_db
from ..core.permissions import Permission, require_permission

router = APIRouter(prefix="/support", tags=["Support & Feedback"])


@router.post("/feedback", response_model=schemas.SupportMessage)
async def create_feedback(
    message: schemas.SupportMessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
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
    await db.commit()
    await db.refresh(db_message)

    # Manually attach names for the response
    db_message.username = current_user.username
    tenant = None
    if current_user.tenant_id:
        tenant_result = await db.execute(
            select(models.Tenant).filter(models.Tenant.id == current_user.tenant_id)
        )
        tenant = tenant_result.scalars().first()
    db_message.clinic_name = tenant.name if tenant else "Unknown"

    # Trigger Background Task via Prefect Flow
    try:
        background_tasks.add_task(
            send_connection_email_flow,
            email=current_user.email,
            subject=f"New Support Message: {message.subject}",
            message=message.message,
        )
    except Exception as e:
        logger.warning("Failed to trigger background email flow: %s", e)

    return db_message


@router.get("/messages", response_model=List[schemas.SupportMessage])
async def get_feedback_messages(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))
):
    """Retrieve feedback messages (Admin+ only)."""

    result = await db.execute(
        select(models.SupportMessage)
        .order_by(models.SupportMessage.created_at.desc())
    )
    messages = result.scalars().all()

    # Attach names for display
    for msg in messages:
        user_result = await db.execute(
            select(models.User).filter(models.User.id == msg.user_id)
        )
        user = user_result.scalars().first()
        tenant = None
        if msg.tenant_id:
            tenant_result = await db.execute(
                select(models.Tenant).filter(models.Tenant.id == msg.tenant_id)
            )
            tenant = tenant_result.scalars().first()
        msg.username = user.username if user else "Deleted User"
        msg.clinic_name = tenant.name if tenant else "Deleted Clinic"

    return messages


@router.put("/messages/{msg_id}/status")
async def update_message_status(
    msg_id: int,
    status: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update message status (read/archived)."""

    result = await db.execute(
        select(models.SupportMessage)
        .filter(models.SupportMessage.id == msg_id)
    )
    db_msg = result.scalars().first()
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    db_msg.status = status
    await db.commit()
    return success_response(data={"message": "Status updated"})


@router.delete("/messages/{msg_id}")
async def delete_support_message(
    msg_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a support message (Admin+ only)."""

    result = await db.execute(
        select(models.SupportMessage)
        .filter(models.SupportMessage.id == msg_id)
    )
    db_msg = result.scalars().first()
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.delete(db_msg)
    await db.commit()
    return success_response(data={"message": "Message deleted"})
