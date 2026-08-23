"""TenantMiddleware must bind tenant context from the signed access_token
cookie exactly like it does for Bearer tokens (HIGH-RLS-01)."""

import pytest

from backend import auth as backend_auth
from backend.middleware.tenant import _tenant_id_from_signed_token


def _token_for(user):
    # No "sid" claim: matches how conftest issues tokens for users whose
    # active_session_id is unset.
    return backend_auth.create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
        }
    )


def test_signed_cookie_yields_tenant_id(test_tenant, test_user):
    token = _token_for(test_user)
    assert _tenant_id_from_signed_token(token) == test_tenant.id


def test_garbage_or_tampered_token_yields_none():
    assert _tenant_id_from_signed_token("not-a-jwt") is None
    assert _tenant_id_from_signed_token("a.b.c") is None


def test_super_admin_cookie_binds_nothing(super_admin_user):
    # Super-admin JWT carries no tenant_id; context stays empty and the
    # audited bootstrap path resolves identity instead.
    token = backend_auth.create_access_token(
        data={"sub": super_admin_user.username, "role": super_admin_user.role}
    )
    assert _tenant_id_from_signed_token(token) is None


def test_cookie_only_session_resolves_current_user(
    client, db_session, admin_user
):
    """End-to-end: /auth/session with ONLY the httpOnly cookie set."""
    token = _token_for(admin_user)

    response = client.get(
        "/api/v1/auth/session",
        cookies={"access_token": token},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == admin_user.id
    assert data["tenant_id"] == admin_user.tenant_id


def test_invalid_cookie_is_rejected(client):
    response = client.get(
        "/api/v1/auth/session",
        cookies={"access_token": "forged-value"},
    )
    assert response.status_code == 401
