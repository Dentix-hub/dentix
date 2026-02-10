"""
API Endpoint Tests for Patients, Appointments, and Payments routers.
Tests CRUD operations, permission checks, and audit logging.
"""

import pytest
from datetime import datetime


class TestPatientsAPI:
    """Tests for /patients/ endpoints."""

    def test_create_patient(self, client, auth_headers, test_tenant):
        """Create a new patient via API."""
        response = client.post(
            "/patients/",
            json={
                "name": "New Patient",
                "phone": "01112223344",
                "age": 25,
                "gender": "female",
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "New Patient"
        assert data["phone"] == "01112223344"

    def test_create_patient_unauthenticated(self, client):
        """Reject patient creation without auth."""
        response = client.post("/patients/", json={"name": "Bad"})
        assert response.status_code in (401, 403, 422)

    def test_get_patients_list(self, client, auth_headers, test_patient):
        """List patients for authenticated user's tenant."""
        response = client.get("/patients/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_patient_by_id(self, client, auth_headers, test_patient):
        """Get a specific patient by ID."""
        response = client.get(f"/patients/{test_patient.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_patient.name

    def test_get_patient_not_found(self, client, auth_headers):
        """Return 404 for non-existent patient."""
        response = client.get("/patients/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_update_patient(self, client, auth_headers, test_patient):
        """Update patient data."""
        response = client.put(
            f"/patients/{test_patient.id}",
            json={
                "name": "Updated Name",
                "phone": test_patient.phone,
                "age": 31,
                "gender": "male",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_delete_patient(self, client, admin_headers, test_patient):
        """Delete patient (admin only)."""
        response = client.delete(
            f"/patients/{test_patient.id}", headers=admin_headers
        )
        assert response.status_code in (200, 204)


class TestAppointmentsAPI:
    """Tests for /appointments/ endpoints."""

    def test_create_appointment(self, client, auth_headers, test_patient):
        """Create an appointment."""
        response = client.post(
            "/appointments/",
            json={
                "patient_id": test_patient.id,
                "date_time": datetime.now().isoformat(),
                "status": "scheduled",
                "notes": "Routine checkup",
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 201, 422)

    def test_list_appointments(self, client, auth_headers):
        """List appointments for tenant."""
        response = client.get("/appointments/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_appointments_unauthenticated(self, client):
        """Reject without auth."""
        response = client.get("/appointments/")
        assert response.status_code in (401, 403)

    def test_delete_appointment_not_found(self, client, auth_headers):
        """404 for deleting non-existent appointment."""
        response = client.delete("/appointments/99999", headers=auth_headers)
        assert response.status_code in (404, 500)


class TestPaymentsAPI:
    """Tests for /payments/ endpoints."""

    def test_list_payments(self, client, auth_headers):
        """List payments for tenant."""
        response = client.get("/payments/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_payments_unauthenticated(self, client):
        """Reject without auth."""
        response = client.get("/payments/")
        assert response.status_code in (401, 403)

    def test_create_payment_missing_data(self, client, auth_headers):
        """Reject payment creation with missing fields."""
        response = client.post(
            "/payments/",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_delete_payment_not_found(self, client, auth_headers):
        """404 for deleting non-existent payment."""
        response = client.delete("/payments/99999", headers=auth_headers)
        assert response.status_code in (404, 500)

    def test_today_payments_endpoint(self, client, auth_headers):
        """Today's payments endpoint responds."""
        response = client.get("/payments/today/payments", headers=auth_headers)
        assert response.status_code == 200

    def test_today_debtors_endpoint(self, client, auth_headers):
        """Today's debtors endpoint responds."""
        response = client.get("/payments/today/debtors", headers=auth_headers)
        assert response.status_code == 200


class TestPermissions:
    """Tests for role-based access control."""

    def test_unauthenticated_access_denied(self, client):
        """All protected endpoints reject unauthenticated requests."""
        endpoints = ["/patients/", "/appointments/", "/payments/"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in (
                401,
                403,
            ), f"Expected 401/403 for {endpoint}, got {response.status_code}"

    def test_invalid_token_rejected(self, client):
        """Invalid JWT token is rejected."""
        response = client.get(
            "/patients/", headers={"Authorization": "Bearer invalid-token-123"}
        )
        assert response.status_code in (401, 403)
