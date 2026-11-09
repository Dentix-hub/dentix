"""End-to-end cookie-only auth flow against a NOBYPASSRLS role (HIGH-RLS-01).

Runs the real application ASGI stack with the database role created by CI
(``dentix_ci_app``: NOSUPERUSER NOBYPASSRLS). Proves:

1. POST /auth/token issues cookies AND body tokens for native clients.
2. Login identity lookup remains case-insensitive after the RLS bootstrap.
3. A cookie-only GET /auth/session resolves the user (middleware binds the
   tenant from the signed cookie; FORCE RLS stays enforced).
4. POST /auth/refresh rotates tokens using the cookie path.
5. Independent browser/device sessions survive another login for the same user.

This file executes only in CI steps whose DATABASE_URL points at the
restricted PostgreSQL role; it skips everywhere else.
"""

import os

import pytest
from sqlalchemy import select

_DATABASE_URL = os.getenv("DATABASE_URL", "")
pytestmark = [
    pytest.mark.skipif(
        not _DATABASE_URL.startswith(("postgresql://", "postgres://")),
        reason="Requires the restricted PostgreSQL CI role",
    ),
    pytest.mark.asyncio,
]

TENANT_ID = 993700
USER_ID = 9937001
USERNAME = "Pg_Cookie_Flow_Admin"
PASSWORD = "cookie-flow-pass-123"
SUPER_ADMIN_ID = 9937002
SUPER_ADMIN_USERNAME = "Pg_Super_Admin_Login"
SUPER_ADMIN_PASSWORD = "super-admin-flow-pass-123"


async def _seed() -> None:
    from backend import models
    from backend.auth import get_password_hash
    from backend.database import AsyncSessionLocal, RlsContext

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            existing = (
                (await db.execute(select(models.User).where(models.User.id == USER_ID)))
                .scalars()
                .first()
            )
            if existing is not None:
                return
            db.add_all(
                [
                    models.Tenant(
                        id=TENANT_ID,
                        name="Cookie Flow Probe",
                        timezone="Africa/Cairo",
                    ),
                    models.User(
                        id=USER_ID,
                        username=USERNAME,
                        email=f"{USERNAME.lower()}@example.com",
                        hashed_password=get_password_hash(PASSWORD),
                        role="admin",
                        tenant_id=TENANT_ID,
                        is_active=True,
                    ),
                ]
            )
            await db.commit()


async def _seed_super_admin() -> None:
    from backend import models
    from backend.auth import get_password_hash
    from backend.database import AsyncSessionLocal, RlsContext

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            existing = (
                (
                    await db.execute(
                        select(models.User).where(models.User.id == SUPER_ADMIN_ID)
                    )
                )
                .scalars()
                .first()
            )
            if existing is not None:
                return
            db.add(
                models.User(
                    id=SUPER_ADMIN_ID,
                    username=SUPER_ADMIN_USERNAME,
                    email=f"{SUPER_ADMIN_USERNAME.lower()}@example.com",
                    hashed_password=get_password_hash(SUPER_ADMIN_PASSWORD),
                    role="super_admin",
                    tenant_id=None,
                    is_active=True,
                )
            )
            await db.commit()


@pytest.mark.asyncio
async def test_login_cookie_session_refresh_under_nobypassrls():
    # Imported lazily so DATABASE_URL is already bound to the restricted role.
    import httpx

    from backend.main import app

    await _seed()

    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://test") as client_a,
        httpx.AsyncClient(transport=transport, base_url="http://test") as client_b,
    ):
        # Regression guard: the stored username is mixed-case, while the login
        # request deliberately uses lowercase. PostgreSQL equality is
        # case-sensitive, so this proves the bootstrap query normalizes it.
        login_res = await client_a.post(
            "/api/v1/auth/token",
            data={"username": USERNAME.lower(), "password": PASSWORD},
        )
        assert login_res.status_code == 200, login_res.text

        body = login_res.json()
        # Mobile Bearer contract: tokens present in the body.
        assert body.get("access_token")
        assert body.get("refresh_token")
        assert body.get("role") == "admin"
        # Return the canonical stored username, not the casing used to login.
        assert body.get("username") == USERNAME
        # Web contract: httpOnly auth cookies + readable PWA hint are issued.
        assert "access_token" in client_a.cookies
        assert "refresh_token" in client_a.cookies
        assert client_a.cookies.get("dentix_session_hint") == "1"
        assert body["user"]["tenant_id"] == str(TENANT_ID)

        # Cookie-only session resolution — no Authorization header sent.
        session_res = await client_a.get("/api/v1/auth/session")
        assert session_res.status_code == 200, session_res.text
        session_body = session_res.json()["data"]
        assert int(session_body["tenant_id"]) == TENANT_ID

        # A second device may authenticate the same account without evicting A.
        second_login = await client_b.post(
            "/api/v1/auth/token",
            data={"username": USERNAME, "password": PASSWORD},
        )
        assert second_login.status_code == 200, second_login.text
        assert second_login.json()["session_id"] != body["session_id"]
        assert client_b.cookies.get("dentix_session_hint") == "1"

        session_a_after_b = await client_a.get("/api/v1/auth/session")
        assert session_a_after_b.status_code == 200, session_a_after_b.text
        session_b = await client_b.get("/api/v1/auth/session")
        assert session_b.status_code == 200, session_b.text

        # Refresh device A via its own httpOnly refresh cookie. Device B remains valid.
        refresh_res = await client_a.post("/api/v1/auth/refresh")
        assert refresh_res.status_code == 200, refresh_res.text
        refreshed = refresh_res.json()
        assert refreshed.get("access_token")
        assert refreshed.get("refresh_token")
        assert refreshed["session_id"] == body["session_id"]
        assert client_a.cookies.get("dentix_session_hint") == "1"

        session_b_after_a_refresh = await client_b.get("/api/v1/auth/session")
        assert session_b_after_a_refresh.status_code == 200, (
            session_b_after_a_refresh.text
        )


@pytest.mark.asyncio
async def test_super_admin_login_transfers_bootstrap_row_to_system_write_scope():
    """A contextless super-admin row must not be attached to two sessions."""
    import httpx

    from backend.main import app

    await _seed_super_admin()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/token",
            data={
                "username": SUPER_ADMIN_USERNAME,
                "password": SUPER_ADMIN_PASSWORD,
            },
        )

        assert login_res.status_code == 200, login_res.text
        body = login_res.json()
        assert body["role"] == "super_admin"
        assert body["user"]["tenant_id"] is None
        assert body["session_id"]


@pytest.mark.parametrize("remember_me", ["true", "false"])
async def test_session_cookie_mode_survives_rotation_under_rls(remember_me):
    import httpx
    from backend.main import app

    await _seed()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/token", data={"username": USERNAME, "password": PASSWORD, "remember_me": remember_me})
        assert login.status_code == 200, login.text
        for response in (login, await client.post("/api/v1/auth/refresh")):
            assert response.status_code == 200, response.text
            for name in ("access_token", "refresh_token", "dentix_session_hint", "csrf_token"):
                cookie = next(c for c in response.headers.get_list("set-cookie") if c.startswith(name + "="))
                assert ("Max-Age=" in cookie) == (remember_me == "true")


@pytest.mark.parametrize("remember_me", ["true", "false"])
@pytest.mark.parametrize("otp_timestamp", [1_800_000_029, 1_800_000_030])
async def test_2fa_login_and_rotation_under_force_rls(remember_me, otp_timestamp, monkeypatch):
    from datetime import datetime
    from types import SimpleNamespace

    import httpx
    import pyotp
    from backend import models
    from backend.database import AsyncSessionLocal, RlsContext
    from backend.main import app
    from backend.services.auth_service import AuthService

    class OtpDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(otp_timestamp, tz)

    # Pin only PyOTP's clock on either side of a 30-second boundary. Keep
    # generation/verification real and leave JWT expiry and database time alone.
    monkeypatch.setattr(pyotp.totp, "datetime", SimpleNamespace(datetime=OtpDatetime))

    await _seed()
    secret = "JBSWY3DPEHPK3PXP"
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            user = (await db.execute(select(models.User).where(models.User.id == USER_ID))).scalar_one()
            user.is_2fa_enabled = True
            user.otp_secret = secret
            await db.commit()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/api/v1/auth/token", data={"username": USERNAME, "password": PASSWORD, "remember_me": remember_me})
            assert first.status_code == 200 and first.json()["user_status"] == "2fa_required"
            assert not client.cookies.get("access_token")
            pending_access = await client.get("/api/v1/auth/session", headers={"Authorization": "Bearer " + first.json()["access_token"]})
            assert pending_access.status_code == 401
            totp = pyotp.TOTP(secret)
            code = totp.now()
            expired_code = totp.at(otp_timestamp - totp.interval)
            wrong_code = f"{(int(code) + 1) % 1_000_000:06d}"
            for rejected_code in (expired_code, wrong_code):
                rejected = await client.post(
                    "/api/v1/auth/login/2fa", data={"code": rejected_code},
                    headers={"Authorization": "Bearer " + first.json()["access_token"]},
                )
                assert rejected.status_code == 401, rejected.text
                assert not client.cookies.get("access_token")
                assert not client.cookies.get("refresh_token")
            second = await client.post("/api/v1/auth/login/2fa", data={"code": code}, headers={"Authorization": "Bearer " + first.json()["access_token"]})
            assert second.status_code == 200, second.text
            rotated = await client.post("/api/v1/auth/refresh")
            assert rotated.status_code == 200, rotated.text
            for response in (second, rotated):
                for name in ("access_token", "refresh_token", "dentix_session_hint", "csrf_token"):
                    cookie = next(c for c in response.headers.get_list("set-cookie") if c.startswith(name + "="))
                    assert ("Max-Age=" in cookie) == (remember_me == "true")
            async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
                async with session.bypass_rls() as db:
                    stored = await AuthService.get_session_by_token(db, rotated.json()["refresh_token"])
                    assert stored.remember_me == (remember_me == "true")
    finally:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
            async with session.bypass_rls() as db:
                user = (await db.execute(select(models.User).where(models.User.id == USER_ID))).scalar_one()
                user.is_2fa_enabled = False
                user.otp_secret = None
                await db.commit()
