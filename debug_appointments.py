
from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = "sqlite:///clinic.db"

def check_appointments():
    print(f"Checking DB: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # 1. Total Appointments
        total = conn.execute(text("SELECT COUNT(*) FROM appointments")).scalar()
        print(f"Total Appointments Table Count: {total}")

        # 2. Today's Appointments (Raw)
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"Checking for date: {today}")
        
        query = text(f"""
            SELECT id, patient_id, date_time, status, is_deleted 
            FROM appointments 
            WHERE date_time LIKE '{today}%'
        """)
        
        rows = conn.execute(query).fetchall()
        print(f"\n--- Today's Appointments ({len(rows)}) ---")
        for r in rows:
            print(f"ID: {r.id} | PatID: {r.patient_id} | Time: {r.date_time} | Status: '{r.status}' | Deleted: {r.is_deleted}")

        # 3. Simulate the Backend Query Logic
        print("\n--- Simulating Logic (Not Cancelled + Not Deleted) ---")
        param_date = today
        logic_query = text(f"""
            SELECT COUNT(*) 
            FROM appointments 
            WHERE date_time LIKE '{param_date}%' 
            AND is_deleted = 0 
            AND status != 'Cancelled'
        """)
        logic_count = conn.execute(logic_query).scalar()
        print(f"Logic Count: {logic_count}")

        # List Tables
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
        print("\n--- Tables ---")
        for t in tables:
            print(t[0])

        # 4. Total Treatments
        treat_count = conn.execute(text("SELECT COUNT(*) FROM treatments")).scalar()
        print(f"\nTotal Treatments: {treat_count}")
        
        # 5. Today's Treatments
        today_treat = conn.execute(text(f"SELECT COUNT(*) FROM treatments WHERE date LIKE '{today}%'")).scalar()
        print(f"Today's Treatments: {today_treat}")

if __name__ == "__main__":
    check_appointments()
