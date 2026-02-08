import sys
import os
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models.user import User
from backend.auth import get_password_hash

def reset_password():
    db = SessionLocal()
    try:
        username = "admin@example.com"
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"User {username} not found. Creating user admin@example.com...")
            # Create a new admin user
            new_user = User(
                username=username,
                email=username,
                role="admin", 
                is_active=True,
                tenant_id=1
            )
            # Hash password immediately
            new_user.hashed_password = get_password_hash("password123")
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
            print(f"Created user: {user.username}")
        else:
            print(f"Found user: {user.username}")
            # Reset password
            user.hashed_password = get_password_hash("password123")
            db.commit()
            print(f"Password reset for {user.username} to 'password123'")
        
        print(f"USERNAME_TO_USE: {user.username}")

    finally:
        db.close()

if __name__ == "__main__":
    reset_password()
