import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .. import models
from ..core.firebase_client import firebase_client

logger = logging.getLogger("smart_clinic")

class NotificationService:
    @staticmethod
    def send_to_user(db: Session, user_id: int, title: str, body: str, data: dict = None):
        """
        Sends a push notification to a specific user using their stored FCM token.
        """
        user = db.query(models.User).filter(models.User.id == user_id, models.User.is_active).first()

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
    def broadcast_to_role(db: Session, role: str, title: str, body: str, data: dict = None):
        """
        Sends push notifications to all active users with a specific role.
        """
        users = db.query(models.User).filter(
            models.User.role == role,
            models.User.is_active,
            models.User.fcm_token.isnot(None)
        ).all()

        success_count = 0
        for user in users:
            if firebase_client.send_push_notification(user.fcm_token, title, body, data):
                success_count += 1

        logger.info(f"Broadcast to {role} complete. Successful: {success_count}/{len(users)}")
        return success_count

    @staticmethod
    def register_token(db: Session, user_id: int, token: str):
        """
        Updates the FCM token for a user.
        """
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.fcm_token = token
            db.commit()
            return True
        return False
