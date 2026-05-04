from backend.database import SessionLocal
from backend import models
import bcrypt

def get_password_hash(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_super_admin():
    db = SessionLocal()
    try:
        username = "admin@dentix.com"
        # Check if already exists
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            existing.role = "super_admin"
            existing.hashed_password = get_password_hash("password123")
            db.commit()
            print(f"Updated existing user {username} to super_admin")
            return

        user = models.User(
            username=username,
            hashed_password=get_password_hash("password123"),
            role="super_admin",
            tenant_id=None, # Super admin doesn't belong to a tenant
        )
        db.add(user)
        db.commit()
        print(f"Created super_admin user: {username}")
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
