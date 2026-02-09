import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from backend.models import Base, Treatment, Patient, Payment, User
import os
from datetime import datetime, timedelta

# DATABASE_URL = os.getenv("DATABASE_URL")
# Override to check backend DB
DATABASE_URL = "sqlite:///backend/clinic.db"
if not DATABASE_URL:
    print("DATABASE_URL is not set")
    exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def debug_financials():
    print("-" * 50)
    print("DEBUGGING FINANCIAL STATS")
    print("-" * 50)

    # 1. Get Tenants
    tenants = db.query(User.tenant_id).distinct().all()
    tenant_ids = [t[0] for t in tenants if t[0] is not None]
    
    # Default to tenant_id=1 if no users found (unlikely but safe)
    if not tenant_ids:
        tenant_ids = [1]

    print(f"Found Tenant IDs: {tenant_ids}")

    for tenant_id in tenant_ids:
        print(f"\nAnalyzing Tenant ID: {tenant_id}")
        
        # Date RAnge (Last 30 days to match default frontend)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"Date Range: {start_date.date()} to {end_date.date()}")

        # 2. RAW DUMP (No filters to verify data)
        print("\n--- RAW DATA CHECK ---")
        
        all_treatments = db.query(Treatment).limit(5).all()
        print(f"Total Treatments in DB: {db.query(Treatment).count()}")
        for t in all_treatments:
            print(f"RAW Treat: ID={t.id} Date={t.date} PatientID={t.patient_id} Tenant={t.tenant_id} Cost={t.cost}")

        all_payments = db.query(Payment).limit(5).all()
        print(f"Total Payments in DB: {db.query(Payment).count()}")
        for p in all_payments:
            print(f"RAW Pay: ID={p.id} Date={p.date} PatientID={p.patient_id} Amount={p.amount}")

        # 3. Analyze specific Patient 'Nadia' if possible (by checking recent big payments)
        # ...

if __name__ == "__main__":
    debug_financials()
