from prefect import task, flow
import logging

logger = logging.getLogger("prefect.email_tasks")


@task(name="send_connection_email_task", retries=3, retry_delay_seconds=60)
def send_connection_email_task(email: str, subject: str, message: str):
    """
    Task to simulate sending an email via SMTP.
    """
    logger.info(f"[WORKER] Starting email task for {email}...")

    logger.info("[WORKER] Email Sent!")
    logger.info(f"To: {email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Body: {message}")

    return {"status": "sent", "email": email}


@flow(name="send-connection-email-flow")
def send_connection_email_flow(email: str, subject: str, message: str):
    """
    Flow that handles the connection email sending.
    """
    return send_connection_email_task(email, subject, message)
