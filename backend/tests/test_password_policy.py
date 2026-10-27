import pytest
from fastapi import HTTPException
from backend.routers.auth.dependencies import (
    COMMON_WEAK_PASSWORDS,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    validate_password,
)


def test_password_min_length_constant():
    assert PASSWORD_MIN_LENGTH == 8
    assert PASSWORD_MAX_LENGTH == 72
    assert len(COMMON_WEAK_PASSWORDS) >= 100


def test_browser_policy_data_matches_backend():
    import json
    from pathlib import Path
    from scripts.generate_password_policy import policy_data

    path = Path(__file__).parents[2] / "frontend/src/auth/passwordPolicyData.json"
    browser = json.loads(path.read_text())
    assert browser == policy_data(), "Run python scripts/generate_password_policy.py"
    assert set(browser["weakPasswords"]) == COMMON_WEAK_PASSWORDS
    assert browser["minLength"] == PASSWORD_MIN_LENGTH
    assert browser["maxLength"] == PASSWORD_MAX_LENGTH


@pytest.mark.parametrize(
    "password",
    [
        "abc12345",
        "ahmed2024",
        "كلمة1234",
        "Str0ng!Pass#2026",
        "طبيب2026ماهر",
        "ALLCAPS2026",
    ],
)
def test_password_policy_accepted(password):
    validate_password(password)


@pytest.mark.parametrize(
    "password,expected_substring",
    [
        ("abc1234", "8 أحرف على الأقل"),  # too short (< 8)
        ("abcdefgh", "حروف وأرقام على الأقل"),  # letters only, no digit
        ("12345678", "حروف وأرقام على الأقل"),  # digits only, no letter
        ("password1", "ضعيفة جداً وشائعة الاستخدام"),  # common blocklist
        ("PASSWORD1", "ضعيفة جداً وشائعة الاستخدام"),  # case-insensitive blocklist
        ("11111111a1", "ضعيفة جداً وشائعة الاستخدام"),  # 11111111a1-style blocklist
        ("qwerty123", "ضعيفة جداً وشائعة الاستخدام"),  # common blocklist
        ("admin123", "ضعيفة جداً وشائعة الاستخدام"),  # common blocklist
        ("dentix123", "ضعيفة جداً وشائعة الاستخدام"),  # common blocklist
        ("a1" * 37, "لا تزيد عن 72 حرفاً"),  # > 72 chars (74 chars)
    ],
)
def test_password_policy_rejected(password, expected_substring):
    with pytest.raises(HTTPException) as exc:
        validate_password(password)
    assert exc.value.status_code == 400
    assert expected_substring in exc.value.detail


@pytest.mark.parametrize(
    "password,username",
    [
        ("ahmed2024", "ahmed2024"),
        ("Ahmed2024", "ahmed2024"),
        ("أحمد2024", "احمد2024"),
        ("  dr_sara12  ", "dr_sara12"),
    ],
)
def test_password_same_as_username_rejected(password, username):
    with pytest.raises(HTTPException) as exc:
        validate_password(password, username=username)
    assert exc.value.status_code == 400
    assert "مطابقة لاسم المستخدم" in exc.value.detail
