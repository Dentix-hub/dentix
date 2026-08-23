"""Support email flow honesty + privacy contract (Medium defect, audit §6)."""

from unittest.mock import patch

from backend.tasks.email_flows import send_connection_email_task


def test_task_reports_sent_only_when_smtp_delivers():
    with patch(
        "backend.email_service.send_plain_email", return_value=True
    ) as mock_send:
        result = send_connection_email_task.fn(
            email="user@example.com", subject="Hi", message="body"
        )

    assert result == {"status": "sent"}
    mock_send.assert_called_once_with(
        to_email="user@example.com", subject="Hi", text_body="body"
    )


def test_task_reports_failed_when_smtp_not_configured():
    with patch("backend.email_service.send_plain_email", return_value=False):
        result = send_connection_email_task.fn(
            email="user@example.com", subject="Hi", message="body"
        )

    assert result["status"] == "failed"
    assert "sent" != result["status"]


def test_task_never_logs_message_content(recap=None):
    import logging

    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = Capture()
    logger = logging.getLogger("prefect.email_tasks")
    logger.addHandler(handler)
    try:
        with patch("backend.email_service.send_plain_email", return_value=True):
            send_connection_email_task.fn(
                email="secret-user@example.com",
                subject="Secret Subject",
                message="Secret medical body content",
            )
    finally:
        logger.removeHandler(handler)

    joined = "\n".join(records)
    assert "secret-user@example.com" not in joined
    assert "Secret medical body content" not in joined
