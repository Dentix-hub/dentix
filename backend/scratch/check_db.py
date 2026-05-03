import sqlite3
import os

db_path = 'dentix.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f" - {table[0]}")
        
    if ('system_errors',) in tables:
        print("\nLatest System Error:")
        cursor.execute("SELECT message, stack_trace FROM system_errors ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        if row:
            print(f"Message: {row[0]}")
            print(f"Stack Trace:\n{row[1]}")
        else:
            print("No errors found in system_errors.")
    else:
        # Check if there is an error_log table
        if ('error_log',) in tables:
             cursor.execute("SELECT message FROM error_log ORDER BY id DESC LIMIT 1;")
             row = cursor.fetchone()
             if row: print(f"Error log: {row[0]}")
             
    conn.close()
