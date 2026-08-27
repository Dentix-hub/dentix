"""TenantMiddleware must bind tenant context from the signed access_token
cookie exactly like it does for Bearer tokens (HIGH-RLS-01)."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend import auth as backend_auth
from backend.core.tenancy import get_current_tenant_id, is_super_admin_bypass
from backend.middleware.tenant import (
    TenantMiddleware,
    _request_scope_from_signed_token,
    _tenant_id_from_signed_token,
)


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
    assert _request_scope_from_signed_token("not-a-jwt") == (None, False)


def test_super_admin_cookie_binds_nothing(super_admin_user):
    # Super-admin JWT carries no tenant_id but selects the isolated system
    # database pool before FastAPI resolves database dependencies.
    token = backend_auth.create_access_token(
        data={"sub": super_admin_user.username, "role": super_admin_user.role}
    )
    assert _tenant_id_from_signed_token(token) is None
    assert _request_scope_from_signed_token(token) == (None, True)


def test_super_admin_cookie_activates_bypass_before_endpoint(super_admin_user):
    app = FastAPI()
    app.add_middleware(TenantMiddleware)

    @app.get("/scope")
    async def read_scope():
        return JSONResponse(
            {
                "tenant_id": get_current_tenant_id(),
                "super_admin_bypass": is_super_admin_bypass(),
            }
        )

    token = backend_auth.create_access_token(
        data={"sub": super_admin_user.username, "role": super_admin_user.role}
    )
    with TestClient(app) as scope_client:
        response = scope_client.get("/scope", cookies={"access_token": token})

    assert response.status_code == 200
    assert response.json() == {"tenant_id": None, "super_admin_bypass": True}


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
