"""HIGH-RLS-01 verification under NOBYPASSRLS.

Invariants after the audited-bootstrap fix:

1. A raw contextless SELECT on ``users`` must stay DENIED — FORCE RLS is the
   active isolation layer, and no code path may read identities without it
   going through the audited bootstrap.
2. ``lookup_user_for_authentication`` resolves a seeded user from the same
   contextless session AND writes an audit entry describing the lookup.
3. The audited bootstrap preserves the legacy normalized login contract:
   username matching is case-insensitive and email is accepted as an identity.
"""

import pytest
from sqlalchemy import select

from backend import models
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.auth_bootstrap import (
    lookup_user_for_authentication,
    REASON_LOGIN,
)


PROBE_TENANT_ID = 993650
PROBE_USER_ID = 9936501
PROBE_USERNAME = "Pg_Rls_Bootstrap_Probe"
PROBE_EMAIL = "pg_rls_bootstrap_probe@example.com"


async def _seed_probe_fixtures() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            existing = (
                await db.execute(
                    select(models.User).where(models.User.id == PROBE_USER_ID)
                )
            ).scalars().first()
            if existing is not None:
                return
            db.add_all(
                [
                    models.Tenant(
                        id=PROBE_TENANT_ID,
                        name="RLS Bootstrap Probe",
                        timezone="Africa/Cairo",
                    ),
                    models.User(
                        id=PROBE_USER_ID,
                        username=PROBE_USERNAME,
                        email=PROBE_EMAIL,
                        hashed_password="h",
                        role="admin",
                        tenant_id=PROBE_TENANT_ID,
                        is_active=True,
                    ),
                ]
            )
            await db.commit()


@pytest.mark.asyncio
async def test_contextless_identity_read_stays_denied():
    """The direct SELECT that used to break login must STAY invisible."""
    await _seed_probe_fixtures()

    # Exactly the condition a cookie-only request produces: no tenant bound.
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        result = await session.execute(
            select(models.User).where(models.User.username == PROBE_USERNAME)
        )
        user = result.scalars().first()

    assert user is None, (
        "A contextless identity read returned a row — FORCE RLS is no longer "
        "enforced; investigate before trusting tenant isolation."
    )


@pytest.mark.asyncio
async def test_audited_bootstrap_resolves_identity_and_writes_audit():
    """Authentication bootstrap finds the user through the audited path."""
    await _seed_probe_fixtures()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        user = await lookup_user_for_authentication(
            session, PROBE_USERNAME, reason=REASON_LOGIN
        )
        assert user is not None
        assert user.tenant_id == PROBE_TENANT_ID

        # Audit rows are tenant-scoped too; verifying them requires the
        # explicit maintenance scope.
        async with session.bypass_rls() as boot:
            audits = (
                (
                    await boot.execute(
                        select(models.AuditLog)
                        .where(models.AuditLog.action == "auth_bootstrap")
                        .order_by(models.AuditLog.id.desc())
                    )
                )
                .scalars()
                .all()
            )
        assert audits, "auth_bootstrap lookup was not audited"
        latest = audits[0]
        assert PROBE_USERNAME in (latest.details or "")
        assert "found=True" in (latest.details or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity",
    [PROBE_USERNAME.lower(), PROBE_USERNAME.upper(), PROBE_EMAIL.upper()],
)
async def test_audited_bootstrap_normalizes_login_identity(identity: str):
    """Case variants and email must resolve without weakening FORCE RLS."""
    await _seed_probe_fixtures()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        user = await lookup_user_for_authentication(
            session, identity, reason=REASON_LOGIN
        )
        assert user is not None
        assert user.id == PROBE_USER_ID
        assert user.username == PROBE_USERNAME
        assert user.tenant_id == PROBE_TENANT_ID