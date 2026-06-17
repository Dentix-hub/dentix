import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models
from ..core.firebase_client import firebase_client

logger = logging.getLogger("smart_clinic")

class NotificationService:
    @staticmethod
    async def send_to_user(db: AsyncSession, user_id: int, title: str, body: str, data: dict = None):
        """
        Sends a push notification to a specific user using their stored FCM token.
        """
        stmt = select(models.User).where(models.User.id == user_id, models.User.is_active == True)  # noqa: E712
        user = (await db.execute(stmt)).scalar_one_or_none()

        if not user or not user.fcm_token:
            logger.warning(f"Cannot send notification to user {user_id}: No FCM token found.")
            return False

        return firebase_client.send_push_notification(
            token=user.fcm_token,
            title=title,
            body=body,
            data=data
        )

    @staticmethod
    async def broadcast_to_role(db: AsyncSession, role: str, title: str, body: str, data: dict = None):
        """
        Sends push notifications to all active users with a specific role.
        """
        stmt = select(models.User).where(
            models.User.role == role,
            models.User.is_active == True,  # noqa: E712
            models.User.fcm_token.isnot(None)
        )
        users = (await db.execute(stmt)).scalars().all()

        success_count = 0
        for user in users:
            if firebase_client.send_push_notification(user.fcm_token, title, body, data):
                success_count += 1

        logger.info(f"Broadcast to {role} complete. Successful: {success_count}/{len(users)}")
        return success_count

    @staticmethod
    async def register_token(db: AsyncSession, user_id: int, token: str):
        """
        Updates the FCM token for a user.
        """
        stmt = select(models.User).where(models.User.id == user_id)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if user:
            user.fcm_token = token
            await db.commit()
            return True
        return False
