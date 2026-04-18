"""
Test: Full Authentication Flow
Login → Token → Refresh → Protected Route → Invalid Refresh
"""

import pytest


def test_auth_login_and_access(client, super_admin_user, super_admin_headers):
    """Test login returns valid tokens and protected route works."""
    # 1. Login
    login_payload = {"username": "superadmin", "password": "superpass123"}
    response = client.post("/api/v1/auth/token", data=login_payload)
    assert response.status_code == 200, f"Login failed: {response.text}"

    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 2. Access Protected Route with returned token
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["data"]["username"] == "superadmin"


@pytest.mark.skip(reason="Refresh endpoint requires UserSession tracking (request.client.host unavailable in TestClient)")
def test_auth_refresh_token(client, super_admin_user):
    """Test token refresh flow."""
    # 1. Login first
    login_payload = {"username": "superadmin", "password": "superpass123"}
    response = client.post("/api/v1/auth/token", data=login_payload)
    assert response.status_code == 200
    refresh_token = response.json()["refresh_token"]

    # 2. Refresh Token
    refresh_payload = {"refresh_token": refresh_token}
    response = client.post("/api/v1/refresh", data=refresh_payload)
    assert response.status_code == 200

    new_tokens = response.json()
    assert "access_token" in new_tokens

    # 3. Verify new access token works
    new_access_token = new_tokens["access_token"]
    headers = {"Authorization": f"Bearer {new_access_token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200


def test_auth_invalid_refresh_token(client, super_admin_user):
    """Test that invalid refresh token is rejected."""
    response = client.post(
        "/api/v1/refresh", data={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401


def test_auth_invalid_credentials(client):
    """Test login with wrong credentials fails."""
    login_payload = {"username": "nonexistent", "password": "wrongpass"}
    response = client.post("/api/v1/auth/token", data=login_payload)
    assert response.status_code == 401
