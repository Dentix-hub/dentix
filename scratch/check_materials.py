import sqlite3
import os

db_path = r'd:\DENTIX\backend\dentix.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Materials ---")
cursor.execute("SELECT id, brand, name, category_id FROM materials LIMIT 20")
for row in cursor.fetchall():
    print(row)

print("\n--- Categories ---")
cursor.execute("SELECT id, name_ar, name_en FROM material_categories")
for row in cursor.fetchall():
    print(row)

conn.close()
