"""
API Endpoint Tests for Procedures.
Tests CRUD operations for dental procedures.
"""

import pytest
from backend import schemas

class TestProceduresAPI:
    """Tests for /procedures/ endpoints."""

    def test_create_procedure(self, client, auth_headers):
        """Create a new procedure."""
        payload = {
            "name": "Root Canal",
            "base_cost": 500.0,
            "category": "Endodontics",
            "description": "Standard root canal treatment",
            "insurance_code": "RC-101"
        }
        response = client.post(
            "/procedures/",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "Root Canal"
        assert data["base_cost"] == 500.0
        return data["id"]

    def test_create_procedure_unauthorized(self, client):
        """Reject unauth creation."""
        response = client.post("/procedures/", json={"name": "Fail"})
        assert response.status_code in (401, 403)

    def test_list_procedures(self, client, auth_headers):
        """List all procedures."""
        # Ensure at least one exists
        self.test_create_procedure(client, auth_headers)
        
        response = client.get("/procedures/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_procedure_by_id(self, client, auth_headers):
        """Get specific procedure."""
        proc_id = self.test_create_procedure(client, auth_headers)
        
        response = client.get(f"/procedures/{proc_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == proc_id

    def test_update_procedure(self, client, auth_headers):
        """Update procedure details."""
        proc_id = self.test_create_procedure(client, auth_headers)
        
        response = client.put(
            f"/procedures/{proc_id}",
            json={
                "name": "Updated Root Canal",
                "base_cost": 600.0,
                "category": "Endodontics"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Root Canal"
        assert data["base_cost"] == 600.0

    def test_delete_procedure(self, client, admin_headers):
        """Delete procedure (admin only)."""
        # Create as admin to ensure we have ID
        payload = {
            "name": "To Delete",
            "base_cost": 100.0,
            "category": "Temp"
        }
        create_resp = client.post("/procedures/", json=payload, headers=admin_headers)
        proc_id = create_resp.json()["id"]

        response = client.delete(f"/procedures/{proc_id}", headers=admin_headers)
        assert response.status_code in (200, 204)
        
        # Verify gone
        get_resp = client.get(f"/procedures/{proc_id}", headers=admin_headers)
        assert get_resp.status_code == 404
