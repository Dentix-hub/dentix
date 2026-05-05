import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from .. import models
from ..core.permissions import Role

logger = logging.getLogger("smart_clinic")

class InternalNotificationService:
    @staticmethod
    def send_system_email(subject: str, message_body: str):
        """
        Send a critical system email to all Super Admins.
        Configuration is pulled from environment variables.
        """
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("SENDER_EMAIL", "alerts@dentix.app")

        if not smtp_user or not smtp_password:
            logger.warning("SMTP credentials not configured. Cannot send system alert email.")
            # Fallback to logging
            logger.error(f"SYSTEM ALERT [{subject}]: {message_body}")
            return False

        try:
            # Note: In a real system, you'd fetch Super Admin emails from DB
            # For now, we'll use a placeholder logic or send to a configured admin group
            recipients = [os.getenv("ADMIN_ALERT_EMAIL", smtp_user)]

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = f"[DENTIX CRITICAL] {subject}"

            msg.attach(MIMEText(message_body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()

            logger.info(f"System alert email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send system email: {e}")
            return False

    @staticmethod
    def notify_super_admins(db: Session, title: str, body: str):
        """
        Notify all Super Admins via multiple channels (Email, FCM).
        """
        # 1. Email (Critical)
        InternalNotificationService.send_system_email(title, body)

        # 2. FCM (Push)
        from .notification_service import NotificationService
        NotificationService.broadcast_to_role(db, Role.SUPER_ADMIN.value, title, body)
