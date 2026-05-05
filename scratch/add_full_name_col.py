import sqlite3
import os

db_path = "d:/DENTIX/dentix.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        print("Column full_name added to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column full_name already exists.")
        else:
            print(f"Error: {e}")
    conn.commit()
    conn.close()
else:
    print(f"Database not found at {db_path}")
