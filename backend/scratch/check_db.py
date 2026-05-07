import sqlite3
import os

db_path = "d:/DENTIX/backend/dentix.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in {db_path}: {tables}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")
