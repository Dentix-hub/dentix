import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from backend import auth, models
from backend.auth import get_password_hash


def _create_user(db_session, test_tenant, *, prefix: str):
    uid = uuid.uuid4().hex[:10]
    username = f"{prefix}_{uid}"
    password = "ValidPass9!Secure"
    user = models.User(
        username=username,
        email=f"{username}@example.com",
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, password


def test_logout_revokes_stolen_access_and_refresh_tokens(client, db_session, test_tenant):
    user, password = _create_user(db_session, test_tenant, prefix="logout_guard")

    login = client.post(
        "/api/v1/auth/token",
        data={"username": user.username, "password": password},
    )
    assert login.status_code == 200, login.text
    access_token = login.cookies.get("access_token")
    refresh_token = login.cookies.get("refresh_token")
    session_id = login.json()["session_id"]
    assert access_token
    assert refresh_token
    assert session_id

    before = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert before.status_code == 200

    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout.status_code == 200, logout.text

    stolen_access = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert stolen_access.status_code == 401

    stolen_refresh = client.post(
        "/api/v1/auth/refresh",
        data={"refresh_token": refresh_token},
    )
    assert stolen_refresh.status_code == 401

    db_session.expire_all()
    persisted_user = db_session.query(models.User).filter(models.User.id == user.id).one()
    assert persisted_user.active_session_id != session_id
    assert persisted_user.active_session_id.startswith("revoked_all_")
    assert (
        db_session.query(models.UserSession)
        .filter(
            models.UserSession.user_id == user.id,
            models.UserSession.is_active.is_(True),
        )
        .count()
        == 0
    )


def test_expired_access_token_is_rejected(client, test_user):
    expired = auth.create_access_token(
        data={
            "sub": test_user.username,
            "role": test_user.role,
            "tenant_id": test_user.tenant_id,
        },
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401


def test_password_reset_token_is_single_use_and_revokes_existing_session(
    client, db_session, test_tenant
):
    user, password = _create_user(db_session, test_tenant, prefix="reset_replay")

    login = client.post(
        "/api/v1/auth/token",
        data={"username": user.username, "password": password},
    )
    assert login.status_code == 200, login.text
    old_access = login.cookies.get("access_token")
    assert old_access

    raw_token = f"reset-{uuid.uuid4().hex}"
    reset_token = models.PasswordResetToken(
        token=hashlib.sha256(raw_token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).replace(
            tzinfo=None
        ),
        used=False,
    )
    db_session.add(reset_token)
    db_session.commit()

    payload = {
        "token": raw_token,
        "new_password": "CorrectHorseBatteryStaple9!",
    }
    first = client.post("/api/v1/auth/reset-password", json=payload)
    assert first.status_code == 200, first.text

    replay = client.post("/api/v1/auth/reset-password", json=payload)
    assert replay.status_code == 400

    stolen_access = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {old_access}"},
    )
    assert stolen_access.status_code == 401

    db_session.expire_all()
    persisted = (
        db_session.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.id == reset_token.id)
        .one()
    )
    assert persisted.used is True


def test_expired_password_reset_token_is_rejected_and_consumed(
    client, db_session, test_tenant
):
    user, _ = _create_user(db_session, test_tenant, prefix="reset_expired")
    raw_token = f"expired-{uuid.uuid4().hex}"
    reset_token = models.PasswordResetToken(
        token=hashlib.sha256(raw_token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).replace(
            tzinfo=None
        ),
        used=False,
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "CorrectHorseBatteryStaple9!",
        },
    )
    assert response.status_code == 400

    db_session.expire_all()
    persisted = (
        db_session.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.id == reset_token.id)
        .one()
    )
    assert persisted.used is True


def test_forgot_password_response_does_not_enumerate_accounts(
    client, db_session, test_tenant, monkeypatch
):
    user, _ = _create_user(db_session, test_tenant, prefix="reset_enum")

    import backend.routers.password_reset as password_reset_router

    monkeypatch.setattr(
        password_reset_router.firebase_client,
        "generate_password_reset_link",
        lambda _email: "https://example.invalid/reset",
    )
    monkeypatch.setattr(
        password_reset_router,
        "send_password_reset_email",
        lambda *_args, **_kwargs: True,
    )

    known = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": user.email},
    )
    unknown = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": f"missing-{uuid.uuid4().hex}@example.com"},
    )

    assert known.status_code == 200, known.text
    assert unknown.status_code == 200, unknown.text
    assert known.json().get("message") == unknown.json().get("message")
