import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from services.accounting_service import AccountingService
from models import User, Treatment, Payment, LabOrder
from core.database import Base, get_db_url
import os

# Setup DB connection
# Assuming sqlite for dev or the url from environment. 
# Since we are in the backend dir, we can try to connect to dev.db
DATABASE_URL = "sqlite:///./dev.db" # Adjust if necessary

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def test_calc():
    print("--- Starting Calculation Debug ---")
    
    # 1. Inspect Service Code Logic (by running it)
    tenant_id = 1 # user tenant
    service = AccountingService(db, tenant_id)
    
    end = datetime.now()
    start = end - timedelta(days=30)
    
    print(f"Date Range: {start} to {end}")
    
    # Get Analytics
    print("Fetching Analytics...")
    analytics = service.get_doctor_revenue_analytics(start, end)
    
    for doc in analytics:
        print(f"Dr. {doc['doctor_name']} | Revenue: {doc['revenue']} | Collected: {doc['collected']} | Lab: {doc['lab_cost']} | %: {doc['commission_percent']}")

    # Calculate Dues
    print("Calculating Dues...")
    dues, total = service.calculate_doctor_dues(start, end)
    
    for d in dues:
        print(f"Dr. {d['name']} | Base (Coll-Lab): {d['commission_base']} | Calc Due: {d['total_due']}")
        
        # Verify Formula
        expected = (d['collected'] - d['lab_cost']) * (d['commission_percent']/100) + d['fixed_salary']
        if abs(expected - d['total_due']) > 0.1:
            print(f"XXX MISMATCH! Expected {expected}, Got {d['total_due']}")
        else:
            print(">>> Matches Formula")

if __name__ == "__main__":
    try:
        test_calc()
    except Exception as e:
        print(e)
