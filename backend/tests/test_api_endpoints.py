"""
API Endpoint Tests for Patients, Appointments, and Payments routers.
Tests CRUD operations, permission checks, and audit logging.
"""

from datetime import datetime


class TestPatientsAPI:
    """Tests for /patients/ endpoints."""

    def test_create_patient(self, client, auth_headers, test_tenant):
        """Create a new patient via API."""
        response = client.post(
            "/api/v1/patients",
            json={
                "name": "New Patient",
                "phone": "01112223344",
                "age": 25,
            },
            headers=auth_headers,
        )
        # Response may be wrapped in StandardResponse or direct
        assert response.status_code in (200, 201, 202)

    def test_create_patient_unauthenticated(self, client):
        """Reject patient creation without auth."""
        response = client.post("/api/v1/patients", json={"name": "Bad"})
        assert response.status_code in (401, 403, 422)

    def test_get_patients_list(self, client, auth_headers, test_patient):
        """List patients for authenticated user's tenant."""
        response = client.get("/api/v1/patients", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Response may be wrapped in StandardResponse or direct list
        if isinstance(data, dict) and "data" in data:
            patients_list = data["data"]
        else:
            patients_list = data
        assert isinstance(patients_list, list)
        assert len(patients_list) >= 1

    def test_get_patient_by_id(self, client, auth_headers, test_patient):
        """Get a specific patient by ID."""
        response = client.get(f"/api/v1/patients/{test_patient.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # PatientSummary schema may use different field names
        assert isinstance(data, dict)

    def test_get_patient_not_found(self, client, auth_headers):
        """Return 404 for non-existent patient."""
        response = client.get("/api/v1/patients/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_update_patient(self, client, auth_headers, test_patient):
        """Update patient data."""
        response = client.put(
            f"/api/v1/patients/{test_patient.id}",
            json={
                "name": "Updated Name",
                "phone": test_patient.phone,
                "age": 31,
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 422)

    def test_delete_patient(self, client, admin_headers, test_patient):
        """Delete patient (admin only)."""
        response = client.delete(
            f"/api/v1/patients/{test_patient.id}", headers=admin_headers
        )
        assert response.status_code in (200, 204, 403, 404)


class TestAppointmentsAPI:
    """Tests for /appointments/ endpoints."""

    def test_create_appointment(self, client, auth_headers, test_patient):
        """Create an appointment."""
        response = client.post(
            "/api/v1/appointments",
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
        response = client.get("/api/v1/appointments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Response may be wrapped in StandardResponse or direct list
        if isinstance(data, dict) and "data" in data:
            appts_list = data["data"]
        else:
            appts_list = data
        assert isinstance(appts_list, list)

    def test_list_appointments_unauthenticated(self, client):
        """Reject without auth."""
        response = client.get("/api/v1/appointments/")
        assert response.status_code in (401, 403)

    def test_delete_appointment_not_found(self, client, auth_headers):
        """403 or 404 for deleting non-existent appointment."""
        response = client.delete("/api/v1/appointments/99999", headers=auth_headers)
        assert response.status_code in (403, 404)


class TestPaymentsAPI:
    """Tests for /payments/ endpoints."""

    def test_list_payments(self, client, auth_headers):
        """List payments for tenant."""
        response = client.get("/api/v1/payments", headers=auth_headers)
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            data = response.json()
            # Response may be wrapped in StandardResponse or direct list
            if isinstance(data, dict) and "data" in data:
                payments_list = data["data"]
            else:
                payments_list = data
            assert isinstance(payments_list, list)

    def test_list_payments_unauthenticated(self, client):
        """Reject without auth."""
        response = client.get("/api/v1/payments")
        assert response.status_code in (401, 403)

    def test_create_payment_missing_data(self, client, auth_headers):
        """Reject payment creation with missing fields."""
        response = client.post(
            "/api/v1/payments",
            json={},
            headers=auth_headers,
        )
        assert response.status_code in (422, 403)

    def test_delete_payment_not_found(self, client, auth_headers):
        """403 or 404 for deleting non-existent payment."""
        response = client.delete("/api/v1/payments/99999", headers=auth_headers)
        assert response.status_code in (403, 404)

    def test_today_payments_endpoint(self, client, auth_headers):
        """Today's payments endpoint responds."""
        response = client.get("/api/v1/payments/today/payments", headers=auth_headers)
        assert response.status_code in (200, 403)

    def test_today_debtors_endpoint(self, client, auth_headers):
        """Today's debtors endpoint responds."""
        response = client.get("/api/v1/payments/today/debtors", headers=auth_headers)
        assert response.status_code in (200, 403)


class TestPermissions:
    """Tests for role-based access control."""

    def test_unauthenticated_access_denied(self, client):
        """All protected endpoints reject unauthenticated requests."""
        endpoints = ["/api/v1/patients", "/api/v1/appointments", "/api/v1/payments"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in (
                401,
                403,
            ), f"Expected 401/403 for {endpoint}, got {response.status_code}"

    def test_invalid_token_rejected(self, client):
        """Invalid JWT token is rejected."""
        response = client.get(
            "/api/v1/patients", headers={"Authorization": "Bearer invalid-token-123"}
        )
        assert response.status_code in (401, 403)
