"""
Test Fixtures for Smart Clinic Backend.

This module provides shared fixtures for all tests:
- Database session management
- Test client setup  
- Authentication helpers
- Sample data factories
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.database import Base, get_db
from backend import models
from backend.auth import create_access_token


# ============================================
# DATABASE FIXTURES
# ============================================

@pytest.fixture(scope="function")
def engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a database session for testing."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================
# DATA FIXTURES
# ============================================

@pytest.fixture
def test_tenant(db_session):
    """Create a test tenant."""
    tenant = models.Tenant(
        name="Test Clinic",
        subdomain="test",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db_session, test_tenant):
    """Create a test user with doctor role."""
    from backend.auth import get_password_hash
    
    user = models.User(
        username="testdoctor",
        email="doctor@test.com",
        full_name="Test Doctor",
        hashed_password=get_password_hash("testpass123"),
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, test_tenant):
    """Create a test admin user."""
    from backend.auth import get_password_hash
    
    user = models.User(
        username="testadmin",
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("adminpass123"),
        role="admin",
        tenant_id=test_tenant.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def super_admin_user(db_session):
    """Create a super admin user (no tenant)."""
    from backend.auth import get_password_hash
    
    user = models.User(
        username="superadmin",
        email="super@test.com",
        full_name="Super Admin",
        hashed_password=get_password_hash("superpass123"),
        role="super_admin",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_patient(db_session, test_tenant):
    """Create a test patient."""
    patient = models.Patient(
        name="Test Patient",
        phone="01234567890",
        email="patient@test.com",
        age=30,
        gender="male",
        tenant_id=test_tenant.id
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


# ============================================
# AUTH FIXTURES
# ============================================

@pytest.fixture
def auth_headers(test_user):
    """Get authentication headers for test user."""
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Get authentication headers for admin user."""
    token = create_access_token(data={"sub": admin_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def super_admin_headers(super_admin_user):
    """Get authentication headers for super admin."""
    token = create_access_token(data={"sub": super_admin_user.username})
    return {"Authorization": f"Bearer {token}"}


# ============================================
# MOCK FIXTURES
# ============================================

@pytest.fixture
def mock_groq_client():
    """Mock Groq API client."""
    mock = MagicMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Test AI response"))]
    )
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock
