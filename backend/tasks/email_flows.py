from prefect import task, flow
import logging

logger = logging.getLogger("prefect.email_tasks")


@task(name="send_connection_email_task", retries=3, retry_delay_seconds=60)
def send_connection_email_task(email: str, subject: str, message: str):
    """
    Deliver a support/connection email through the configured SMTP server.

    SECURITY: never log the recipient address or the message body — both can
    carry sensitive content. The email service masks recipients itself.
    """
    logger.info("[WORKER] Starting email task...")

    from backend.email_service import send_plain_email

    sent = send_plain_email(to_email=email, subject=subject, text_body=message)
    if sent:
        logger.info("[WORKER] Email handed to SMTP successfully.")
        return {"status": "sent"}

    logger.error(
        "[WORKER] Email delivery failed (SMTP unavailable or not configured)."
    )
    return {"status": "failed", "reason": "smtp_unavailable"}


@flow(name="send-connection-email-flow")
def send_connection_email_flow(email: str, subject: str, message: str):
    """
    Flow that handles the connection email sending.
    """
    return send_connection_email_task(email, subject, message)
