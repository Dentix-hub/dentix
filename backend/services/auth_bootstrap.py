"""Audited identity-bootstrap lookups for authentication (HIGH-RLS-01).

FORCE RLS on ``users`` correctly hides every row from a session without a
tenant binding. That is the desired default — but three flows must resolve a
user row *before* any tenant can be bound:

1. Credential verification at login (no token exists yet).
2. Refresh-token exchange (the JWT is being re-established).
3. Super-admin / contextless requests resolving their own identity.

``lookup_user_for_authentication`` performs this narrow lookup on the isolated
system database connection, RE-BINDS the request session to the resolved
tenant, then audits the bootstrap lookup. Every later statement
— including login's writes to ``users`` — therefore runs with a real tenant
identity under FORCE RLS. It MUST NOT be used for general data access; regular
per-request reads stay fully tenant-scoped.

Super-admin identities carry no tenant; their bootstrap audit and the few
bookkeeping writes their login performs use narrow explicit bypass scopes.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..crud.auth import normalize_username
from ..utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic.auth")

# Reasons are fixed tokens so audit queries stay predictable.
REASON_LOGIN = "login_credential_lookup"
REASON_REFRESH = "refresh_token_exchange"
REASON_SESSION_RESOLVE = "session_identity_resolution"

SUPER_ADMIN_ROLE = "super_admin"


@asynccontextmanager
async def clinic_registration_scope(db: AsyncSession):
    """Yield the narrow database scope used to create a clinic's first user.

    PostgreSQL registration starts before a tenant identity exists, so its
    atomic tenant/admin bootstrap must use the isolated native-BYPASSRLS role.
    SQLite keeps the injected request session so unit-test transaction
    isolation and dependency overrides continue to work.
    """
    from backend.database import ASYNC_DATABASE_URL, system_session_scope

    if "postgresql" in ASYNC_DATABASE_URL:
        async with system_session_scope() as system_db:
            yield system_db
        return
    yield db


async def lookup_user_for_authentication(
    db: AsyncSession,
    username: str,
    reason: str,
) -> models.User | None:
    """Resolve one user row for credential/JWT verification."""
    from backend.database import system_session_scope

    async with system_session_scope() as system_db:
        result = await system_db.execute(_identity_stmt(username))
        system_user = result.scalars().first()
        user_id = system_user.id if system_user is not None else None
        tenant_id = system_user.tenant_id if system_user is not None else None

    if tenant_id is not None:
        _bind_tenant(db, tenant_id)
        # Re-read through the normal request session so the returned row is
        # attached to that tenant-scoped transaction for post-auth updates.
        result = await db.execute(_identity_stmt(username))
        user = result.scalars().first()
    else:
        # A contextless super-admin row cannot be loaded by the app role. It is
        # detached after the system lookup and is explicitly attached again
        # only inside post_auth_write_scope when a bookkeeping write is needed.
        user = system_user

    await _audit_bootstrap(
        user_id=user_id,
        tenant_id=tenant_id,
        username=username,
        reason=reason,
    )

    return user


def _bind_tenant(db: AsyncSession, tenant_id: int) -> None:
    """Bind both SQLAlchemy RLS state and request-local tenant state."""
    from backend.core.tenancy import set_current_tenant_id
    from backend.database import rebind_session_tenant

    rebind_session_tenant(db, tenant_id)
    set_current_tenant_id(tenant_id)


def _identity_stmt(username: str):
    # Keep the bootstrap path behavior-compatible with the pre-RLS auth lookup:
    # login identities are trimmed/normalized, username matching is
    # case-insensitive, and email remains a supported login identifier.
    clean_identity = normalize_username(username)
    return (
        select(models.User)
        .where(
            or_(
                func.lower(models.User.username) == clean_identity,
                func.lower(models.User.email) == clean_identity,
            )
        )
        # Login/refresh touch user.tenant right after resolution; eager
        # load so no lazy IO happens outside the bootstrap scope.
        .options(joinedload(models.User.tenant))
    )


async def _audit_bootstrap(
    *,
    user_id: int | None,
    tenant_id: int | None,
    username: str,
    reason: str,
) -> bool:
    """Persist one bootstrap audit entry without making auth depend on it."""

    async def _write(target_db: AsyncSession) -> None:
        log_admin_action(
            db=target_db,
            admin_user=None,
            action="auth_bootstrap",
            entity_type="user",
            entity_id=user_id,
            tenant_id=tenant_id,
            details=f"reason={reason} target_username={username} found={user_id is not None}",
        )
        await target_db.commit()

    try:
        from backend.database import system_session_scope

        # Keep audit failure/commit isolated from the request transaction so a
        # best-effort audit cannot expire or roll back the authenticated row.
        async with system_session_scope() as system_db:
            await _write(system_db)
        return True
    except Exception:
        # Auditing must never break authentication itself, but failures are
        # security-relevant and must be visible in logs.
        logger.exception("auth_bootstrap audit write failed")
        return False


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
        from backend.database import system_session_scope

        async with system_session_scope() as system_db:
            # The bootstrap row may still be associated with the short-lived
            # lookup session. ``merge`` copies it into this write session
            # without trying to attach one ORM instance to two sessions.
            scoped_user = await system_db.merge(user)
            yield system_db, scoped_user
        return
    yield db, user
