from sqlalchemy.orm import Session
import sys
import os

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models.clinical import Procedure
from backend.models.user import User

def debug_procedures():
    db = SessionLocal()
    try:
        # Check Procedures
        procs = db.query(Procedure).all()
        print(f"Total Procedures in DB: {len(procs)}")
        if procs:
            print(f"Sample Procedure: ID={procs[0].id}, Name={procs[0].name}, TenantID={procs[0].tenant_id}")
            t_ids = set(p.tenant_id for p in procs)
            print(f"Tenant IDs found in Procedures: {t_ids}")
        else:
            print("No procedures in DB!")

        # Check Admin User
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"User: {u.username}, Role: {u.role}, TenantID: {u.tenant_id}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_procedures()
