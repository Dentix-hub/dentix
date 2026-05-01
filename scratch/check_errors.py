
import sys
import os
from sqlalchemy.orm import Session
# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models.system import SystemError

def get_recent_errors():
    db = SessionLocal()
    try:
        errors = db.query(SystemError).order_by(SystemError.created_at.desc()).limit(5).all()
        for err in errors:
            print(f"ID: {err.id} | Time: {err.created_at}")
            print(f"Path: {err.method} {err.path}")
            print(f"Message: {err.message}")
            print(f"Stack Trace: {err.stack_trace[:500]}...")
            print("-" * 50)
    finally:
        db.close()

if __name__ == "__main__":
    get_recent_errors()
