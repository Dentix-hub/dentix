import os
import sys

# Ensure backend path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set env for testing (though main.py might not use it if loaded??)
os.environ["DATABASE_URL"] = "sqlite:///./debug_auth.db"

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models import User
from backend.auth import create_access_token
from fastapi.testclient import TestClient


def debug_auth():
    print("DEBUG: Starting Debug Auth Script")

    # 1. Setup DB
    if os.path.exists("./debug_auth.db"):
        os.remove("./debug_auth.db")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 2. Create User
        print("DEBUG: Creating Super Admin")
        admin = User(
            username="test_super_admin",
            email="admin@test.com",
            hashed_password="hashed_secret",
            role="super_admin",
            tenant_id=1,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"DEBUG: User Created: {admin.id}, {admin.username}, {admin.tenant_id}")

        # 3. Generate Token
        token = create_access_token(
            data={
                "sub": admin.username,
                "role": "super_admin",
                "tenant_id": admin.tenant_id,
            }
        )
        print(f"DEBUG: Token Generated: {token}")

        # 4. Test Client
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}

        print("DEBUG: Hitting /debug/me")
        response = client.get("/debug/me", headers=headers)

        print(f"DEBUG: Response Status: {response.status_code}")
        print(f"DEBUG: Response Body: {response.text}")

        if response.status_code == 200:
            print("SUCCESS: Auth Verified")
        else:
            print("FAILURE: Auth Failed")

    finally:
        db.close()


if __name__ == "__main__":
    debug_auth()
