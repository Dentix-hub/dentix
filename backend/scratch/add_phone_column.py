import sqlite3
import os

db_path = "d:/DENTIX/dentix.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(tenants)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "contact_phone" not in columns:
            print("Adding contact_phone column to tenants table...")
            cursor.execute("ALTER TABLE tenants ADD COLUMN contact_phone TEXT")
            conn.commit()
            print("Column added successfully.")
        else:
            print("contact_phone column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
