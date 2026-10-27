import logging

from backend import email_service


def test_missing_smtp_never_logs_reset_link_in_debug(monkeypatch, caplog):
    monkeypatch.setenv('DEBUG', 'true')
    monkeypatch.setattr(email_service, 'SMTP_USER', '')
    monkeypatch.setattr(email_service, 'SMTP_PASSWORD', '')
    with caplog.at_level(logging.INFO):
        assert not email_service.send_password_reset_email('synthetic@example.com', 'synthetic-reset-token', 'synthetic')
    assert 'synthetic-reset-token' not in caplog.text
    assert 'reset-password?token=' not in caplog.text
