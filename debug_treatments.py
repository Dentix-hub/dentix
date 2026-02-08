"""Debug script to check treatments and procedures matching."""
import sqlite3

conn = sqlite3.connect('clinic.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== Treatments during session window (Session 30) ===')
# Session 30 was opened at 2026-02-03 20:19:17 and closed at 2026-02-03 20:21:02
cursor.execute("""SELECT t.id, t.procedure, t.doctor_id, t.date, t.tenant_id 
FROM treatments t 
WHERE t.date >= '2026-02-03 20:19:17' AND t.date <= '2026-02-03 20:21:02'
AND t.tenant_id = 1
LIMIT 20""")
treatments = cursor.fetchall()
if treatments:
    for t in treatments:
        print(dict(t))
else:
    print('  No treatments found in this window!')

print()
print('=== Recent Treatments (last 10) ===')
cursor.execute('SELECT id, procedure, doctor_id, date, tenant_id FROM treatments ORDER BY id DESC LIMIT 10')
recent = cursor.fetchall()
for r in recent:
    print(dict(r))

print()
print('=== Procedures Table ===')
cursor.execute('SELECT id, name, tenant_id FROM procedures WHERE tenant_id = 1 LIMIT 10')
procs = cursor.fetchall()
for p in procs:
    print(dict(p))

conn.close()
