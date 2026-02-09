import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
import os
from sqlalchemy import create_engine, text

# Add root to path so we can import backend if needed, 
# but for this text we just check the file directly via sqlite url.
print(f"CWD: {os.getcwd()}")
db_path = "sqlite:///clinic.db"
print(f"Connecting to: {db_path}")

try:
    engine = create_engine(db_path)
    with engine.connect() as conn:
        # Check Tenants
        tenants = conn.execute(text("SELECT * FROM tenants")).fetchall()
        print(f"Tenants Count: {len(tenants)}")
        print(f"Tenants Data: {tenants}")

        # Check Procedures
        procs = conn.execute(text("SELECT count(*) FROM procedures")).scalar()
        print(f"Total Procedures: {procs}")
        
        global_procs = conn.execute(text("SELECT count(*) FROM procedures WHERE tenant_id IS NULL")).scalar()
        print(f"Global Procedures: {global_procs}")
        
        # Check PriceLists
        pl = conn.execute(text("SELECT count(*) FROM price_lists")).scalar()
        print(f"Total PriceLists: {pl}")

except Exception as e:
    print(f"Error: {e}")
