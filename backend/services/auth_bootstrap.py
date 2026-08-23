"""Audited identity-bootstrap lookups for authentication (HIGH-RLS-01).

FORCE RLS on ``users`` correctly hides every row from a session without a
tenant binding. That is the desired default — but three flows must resolve a
user row *before* any tenant can be bound:

1. Credential verification at login (no token exists yet).
2. Refresh-token exchange (the JWT is being re-established).
3. Super-admin / contextless requests resolving their own identity.

``lookup_user_for_authentication`` performs this narrow lookup inside an
explicit, short-lived ``bypass_rls()`` scope, audits it, then RE-BINDS the
request session to the resolved tenant so every later statement — including
login's writes to ``users`` — runs with a real tenant identity under FORCE
RLS. It MUST NOT be used for general data access; regular per-request reads
stay fully tenant-scoped.

Super-admin identities carry no tenant; the few bookkeeping writes their
login performs run through ``post_auth_write_scope``, which uses an explicit
bypass scope only for those statements.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic.auth")

# Reasons are fixed tokens so audit queries stay predictable.
REASON_LOGIN = "login_credential_lookup"
REASON_REFRESH = "refresh_token_exchange"
REASON_SESSION_RESOLVE = "session_identity_resolution"

SUPER_ADMIN_ROLE = "super_admin"


async def lookup_user_for_authentication(
    db: AsyncSession,
    username: str,
    reason: str,
) -> models.User | None:
    """Resolve one user row for credential/JWT verification."""
    if hasattr(db, "bypass_rls"):
        # Real request path: CustomAsyncRlsSession with explicit bypass scope.
        async with db.bypass_rls():
            result = await db.execute(_identity_stmt(username))
            user = result.scalars().first()
        await _audit_bootstrap(db, user, username, reason)
    else:
        # Plain AsyncSession (SQLite test overrides): there is no RLS layer to
        # bypass; run directly so behavior matches legacy lookups.
        result = await db.execute(_identity_stmt(username))
        user = result.scalars().first()

    if user is not None and user.tenant_id is not None:
        from backend.core.tenancy import set_current_tenant_id
        from backend.database import rebind_session_tenant

        rebind_session_tenant(db, user.tenant_id)
        set_current_tenant_id(user.tenant_id)

    return user


def _identity_stmt(username: str):
    return (
        select(models.User)
        .where(models.User.username == username)
        # Login/refresh touch user.tenant right after resolution; eager
        # load so no lazy IO happens outside the bootstrap scope.
        .options(joinedload(models.User.tenant))
    )


async def _audit_bootstrap(
    db: AsyncSession, user, username: str, reason: str
) -> None:
    """Persist the audit entry for one bootstrap lookup (best-effort)."""
    try:
        log_admin_action(
            db=db,
            admin_user=None,
            action="auth_bootstrap",
            entity_type="user",
            entity_id=user.id if user else None,
            tenant_id=getattr(user, "tenant_id", None),
            details=f"reason={reason} target_username={username} found={user is not None}",
        )
        await db.commit()
    except Exception:
        # Auditing must never break authentication itself, but failures are
        # security-relevant and must be visible in logs.
        logger.exception("auth_bootstrap audit write failed")
        await db.rollback()


@asynccontextmanager
async def post_auth_write_scope(db: AsyncSession, user: models.User | None):
    """Scope for post-authentication writes to the ``users`` row.

    - Staff identity: the session was already re-bound to its tenant by the
      bootstrap lookup, so writes run normally under FORCE RLS.
    - Super-admin identity (no tenant exists): the write runs inside an
      explicit bypass scope — the same audited escape hatch used for
      maintenance operations — because no tenant can ever satisfy the policy.
    """
    if user is not None and getattr(user, "role", "") == SUPER_ADMIN_ROLE:
        if hasattr(db, "bypass_rls"):
            async with db.bypass_rls() as scoped:
                yield scoped
            return
        # Plain session (no RLS capability): yield as-is.
    yield db
