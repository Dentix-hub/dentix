"""End-to-end cookie-only auth flow against a NOBYPASSRLS role (HIGH-RLS-01).

Runs the real application ASGI stack with the database role created by CI
(``dentix_ci_app``: NOSUPERUSER NOBYPASSRLS). Proves:

1. POST /auth/token issues cookies AND body tokens for native clients.
2. Login identity lookup remains case-insensitive after the RLS bootstrap.
3. A cookie-only GET /auth/session resolves the user (middleware binds the
   tenant from the signed cookie; FORCE RLS stays enforced).
4. POST /auth/refresh rotates tokens using the cookie path.

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


async def _seed() -> None:
    from backend import models
    from backend.auth import get_password_hash
    from backend.database import AsyncSessionLocal, RlsContext

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            existing = (
                await db.execute(
                    select(models.User).where(models.User.id == USER_ID)
                )
            ).scalars().first()
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


@pytest.mark.asyncio
async def test_login_cookie_session_refresh_under_nobypassrls():
    # Imported lazily so DATABASE_URL is already bound to the restricted role.
    import httpx

    from backend.main import app

    await _seed()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Regression guard: the stored username is mixed-case, while the login
        # request deliberately uses lowercase. PostgreSQL equality is
        # case-sensitive, so this proves the bootstrap query normalizes it.
        login_res = await client.post(
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
        # Web contract: httpOnly cookie issued and user payload returned.
        assert "access_token" in client.cookies
        assert body["user"]["tenant_id"] == str(TENANT_ID)

        # Cookie-only session resolution — no Authorization header sent.
        session_res = await client.get("/api/v1/auth/session")
        assert session_res.status_code == 200, session_res.text
        session_body = session_res.json()["data"]
        assert int(session_body["tenant_id"]) == TENANT_ID

        # Refresh via the httpOnly refresh cookie.
        refresh_res = await client.post("/api/v1/auth/refresh")
        assert refresh_res.status_code == 200, refresh_res.text
        refreshed = refresh_res.json()
        assert refreshed.get("access_token")
        assert refreshed.get("refresh_token")
