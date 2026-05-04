
import os
import sys
from sqlalchemy import create_engine, text

# Set up DB connection
DB_URL = "sqlite:///D:/DENTIX/backend/dentix.db"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Check patient with ID 1
    result = conn.execute(text("SELECT id, name FROM patients WHERE id = 1")).fetchone()
    if result:
        print(f"ID: {result[0]}, NAME: '{result[1]}'")
    else:
        print("Patient 1 not found")

    # Check all patients to see if it's widespread
    results = conn.execute(text("SELECT id, name FROM patients LIMIT 5")).fetchall()
    print("\nRECENT PATIENTS:")
    for row in results:
        print(f"ID: {row[0]}, NAME: '{row[1]}'")
