import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

sys.path.append(os.getcwd())
from backend.database import SQLALCHEMY_DATABASE_URL
from backend.models import AIUsageLog, BackgroundJob

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    print("Testing DB Write...")
    # Test 1: BackgroundJob
    job = BackgroundJob(job_name="test_db_check", status="running")
    db.add(job)
    db.commit()
    print("   [OK] BackgroundJob insert success.")

    # Test 2: AIUsageLog (checking for Trace ID columns)
    try:
        log = AIUsageLog(
            username="test_user",
            query="test",
            trace_id="123", # New field
            trace_details="{}", # New field
            created_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        print("   [OK] AIUsageLog insert success (Schema matches).")
    except Exception as e:
        print(f"   [FAIL] AIUsageLog insert failed: {e}")
        db.rollback()

except Exception as e:
    print(f"   [FAIL] General DB Error: {e}")
finally:
    db.close()
