import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.database import Base, get_db
from backend import models, auth
import os

# Setup In-Memory DB for testing
# Setup DB for testing
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    # If no DB set, maybe skip or use a strict fail. 
    # For CI/CD, usually we want a service container.
    # We will raise error to be compliant with "No hidden SQLite"
    raise RuntimeError("DATABASE_URL must be set for tests.")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create Test Admin User
    db = TestingSessionLocal()
    password_hash = auth.get_password_hash("testpassword")
    
    # Create Tenant first
    tenant = models.Tenant(name="Test Clinic")
    db.add(tenant)
    db.commit()
    
    user = models.User(
        username="testadmin", 
        hashed_password=password_hash, 
        role="super_admin", 
        tenant_id=tenant.id
    )
    db.add(user)
    db.commit()
    yield db
    Base.metadata.drop_all(bind=engine)

def test_auth_process(test_db):
    # 1. Login
    login_payload = {"username": "testadmin", "password": "testpassword"}
    response = client.post("/token", data=login_payload)
    assert response.status_code == 200, f"Login failed: {response.text}"
    
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    
    # 2. Access Protected Route
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/users/me/", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testadmin"
    
    # 3. Refresh Token
    refresh_payload = {"refresh_token": refresh_token}
    response = client.post("/auth/refresh", data=refresh_payload)
    assert response.status_code == 200
    
    new_tokens = response.json()
    assert "access_token" in new_tokens
    new_access_token = new_tokens["access_token"]
    
    # Verify new access token works
    headers = {"Authorization": f"Bearer {new_access_token}"}
    response = client.get("/users/me/", headers=headers)
    assert response.status_code == 200

    # 4. Invalid Refresh Token
    response = client.post("/auth/refresh", data={"refresh_token": "invalid_token"})
    assert response.status_code == 401

