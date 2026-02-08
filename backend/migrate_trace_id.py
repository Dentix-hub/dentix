import sys
import os
from sqlalchemy import create_engine, text

# Setup paths
sys.path.append(os.getcwd())

from backend.database import SQLALCHEMY_DATABASE_URL

def migrate_trace_id():
    print(">>> Applying Trace ID Migration...")
    
    # Strict DATABASE_URL check
    if not SQLALCHEMY_DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required. Production mode enforced.")
        
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # 1. Add trace_id to ai_usage_logs
            print("Adding 'trace_id' to 'ai_usage_logs'...")
            try:
                conn.execute(text("ALTER TABLE ai_usage_logs ADD COLUMN trace_id VARCHAR"))
                print("Added trace_id column.")
            except Exception as e:
                print(f"trace_id column might exist: {e}")

            # 2. Add trace_details to ai_usage_logs
            print("Adding 'trace_details' to 'ai_usage_logs'...")
            try:
                conn.execute(text("ALTER TABLE ai_usage_logs ADD COLUMN trace_details TEXT"))
                print("Added trace_details column.")
            except Exception as e:
                print(f"trace_details column might exist: {e}")

            conn.commit()
            print("Migration Successful!")
        except Exception as e:
            print(f"Migration Failed: {e}")

if __name__ == "__main__":
    migrate_trace_id()
