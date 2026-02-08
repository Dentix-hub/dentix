"""
Debug script to check active sessions for materials.
"""
import sqlite3
import os

# Connect to database - using PROJECT ROOT clinic.db (as per .env)
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'clinic.db')
print(f"Database: {db_path}")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n=== All Materials ===")
cursor.execute("SELECT id, name, type, tenant_id FROM materials")
for row in cursor.fetchall():
    print(f"  ID={row['id']}, Name={row['name']}, Type={row['type']}, Tenant={row['tenant_id']}")

print("\n=== All Active Sessions ===")
cursor.execute("""
    SELECT 
        ms.id as session_id,
        ms.status,
        si.id as stock_item_id,
        si.quantity as stock_qty,
        m.id as material_id,
        m.name as material_name,
        m.type as material_type
    FROM material_sessions ms
    JOIN stock_items si ON ms.stock_item_id = si.id
    JOIN batches b ON si.batch_id = b.id
    JOIN materials m ON b.material_id = m.id
    WHERE ms.status = 'ACTIVE'
""")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  Session ID={row['session_id']}, Status={row['status']}, Material={row['material_name']} (ID={row['material_id']}), Type={row['material_type']}, StockQty={row['stock_qty']}")
else:
    print("  No active sessions found!")

print("\n=== Composite Material Check ===")
cursor.execute("SELECT id, name, type FROM materials WHERE name LIKE '%كومبوزيت%' OR name LIKE '%Composite%' OR name LIKE '%composite%'")
composite_rows = cursor.fetchall()
if composite_rows:
    for row in composite_rows:
        print(f"  Found: ID={row['id']}, Name={row['name']}, Type={row['type']}")
        
        # Check batches
        cursor.execute("SELECT id, batch_number FROM batches WHERE material_id = ?", (row['id'],))
        batches = cursor.fetchall()
        for b in batches:
            print(f"    Batch ID={b['id']}, Number={b['batch_number']}")
            
            # Check stock items
            cursor.execute("SELECT id, quantity FROM stock_items WHERE batch_id = ?", (b['id'],))
            items = cursor.fetchall()
            for si in items:
                print(f"      StockItem ID={si['id']}, Qty={si['quantity']}")
                
                # Check sessions
                cursor.execute("SELECT id, status FROM material_sessions WHERE stock_item_id = ?", (si['id'],))
                sessions = cursor.fetchall()
                for s in sessions:
                    print(f"        Session ID={s['id']}, Status={s['status']}")
else:
    print("  No composite material found!")

conn.close()
