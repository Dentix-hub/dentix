import sys
import os
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models.user import User
from backend.auth import get_password_hash

def reset_eslam():
    db = SessionLocal()
    try:
        username = "eslam"
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"User '{username}' NOT FOUND. Creating new admin user...")
            new_user = User(
                username=username,
                email="eslam@smartclinic.com",
                hashed_password=get_password_hash("password123"),
                role="admin",
                tenant_id=1,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print(f"SUCCESS: Created user '{username}' with password 'password123'")
            return

        print(f"Found user: {user.username} (ID: {user.id})")
        new_hash = get_password_hash("password123")
        user.hashed_password = new_hash
        db.commit()
        print(f"SUCCESS: Password for '{user.username}' reset to 'password123'")

    finally:
        db.close()

if __name__ == "__main__":
    reset_eslam()
