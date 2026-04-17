"""
Tests for authentication hardening features:
- Account lockout after 5 failed attempts
- Refresh token rotation (single-use tokens)
- Single-session enforcement
- 2FA (TOTP) completion flow
"""
import uuid

import pyotp
from datetime import datetime, timedelta

from backend.models.user import User


def _http_error_text(body: dict) -> str:
    """Support both legacy FastAPI `detail` and unified API error envelopes."""
    if "detail" in body:
        d = body["detail"]
        return d if isinstance(d, str) else str(d)
    err = body.get("error") or {}
    return (err.get("message") or "") + (err.get("details") or "")


def test_account_lockout(db_session, client, test_tenant):
    """Verify account locks after 5 failed login attempts and unlocks after expiry."""
    from backend.auth import get_password_hash

    # Clean slate
    db_session.query(User).filter(User.username == "lockout_user").delete()
    db_session.commit()

    user = User(
        username="lockout_user",
        email="lockout@example.com",
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
        hashed_password=get_password_hash("ValidPass1!"),
    )
    db_session.add(user)
    db_session.commit()

    # --- Phase 1: 5 wrong attempts should all return 401 ---
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "lockout_user", "password": "WrongPasswordX"},
        )
        assert resp.status_code == 401, f"Attempt {i+1}: expected 401, got {resp.status_code} — {resp.text[:200]}"

    # --- Phase 2: 6th attempt should be 403 (account locked) ---
    resp_locked = client.post(
        "/api/v1/auth/token",
        data={"username": "lockout_user", "password": "WrongPasswordX"},
    )
    assert resp_locked.status_code == 403, f"Expected 403 lockout, got {resp_locked.status_code} — {resp_locked.text[:200]}"

    # Verify lockout message is in Arabic
    body = resp_locked.json()
    assert "قفل الحساب" in _http_error_text(body)

    # --- Phase 3: Even correct password should be rejected during lockout ---
    resp_correct = client.post(
        "/api/v1/auth/token",
        data={"username": "lockout_user", "password": "ValidPass1!"},
    )
    assert resp_correct.status_code == 403

    # --- Phase 4: Simulate lockout expiry (set locked_until to the past) ---
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "lockout_user").first()
    user.account_locked_until = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    # Now login should succeed
    resp_success = client.post(
        "/api/v1/auth/token",
        data={"username": "lockout_user", "password": "ValidPass1!"},
    )
    assert resp_success.status_code == 200, f"Expected 200 after lockout expiry, got {resp_success.status_code} — {resp_success.text[:200]}"
    assert "access_token" in resp_success.json()


def test_refresh_token_rotation(db_session, client, test_tenant):
    """Verify old refresh tokens are invalidated after rotation."""
    from backend.auth import get_password_hash

    # Clean slate
    db_session.query(User).filter(User.username == "rotate_user").delete()
    db_session.commit()

    user = User(
        username="rotate_user",
        email="rotate@example.com",
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
        hashed_password=get_password_hash("ValidPass1!"),
    )
    db_session.add(user)
    db_session.commit()

    # Login to get initial tokens
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "rotate_user", "password": "ValidPass1!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text[:200]}"
    original_refresh = resp.json()["refresh_token"]

    # Use refresh token to get new tokens
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        data={"refresh_token": original_refresh},
    )
    assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text[:200]}"
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != original_refresh, "New refresh token should differ from old one"

    # Old refresh token should now be invalid
    fail_resp = client.post(
        "/api/v1/auth/refresh",
        data={"refresh_token": original_refresh},
    )
    assert fail_resp.status_code == 401, f"Old token should be rejected, got {fail_resp.status_code} — {fail_resp.text[:200]}"


def test_single_session_second_login_invalidates_first_token(
    db_session, client, test_tenant
):
    """After logging in again, the previous access token must be rejected."""
    from backend.auth import get_password_hash

    uname = f"session_user_{uuid.uuid4().hex[:8]}"
    db_session.query(User).filter(User.username == uname).delete()
    db_session.commit()

    user = User(
        username=uname,
        email=f"{uname}@example.com",
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
        hashed_password=get_password_hash("ValidPass1!"),
    )
    db_session.add(user)
    db_session.commit()

    r1 = client.post(
        "/api/v1/auth/token",
        data={"username": uname, "password": "ValidPass1!"},
    )
    assert r1.status_code == 200
    token1 = r1.json()["access_token"]

    me1 = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert me1.status_code == 200

    r2 = client.post(
        "/api/v1/auth/token",
        data={"username": uname, "password": "ValidPass1!"},
    )
    assert r2.status_code == 200
    token2 = r2.json()["access_token"]
    assert token2 != token1

    stale = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert stale.status_code == 401

    ok = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert ok.status_code == 200


def test_2fa_wrong_code_then_correct(db_session, client, test_tenant):
    """2FA user: wrong TOTP → 401; correct TOTP → 200 with full tokens."""
    from backend.auth import get_password_hash

    uname = f"twofa_{uuid.uuid4().hex[:8]}"
    otp_secret = "JBSWY3DPEHPK3PXP"

    db_session.query(User).filter(User.username == uname).delete()
    db_session.commit()

    user = User(
        username=uname,
        email=f"{uname}@example.com",
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
        is_2fa_enabled=True,
        otp_secret=otp_secret,
        hashed_password=get_password_hash("ValidPass1!"),
    )
    db_session.add(user)
    db_session.commit()

    step1 = client.post(
        "/api/v1/auth/token",
        data={"username": uname, "password": "ValidPass1!"},
    )
    assert step1.status_code == 200
    body = step1.json()
    assert body.get("user_status") == "2fa_required"
    temp = body["access_token"]
    assert body.get("refresh_token") in (None, "")

    bad = client.post(
        "/api/v1/auth/login/2fa",
        data={"code": "000000"},
        headers={"Authorization": f"Bearer {temp}"},
    )
    assert bad.status_code == 401

    code = pyotp.TOTP(otp_secret).now()
    good = client.post(
        "/api/v1/auth/login/2fa",
        data={"code": code},
        headers={"Authorization": f"Bearer {temp}"},
    )
    assert good.status_code == 200, good.text
    final = good.json()
    assert final.get("refresh_token")


def test_register_clinic_rejects_weak_password(client):
    """Clinic registration must apply the same password policy as other flows."""
    uid = uuid.uuid4().hex[:10]
    resp = client.post(
        "/api/v1/auth/register_clinic",
        data={
            "clinic_name": f"Clinic {uid}",
            "admin_username": f"adm_{uid}",
            "admin_email": f"{uid}@clinic.test",
            "admin_password": "short",
        },
    )
    assert resp.status_code == 400
