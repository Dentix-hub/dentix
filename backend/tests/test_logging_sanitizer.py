"""
Unit tests for backend/core/logging_sanitizer.py.
Verifies redaction of JWTs, passwords, database URLs, National IDs, Egyptian phone numbers, and length bounds.
"""

from backend.core.logging_sanitizer import (
    sanitize_text,
    sanitize_stack_trace,
    sanitize_dict,
    BoundedSanitizingFilter,
)
import logging


def test_sanitize_jwt_and_bearer_tokens():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.do_not_leak_signature_here"
    msg = f"User logged in with header: Bearer {jwt}"
    cleaned = sanitize_text(msg)
    assert jwt not in cleaned
    assert "[REDACTED_JWT]" in cleaned


def test_sanitize_passwords_and_urls():
    url = "postgresql://dentix_user:super_secret_db_pass@127.0.0.1:5432/dentix_prod"
    cleaned = sanitize_text(url)
    assert "super_secret_db_pass" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned

    json_msg = '{"username": "admin", "password": "super_secret_login_123", "token": "abc123xyz"}'
    cleaned_json = sanitize_text(json_msg)
    assert "super_secret_login_123" not in cleaned_json
    assert "abc123xyz" not in cleaned_json
    assert "[REDACTED]" in cleaned_json


def test_sanitize_national_id_and_phone():
    nid = "29801011234567"
    phone = "01012345678"
    msg = f"Patient registration: National ID={nid}, Phone={phone}"
    cleaned = sanitize_text(msg)
    assert nid not in cleaned
    assert phone not in cleaned
    assert "298********567" in cleaned
    assert "010****5678" in cleaned


def test_sanitize_length_bounding():
    huge_text = "A" * 10000
    cleaned = sanitize_text(huge_text, max_length=1000)
    assert len(cleaned) <= 1050
    assert "[TRUNCATED]" in cleaned


def test_sanitize_dict_recursive():
    payload = {
        "user": "dr_ahmed",
        "password": "plain_password_here",
        "nested": {
            "api_key": "secret_key_123",
            "phone": "01123456789",
        },
        "tags": ["safe", "01234567890"]
    }
    cleaned = sanitize_dict(payload)
    assert cleaned["user"] == "dr_ahmed"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["nested"]["api_key"] == "[REDACTED]"
    assert "01123456789" not in cleaned["nested"]["phone"]
    assert "01234567890" not in cleaned["tags"][1]


def test_bounded_sanitizing_filter():
    logger = logging.getLogger("test_sanitizing_logger")
    logger.setLevel(logging.INFO)
    filt = BoundedSanitizingFilter()
    logger.addFilter(filt)

    record = logger.makeRecord(
        "test_sanitizing_logger",
        logging.INFO,
        "test.py",
        10,
        "Failed login with password: %s",
        ("secret_password_in_args",),
        None
    )
    filt.filter(record)
    assert "secret_password_in_args" not in record.msg
