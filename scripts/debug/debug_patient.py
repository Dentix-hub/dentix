import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Candidate DBs
dbs = [
    "sqlite:///clinic.db",
    "sqlite:///backend/clinic.db",
    "sqlite:///backend/smart_clinic.db",
    "sqlite:///backend/database.db"
]

def check_patient():
    print("SEARCHING FOR 'Nadia' OR 'P-1'...")
    
    for db_url in dbs:
        print(f"\nChecking DB: {db_url}")
        try:
            if not os.path.exists(db_url.replace("sqlite:///", "")):
                print(" -> File not found.")
                continue
                
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # 1. Search Patient
                res = conn.execute(text("SELECT id, name, tenant_id, is_deleted FROM patients WHERE name LIKE '%Nadia%' OR name LIKE '%نادية%'")).fetchall()
                if not res:
                    print(" -> No patient found.")
                    continue
                
                for p in res:
                    print(f" -> FOUND PATIENT: ID={p.id} Name={p.name} Tenant={p.tenant_id} Deleted={p.is_deleted}")
                    
                    # 2. Check Payments
                    pay_res = conn.execute(text(f"SELECT id, amount, date FROM payments WHERE patient_id = {p.id}")).fetchall()
                    print(f"    -> PAYMENTS ({len(pay_res)}):")
                    for pay in pay_res:
                        print(f"       ID={pay.id} Amt={pay.amount} Date={pay.date}")

                    # 3. Check Treatments
                    treat_res = conn.execute(text(f"SELECT id, cost, date FROM treatments WHERE patient_id = {p.id}")).fetchall()
                    print(f"    -> TREATMENTS ({len(treat_res)}):")
                    for t in treat_res:
                        print(f"       ID={t.id} Cost={t.cost} Date={t.date}")

        except Exception as e:
            print(f" -> Error: {e}")

if __name__ == "__main__":
    check_patient()
