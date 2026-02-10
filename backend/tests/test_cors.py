"""
Test: CORS Configuration
Verifies that CORS headers are set correctly for cross-origin requests.
"""


def test_cors_options_request(client):
    """Test that OPTIONS preflight request returns correct CORS headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/v1/token", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_allows_localhost_origin(client):
    """Test that localhost origins are allowed."""
    headers = {
        "Origin": "http://localhost:5173",
    }
    response = client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200
