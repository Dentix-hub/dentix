import sqlite3
conn = sqlite3.connect('clinic.db')
cursor = conn.cursor()
cursor.execute('SELECT id, name, tenant_id FROM procedures')
rows = cursor.fetchall()
print('=== All Procedures ===')
for r in rows:
    print(f'  ID={r[0]}, tenant={r[2]}, name={r[1][:50]}')
conn.close()
