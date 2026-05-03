import pytest
from fastapi import HTTPException
from backend.routers.auth.dependencies import validate_password


@pytest.mark.parametrize(
    "password",
    [
        "Short1!",
        "A1@short",
        "NoDigitHere!!",
        "NoSpecial123",
        "12345678!",
        "qwerty!A1",
    ],
)
def test_weak_passwords_rejected(password):
    with pytest.raises(HTTPException) as exc:
        validate_password(password)
    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "password",
    [
        "M3d1c@l_D3nt1x!P4ss",
        "X7$kLm9#nPq2@Wx!Zz",
        "R8#tY2$uI5^oP9&lK3*",
        "Zx4!Cv7#Bn1$Mq9@We",
        "H2#jK8$lP5^sD3&fG1*",
    ],
)
def test_strong_passwords_accepted(password):
    validate_password(password)


def test_password_too_short_message():
    with pytest.raises(HTTPException) as exc:
        validate_password("A1@sho")
    assert exc.value.status_code == 400
    assert "8 أحرف" in exc.value.detail


def test_password_missing_classes_message():
    with pytest.raises(HTTPException) as exc:
        validate_password("alllowercase123")
    assert exc.value.status_code == 400


def test_password_weak_zxcvbn_message():
    with pytest.raises(HTTPException) as exc:
        validate_password("Password123!")
    assert exc.value.status_code == 400
    assert "ضعيفة" in exc.value.detail
