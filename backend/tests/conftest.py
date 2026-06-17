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

# Force SQLite and Test Mode for all backend imports
os.environ["DATABASE_URL"] = "sqlite:///file:testdb?mode=memory&cache=shared&uri=true"
os.environ["ENVIRONMENT"] = "testing"

# Mock RLS registration for SQLite test environment to prevent syntax errors
try:
    import rls.register_rls
    rls.register_rls.register_rls = lambda *args, **kwargs: None
except ImportError:
    pass

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.database import Base, get_async_db
from backend import models
from backend.auth import create_access_token


# ============================================
# DATABASE FIXTURES
# ============================================


@pytest.fixture(scope="session")
def engine():
    """Create a persistent in-memory SQLite engine for the whole session."""
    engine = create_engine(
        "sqlite:///file:testdb?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="session")
def async_engine_fixture():
    """Create a persistent async SQLite engine for the session."""
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine


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
async def async_db_session(async_engine_fixture):
    """Create an async database session for testing."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    TestingAsyncSessionLocal = async_sessionmaker(
        bind=async_engine_fixture, expire_on_commit=False, autoflush=False
    )
    async with TestingAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="function", autouse=True)
def cleanup_database(engine):
    yield
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
            trans.commit()
        except Exception:
            trans.rollback()
            raise


@pytest.fixture(scope="function", autouse=True)
def reset_tenant_context_fixture():
    from backend.core.tenancy import reset_current_tenant_id, clear_tenant_context
    yield
    reset_current_tenant_id()
    clear_tenant_context()


@pytest.fixture(scope="function", autouse=True)
async def cleanup_async_database(async_engine_fixture):

    yield
    async with async_engine_fixture.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture(scope="function")
def client(db_session, async_engine_fixture):
    """Create a test client with database override."""

    async def override_get_async_db():
        from sqlalchemy.ext.asyncio import async_sessionmaker
        TestingAsyncSessionLocal = async_sessionmaker(
            bind=async_engine_fixture, expire_on_commit=False, autoflush=False
        )
        async with TestingAsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_async_db] = override_get_async_db

    # Reset rate limiter state so tests don't get 429 from previous runs
    try:
        from backend.core.limiter import limiter
        limiter.reset()
    except Exception:
        pass

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()


# ============================================
# DATA FIXTURES
# ============================================


@pytest.fixture
def test_tenant(db_session):
    """Create a test tenant with unique name."""
    import uuid
    uid = str(uuid.uuid4())[:8]
    tenant = models.Tenant(name=f"Test Clinic {uid}", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db_session, test_tenant):
    """Create a test user with unique username."""
    from backend.auth import get_password_hash
    import uuid
    uid = str(uuid.uuid4())[:8]
    user = models.User(
        username=f"doctor_{uid}",
        email=f"doctor_{uid}@test.com",
        hashed_password=get_password_hash("testpass123"),
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, test_tenant):
    """Create a test admin user with unique username."""
    from backend.auth import get_password_hash
    import uuid
    uid = str(uuid.uuid4())[:8]
    user = models.User(
        username=f"admin_{uid}",
        email=f"admin_{uid}@test.com",
        hashed_password=get_password_hash("adminpass123"),
        role="admin",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def super_admin_user(db_session):
    """Create a super admin user (no tenant)."""
    from backend.auth import get_password_hash

    user = db_session.query(models.User).filter(models.User.username == "superadmin").first()
    if not user:
        user = models.User(
            username="superadmin",
            email="super@test.com",
            hashed_password=get_password_hash("superpass123"),
            role="super_admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def test_patient(db_session, test_tenant, test_user):
    """Create a test patient assigned to the test doctor."""
    patient = models.Patient(
        name="Test Patient",
        phone="01234567890",
        email="patient@test.com",
        age=30,
        tenant_id=test_tenant.id,
        assigned_doctor_id=test_user.id,
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
    token = create_access_token(
        data={
            "sub": test_user.username,
            "role": test_user.role,
            "tenant_id": test_user.tenant_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Get authentication headers for admin user."""
    token = create_access_token(
        data={
            "sub": admin_user.username,
            "role": admin_user.role,
            "tenant_id": admin_user.tenant_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def super_admin_headers(super_admin_user):
    """Get authentication headers for super admin."""
    token = create_access_token(
        data={
            "sub": super_admin_user.username,
            "role": super_admin_user.role,
            "tenant_id": super_admin_user.tenant_id,
        }
    )
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
