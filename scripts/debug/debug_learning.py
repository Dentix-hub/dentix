import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
"""Debug script to check learning data in database."""
import sqlite3

conn = sqlite3.connect('clinic.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== Material Learning Logs ===')
cursor.execute('SELECT * FROM material_learning_logs ORDER BY id DESC LIMIT 10')
logs = cursor.fetchall()
if logs:
    for l in logs:
        print(dict(l))
else:
    print('  No learning logs found!')

print()
print('=== Closed Sessions ===')
cursor.execute("""SELECT ms.id, ms.status, ms.total_amount_consumed, ms.opened_at, ms.closed_at, m.name as material_name
FROM material_sessions ms 
JOIN stock_items si ON ms.stock_item_id = si.id 
JOIN batches b ON si.batch_id = b.id 
JOIN materials m ON b.material_id = m.id 
WHERE ms.status = 'CLOSED' 
ORDER BY ms.closed_at DESC LIMIT 5""")
sessions = cursor.fetchall()
if sessions:
    for s in sessions:
        print(dict(s))
else:
    print('  No closed sessions found!')

print()
print('=== ProcedureMaterialWeight with learning data ===')
cursor.execute("""SELECT pmw.*, p.name as proc_name, m.name as mat_name 
FROM procedure_material_weights pmw 
JOIN procedures p ON pmw.procedure_id = p.id 
JOIN materials m ON pmw.material_id = m.id 
WHERE pmw.current_average_usage > 0 OR pmw.sample_size > 0 LIMIT 10""")
weights = cursor.fetchall()
if weights:
    for w in weights:
        print(dict(w))
else:
    print('  No weights with learning data found!')

print()
print('=== All ProcedureMaterialWeight ===')
cursor.execute("""SELECT pmw.id, pmw.procedure_id, pmw.material_id, pmw.weight, pmw.current_average_usage, pmw.sample_size, p.name as proc_name, m.name as mat_name 
FROM procedure_material_weights pmw 
JOIN procedures p ON pmw.procedure_id = p.id 
JOIN materials m ON pmw.material_id = m.id 
LIMIT 20""")
all_weights = cursor.fetchall()
for w in all_weights:
    print(dict(w))

conn.close()
