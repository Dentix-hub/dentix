import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import models, crud, schemas
from backend.auth import get_password_hash

# Mock DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./backend/clinic.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
models.Base.metadata.create_all(bind=engine)  # Create tables
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = TestingSessionLocal()

# Mock Admin
admin_user = db.query(models.User).filter(models.User.role == "admin").first()
if not admin_user:
    # Create temp admin if needed (unlikely if seeded)
    print("No admin found, creating mock")
    admin_user = models.User(username="mock_admin", role="admin", tenant_id=1)

print(f"Acting as Admin: {admin_user.username}")

# Inputs from failed request
username = "admin"
password = "password123"
role = "doctor"
permissions = '["view_patients","edit_patients","view_treatments","view_financials","manage_lab","edit_treatments"]'

# Logic from routers/users.py
try:
    print("--- 1. Check if user exists ---")
    existing = crud.get_user(db, username)
    if existing:
        print(f"FAIL: User {username} already exists (ID: {existing.id})")
        # sys.exit(0) # Don't exit, just reporting

    print("--- 2. Check User Limit ---")
    tenant = (
        db.query(models.Tenant).filter(models.Tenant.id == admin_user.tenant_id).first()
    )
    if tenant and tenant.subscription_plan:
        max_users = tenant.subscription_plan.max_users
        print(f"Max Users: {max_users}")
        if max_users is not None:
            current_count = (
                db.query(models.User)
                .filter(models.User.tenant_id == admin_user.tenant_id)
                .count()
            )
            print(f"Current Count: {current_count}")
            if current_count >= max_users:
                print(f"FAIL: User limit reached ({current_count}/{max_users})")

    print("--- 3. Password Strength ---")
    if (
        len(password) < 6
        or not any(c.isalpha() for c in password)
        or not any(c.isdigit() for c in password)
    ):
        print("FAIL: Password weak")
    else:
        print("Password OK")

    print("--- 4. Attempt Create (Dry Run) ---")
    # Don't actually commit if we want to preserve state, or do?
    # validation passed so far?

    hashed = get_password_hash(password)
    user_in = schemas.User(username=username, role=role, permissions=permissions)
    # logic seems okay?

except Exception as e:
    print(f"EXCEPTION: {e}")
finally:
    db.close()
