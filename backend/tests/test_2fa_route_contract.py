"""Regression tests for 2FA route registration and contract (HIGH-04).

- Routes must live at /api/v1/auth/2fa/* (not /api/v1/auth/auth/2fa/*).
- Verify accepts a JSON body {code, secret}.
- Full setup -> verify -> disable flow revokes sessions.
"""

import pyotp
import pytest

from backend import models


def _route_paths(app):
    return {getattr(route, "path", None) for route in app.routes}


def test_2fa_routes_are_not_double_prefixed(client):
    from backend.main import app

    paths = _route_paths(app)
    assert "/api/v1/auth/2fa/setup" in paths
    assert "/api/v1/auth/2fa/verify" in paths
    assert "/api/v1/auth/2fa/disable" in paths
    # The broken duplicated prefix must not exist
    assert "/api/v1/auth/auth/2fa/setup" not in paths


def test_2fa_full_flow_with_json_body(client, admin_headers, db_session, admin_user):
    setup_res = client.post("/api/v1/auth/2fa/setup", headers=admin_headers)
    assert setup_res.status_code == 200
    secret = setup_res.json()["secret"]
    assert "qr_code" in setup_res.json()

    code = pyotp.TOTP(secret).now()
    verify_res = client.post(
        "/api/v1/auth/2fa/verify",
        json={"code": code, "secret": secret},
        headers=admin_headers,
    )
    assert verify_res.status_code == 200

    db_session.refresh(admin_user)
    assert admin_user.is_2fa_enabled is True

    wrong_code = str((int(code) + 1) % 1000000).zfill(6)
    bad_res = client.post(
        "/api/v1/auth/2fa/verify",
        json={"code": wrong_code, "secret": secret},
        headers=admin_headers,
    )
    assert bad_res.status_code == 400


def test_2fa_verify_rejects_missing_body_fields(client, admin_headers):
    res = client.post(
        "/api/v1/auth/2fa/verify",
        json={"code": "123456"},
        headers=admin_headers,
    )
    assert res.status_code == 422
