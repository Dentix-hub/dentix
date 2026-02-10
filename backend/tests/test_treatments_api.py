"""
API Endpoint Tests for Treatments.
Tests treatment creation, updates, and tooth status management.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend import schemas

class TestTreatmentsAPI:
    """Tests for /treatments/ endpoints."""

    @pytest.fixture
    def mock_inventory(self):
        """Mock inventory service to avoid excessive setup."""
        with patch("backend.routers.treatments.inventory_service") as mock:
            mock.validate_stock_availability.return_value = True
            mock.deduct_material_usage.return_value = True
            yield mock

    def test_create_treatment(self, client, auth_headers, test_patient, mock_inventory):
        """Create a new treatment."""
        payload = {
            "patient_id": test_patient.id,
            "procedure": "Amalgam Filling",
            "tooth_number": "16",
            "price": 150.0,
            "notes": "Deep cavity",
            "status": "completed"
        }
        response = client.post(
            "/treatments/",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["procedure"] == "Amalgam Filling"
        assert data["price"] == 150.0
        assert data["tooth_number"] == 16
        
        # Verify inventory was checked
        mock_inventory.validate_stock_availability.assert_called()

    def test_create_treatment_invalid_patient(self, client, auth_headers):
        """Reject treatment for non-existent patient."""
        payload = {
            "patient_id": 99999,
            "procedure": "Test",
            "price": 100
        }
        response = client.post("/treatments/", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_update_tooth_status(self, client, auth_headers, test_patient):
        """Update tooth status (Dental Chart)."""
        payload = {
            "patient_id": test_patient.id,
            "tooth_number": "21",
            "status": "missing",
            "notes": "Extracted years ago"
        }
        response = client.post(
            "/treatments/tooth-status",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tooth_number"] == 21
        assert data["status"] == "missing"

    def test_delete_treatment(self, client, admin_headers, test_patient, mock_inventory):
        """Delete treatment (admin only)."""
        # Create first
        payload = {
            "patient_id": test_patient.id,
            "procedure": "To Delete",
            "price": 50.0
        }
        create_resp = client.post("/treatments/", json=payload, headers=admin_headers)
        t_id = create_resp.json()["id"]

        response = client.delete(f"/treatments/{t_id}", headers=admin_headers)
        assert response.status_code in (200, 204)
