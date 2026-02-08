from celery import shared_task
import time
import logging

logger = logging.getLogger(__name__)

@shared_task(name="send_connection_email")
def send_connection_email(email: str, subject: str, message: str):
    """
    Simulates sending an email via SMTP.
    In production, use simplelog, mailgun, or sendgrid here.
    """
    logger.info(f"[WORKER] Starting email task for {email}...")
    
    # Simulate network delay
    time.sleep(2)
    
    logger.info(f"[WORKER] Email Sent!")
    logger.info(f"To: {email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Body: {message}")
    
    return {"status": "sent", "email": email}
