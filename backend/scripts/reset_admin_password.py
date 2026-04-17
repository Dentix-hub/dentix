import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend import models, auth


def reset_passwords():
    db = SessionLocal()
    try:
        print("Resetting admin passwords...")

        # 1. Reset Super Admin (Email)
        username_email = "eslamemara1312@gmail.com"
        user = (
            db.query(models.User).filter(models.User.username == username_email).first()
        )
        if user:
            new_hash = auth.get_password_hash("ESLAMomara11##")
            user.hashed_password = new_hash
            db.commit()
            print(f"Updated password for {username_email} (Hash: {new_hash[:10]}...)")
        else:
            print(f"User {username_email} not found.")

        # 2. Reset Default Admin (username)
        username_admin = "eslam"
        user_admin = (
            db.query(models.User).filter(models.User.username == username_admin).first()
        )
        if user_admin:
            new_hash_admin = auth.get_password_hash("1111")
            user_admin.hashed_password = new_hash_admin
            db.commit()
            print(
                f"Updated password for {username_admin} (Hash: {new_hash_admin[:10]}...)"
            )
        else:
            print(f"User {username_admin} not found.")

    except Exception as e:
        print(f"Error resetting passwords: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    reset_passwords()
