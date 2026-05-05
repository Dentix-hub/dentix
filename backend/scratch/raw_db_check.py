import sqlite3
import os

db_paths = [
    "d:/DENTIX/backend/dentix.db",
    "d:/DENTIX/dentix.db"
]

for path in db_paths:
    print(f"--- Checking {path} ---")
    if not os.path.exists(path):
        print("File not found")
        continue

    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"Tables: {tables}")

        if "patients" in tables:
            cursor.execute("SELECT id, name FROM patients LIMIT 5;")
            rows = cursor.fetchall()
            print("Patients data:")
            for row in rows:
                print(row)
        else:
            print("No 'patients' table found")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")
    print()
