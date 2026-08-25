"""
Tests for Phase P10: Clinical PHI De-identification & AI Egress Controls.
"""

from backend.ai.security.sanitizer import AISanitizer


def test_ai_sanitizer_redacts_egyptian_national_id():
    raw_prompt = "Patient National ID is 29801011234567 and needs dental extraction."
    masked = AISanitizer.mask_sensitive_data(raw_prompt)
    assert "29801011234567" not in masked
    assert "[REDACTED_NATIONAL_ID]" in masked


def test_ai_sanitizer_redacts_egyptian_phone_numbers():
    raw_prompt = "Call patient at 01012345678 or +201123456789 for follow-up."
    masked = AISanitizer.mask_sensitive_data(raw_prompt)
    assert "01012345678" not in masked
    assert "+201123456789" not in masked
    assert "[REDACTED_PHONE]" in masked


def test_ai_sanitizer_redacts_credit_cards():
    raw_prompt = "Payment attempted with 4532 1122 3344 5566."
    masked = AISanitizer.mask_sensitive_data(raw_prompt)
    assert "4532 1122 3344 5566" not in masked
    assert "[HIDDEN_CARD]" in masked
