"""Browser persistence is bound to the stored refresh session."""
import uuid

import pyotp
import pytest

from backend import auth
from backend.models import User


def assert_cookie_mode(response, persistent):
    cookies = response.headers.get_list("set-cookie")
    for name in ("access_token", "refresh_token", "dentix_session_hint", "csrf_token"):
        cookie = next(c for c in cookies if c.startswith(name + "="))
        assert ("Max-Age=" in cookie) is persistent
        assert "expires=" not in cookie.lower()


@pytest.mark.parametrize("choice", [None, "true", "false"])
def test_login_and_rotation_preserve_mode(client, super_admin_user, choice):
    payload = {"username": super_admin_user.username, "password": "superpass123"}
    if choice is not None:
        payload["remember_me"] = choice
    login = client.post("/api/v1/auth/token", data=payload)
    assert login.status_code == 200, login.text
    persistent = choice != "false"
    assert_cookie_mode(login, persistent)
    token = login.json()["refresh_token"]
    refresh = client.post("/api/v1/auth/refresh", data={"refresh_token": token, "remember_me": "true"})
    assert refresh.status_code == 200, refresh.text
    assert_cookie_mode(refresh, persistent)
    assert refresh.json()["refresh_token"] != token


@pytest.mark.parametrize("persistent", [True, False])
def test_2fa_preserves_login_choice(db_session, client, test_tenant, persistent):
    username = "remember_" + uuid.uuid4().hex[:8]
    secret = "JBSWY3DPEHPK3PXP"
    user = User(username=username, email=username + "@example.com", role="doctor",
                tenant_id=test_tenant.id, is_active=True, is_2fa_enabled=True,
                otp_secret=secret, hashed_password=auth.get_password_hash("ValidPass1!"))
    db_session.add(user)
    db_session.commit()
    first = client.post("/api/v1/auth/token", data={"username": username, "password": "ValidPass1!", "remember_me": str(persistent).lower()})
    assert first.status_code == 200
    result = client.post("/api/v1/auth/login/2fa", data={"code": pyotp.TOTP(secret).now()}, headers={"Authorization": "Bearer " + first.json()["access_token"]})
    assert result.status_code == 200, result.text
    assert_cookie_mode(result, persistent)
    refresh = client.post("/api/v1/auth/refresh", data={"refresh_token": result.json()["refresh_token"]})
    assert refresh.status_code == 200
    assert_cookie_mode(refresh, persistent)
