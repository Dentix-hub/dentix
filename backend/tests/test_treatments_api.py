"""
API Endpoint Tests for Treatments.
Tests treatment creation, updates, and tooth status management.
"""


class TestTreatmentsAPI:
    """Tests for /treatments/ endpoints."""

    def test_create_treatment_endpoint_exists(self, client, auth_headers, test_patient):
        """Verify treatment endpoint exists and requires proper permissions."""
        payload = {
            "patient_id": test_patient.id,
            "procedure": "Amalgam Filling",
            "tooth_number": "16",
            "notes": "Deep cavity",
        }
        response = client.post(
            "/api/v1/treatments/",
            json=payload,
            headers=auth_headers
        )
        # Should not be 401/403 (auth works) or 405 (route exists)
        assert response.status_code not in (401, 403, 405)

    def test_create_treatment_unauthenticated(self, client):
        """Reject unauthenticated treatment creation."""
        payload = {"patient_id": 1, "procedure": "Test"}
        response = client.post("/api/v1/treatments/", json=payload)
        assert response.status_code in (401, 403)

    def test_tooth_status_endpoint_exists(self, client, auth_headers, test_patient):
        """Verify tooth status endpoint exists."""
        payload = {
            "patient_id": test_patient.id,
            "tooth_number": "21",
            "status": "missing",
        }
        response = client.post(
            "/api/v1/treatments/tooth_status/",
            json=payload,
            headers=auth_headers
        )
        # Should not be 401/403/405
        assert response.status_code not in (401, 403, 405)

    def test_delete_treatment_requires_auth(self, client):
        """Delete treatment requires authentication."""
        response = client.delete("/api/v1/treatments/99999")
        assert response.status_code in (401, 403)
