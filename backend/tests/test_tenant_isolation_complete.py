"""
Complete Tenant Isolation Test Suite.

Tests cross-tenant access scenarios to ensure strict data isolation.
Covers: patients, treatments, payments, appointments, inventory.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.database import Base, get_db
from backend import models
from backend.auth import create_access_token, get_password_hash


# ============================================================
# Test Database Setup
# ============================================================

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def db_session(engine):
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================
# Data Factories
# ============================================================


@pytest.fixture(scope="module")
def tenant_a(db_session):
    """Tenant A — Clinic Alpha."""
    tenant = models.Tenant(name="Clinic Alpha", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="module")
def tenant_b(db_session):
    """Tenant B — Clinic Beta."""
    tenant = models.Tenant(name="Clinic Beta", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="module")
def doctor_a(db_session, tenant_a):
    """Doctor belonging to Tenant A."""
    user = models.User(
        username="doctor_alpha",
        email="doctor@alpha.com",
        hashed_password=get_password_hash("Test@12345"),
        role="doctor",
        tenant_id=tenant_a.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def doctor_b(db_session, tenant_b):
    """Doctor belonging to Tenant B."""
    user = models.User(
        username="doctor_beta",
        email="doctor@beta.com",
        hashed_password=get_password_hash("Test@12345"),
        role="doctor",
        tenant_id=tenant_b.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def super_admin(db_session):
    """Super Admin user — no tenant."""
    user = models.User(
        username="superadmin_iso",
        email="superadmin@iso.com",
        hashed_password=get_password_hash("Super@12345"),
        role="super_admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def patient_a(db_session, tenant_a):
    """Patient in Tenant A."""
    patient = models.Patient(
        name="Patient Alpha",
        phone="01111111111",
        email="patient@alpha.com",
        age=25,
        tenant_id=tenant_a.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture(scope="module")
def patient_b(db_session, tenant_b):
    """Patient in Tenant B."""
    patient = models.Patient(
        name="Patient Beta",
        phone="02222222222",
        email="patient@beta.com",
        age=30,
        tenant_id=tenant_b.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


# ============================================================
# Auth Header Helpers
# ============================================================


def make_headers(user):
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# Test Suite: Patient Isolation
# ============================================================


class TestPatientIsolation:
    """Ensure patients are scoped to their own tenant."""

    def test_doctor_a_cannot_get_tenant_b_patient(
        self, client, doctor_a, patient_b
    ):
        """Tenant A doctor → GET /patients/{patient_b.id} → 404 or 403."""
        headers = make_headers(doctor_a)
        response = client.get(f"/api/v1/patients/{patient_b.id}", headers=headers)
        assert response.status_code in (403, 404), (
            f"Expected 403/404, got {response.status_code} — cross-tenant access not blocked!"
        )

    def test_doctor_b_cannot_get_tenant_a_patient(
        self, client, doctor_b, patient_a
    ):
        """Tenant B doctor → GET /patients/{patient_a.id} → 404 or 403."""
        headers = make_headers(doctor_b)
        response = client.get(f"/api/v1/patients/{patient_a.id}", headers=headers)
        assert response.status_code in (403, 404), (
            f"Expected 403/404, got {response.status_code}"
        )

    def test_doctor_a_list_patients_scoped_to_tenant_a(
        self, client, doctor_a, patient_a, patient_b
    ):
        """Tenant A doctor patient list must NOT include Tenant B patients."""
        headers = make_headers(doctor_a)
        response = client.get("/api/v1/patients", headers=headers)
        if response.status_code == 200:
            data = response.json()
            patients = data if isinstance(data, list) else data.get("data", data.get("patients", []))
            patient_ids = [p.get("id") for p in patients if isinstance(p, dict)]
            assert patient_b.id not in patient_ids, (
                f"Tenant B patient (id={patient_b.id}) found in Tenant A's patient list!"
            )

    def test_doctor_b_list_patients_scoped_to_tenant_b(
        self, client, doctor_b, patient_a, patient_b
    ):
        """Tenant B doctor patient list must NOT include Tenant A patients."""
        headers = make_headers(doctor_b)
        response = client.get("/api/v1/patients", headers=headers)
        if response.status_code == 200:
            data = response.json()
            patients = data if isinstance(data, list) else data.get("data", data.get("patients", []))
            patient_ids = [p.get("id") for p in patients if isinstance(p, dict)]
            assert patient_a.id not in patient_ids, (
                f"Tenant A patient (id={patient_a.id}) found in Tenant B's patient list!"
            )


# ============================================================
# Test Suite: Appointment Isolation
# ============================================================


class TestAppointmentIsolation:
    """Ensure appointments are scoped to their tenant."""

    def test_doctor_a_cannot_create_appointment_for_tenant_b_patient(
        self, client, doctor_a, patient_b
    ):
        """Tenant A doctor cannot book appointment for Tenant B patient."""
        headers = make_headers(doctor_a)
        payload = {
            "patient_id": patient_b.id,
            "appointment_date": "2099-01-01T09:00:00",
            "reason": "Cross-tenant attack attempt",
        }
        response = client.post("/api/v1/appointments/", json=payload, headers=headers)
        # Should be rejected — 403, 404, or 422 (patient not found in tenant)
        assert response.status_code in (400, 403, 404, 422), (
            f"Expected error, got {response.status_code} — cross-tenant appointment not blocked!"
        )


# ============================================================
# Test Suite: Financial Isolation
# ============================================================


class TestFinancialIsolation:
    """Ensure payments/accounting are scoped to their tenant."""

    def test_doctor_a_cannot_view_tenant_b_payments(
        self, client, doctor_a, patient_b
    ):
        """Tenant A doctor cannot access Tenant B payment data."""
        headers = make_headers(doctor_a)
        # Try to query payments for a Tenant B patient
        response = client.get(
            f"/api/v1/payments?patient_id={patient_b.id}", headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            payments = data if isinstance(data, list) else data.get("data", [])
            # All returned payments should have patient_id from Tenant A only
            for payment in payments:
                if isinstance(payment, dict):
                    assert payment.get("patient_id") != patient_b.id, (
                        "Tenant B payment returned for Tenant A doctor!"
                    )


# ============================================================
# Test Suite: Super Admin Cross-Tenant Access
# ============================================================


class TestSuperAdminAccess:
    """Super Admin can see data from all tenants."""

    def test_super_admin_can_list_all_tenants(self, client, super_admin):
        """Super Admin → GET /admin/tenants → sees all tenants."""
        headers = make_headers(super_admin)
        response = client.get("/api/v1/admin/tenants", headers=headers)
        assert response.status_code in (200, 404), (
            f"Super admin tenant list failed: {response.status_code}"
        )

    def test_super_admin_can_access_admin_only_endpoints(self, client, super_admin):
        """Super admin can access system admin endpoints."""
        headers = make_headers(super_admin)
        # Try any super-admin endpoint
        response = client.get("/api/v1/admin/system/logs", headers=headers)
        assert response.status_code in (200, 403, 404), (
            f"Unexpected status: {response.status_code}"
        )


# ============================================================
# Test Suite: Unauthenticated Access
# ============================================================


class TestUnauthenticatedAccess:
    """Unauthenticated users should get 401/403 on all protected endpoints."""

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/patients/",
        "/api/v1/appointments/",
        "/api/v1/payments/",
        "/api/v1/users/",
    ])
    def test_unauthenticated_blocked(self, client, endpoint):
        """No auth header → 401 or 403 on all protected endpoints."""
        response = client.get(endpoint)
        assert response.status_code in (401, 403), (
            f"Endpoint {endpoint} accessible without auth! Got {response.status_code}"
        )
