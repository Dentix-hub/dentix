import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
import os
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models.system_log import SystemError
from sqlalchemy import desc

def read_last_error():
    db = SessionLocal()
    try:
        # Get 3 most recent errors to compare
        errors = db.query(SystemError).order_by(desc(SystemError.created_at)).limit(3).all()
        
        if not errors:
            print("No errors found in database.")
            return
        
        for i, err in enumerate(errors):
            print(f"\n--- ERROR #{i+1} ---")
            print(f"ID: {err.id}")
            print(f"Time: {err.created_at}")
            print(f"Path: {err.path}")
            print(f"Message: {err.message[:100]}...")
            if err.stack_trace:
                # Show last 500 chars of traceback (most relevant part)
                print(f"\n[TRACEBACK TAIL]:\n{err.stack_trace[-500:]}")
            print("-------------------")

    finally:
        db.close()

if __name__ == "__main__":
    read_last_error()
