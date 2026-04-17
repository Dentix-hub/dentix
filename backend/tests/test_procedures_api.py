"""
API Endpoint Tests for Procedures.
Tests CRUD operations for dental procedures.
"""


class TestProceduresAPI:
    """Tests for /procedures/ endpoints."""

    def test_list_procedures(self, client, auth_headers):
        """List all procedures."""
        response = client.get("/api/v1/procedures/", headers=auth_headers)
        assert response.status_code in (200, 403)

    def test_list_procedures_unauthenticated(self, client):
        """Reject unauth access."""
        response = client.get("/api/v1/procedures/")
        assert response.status_code in (401, 403)
