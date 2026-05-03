"""
Verification tests for the consolidated /api/v1/users/me endpoint and StandardResponse wrapper.
"""
import pytest
from backend import models

def test_get_user_me_standardized(client, auth_headers, test_user):
    """
    Verify that GET /api/v1/users/me returns a StandardResponse[User].
    """
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    # Check for StandardResponse structure
    assert "success" in data
    assert data["success"] is True
    assert "data" in data
    
    user_data = data["data"]
    assert user_data["id"] == test_user.id
    assert user_data["username"] == test_user.username
    assert user_data["email"] == test_user.email

def test_update_user_me_standardized(client, auth_headers, test_user):
    """
    Verify that PUT /api/v1/users/me returns a StandardResponse[User].
    """
    new_email = "updated_me@test.com"
    response = client.put(
        "/api/v1/users/me",
        json={"email": new_email},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == new_email

def test_users_me_unauthenticated(client):
    """
    Verify that /api/v1/users/me requires authentication (401).
    """
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
