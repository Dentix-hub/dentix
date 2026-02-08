import sys
import os
# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.database import SQLALCHEMY_DATABASE_URL
from sqlalchemy import create_engine, text

print(f"CWD: {os.getcwd()}")
print(f"DB URL: {SQLALCHEMY_DATABASE_URL}")

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        tenants = conn.execute(text("SELECT * FROM tenants")).fetchall()
        print(f"Tenants Count: {len(tenants)}")
        print(f"Tenants Data: {tenants}")
        
        users = conn.execute(text("SELECT id, username, tenant_id FROM users")).fetchall()
        print(f"Users Count: {len(users)}")
        print(f"Users Data: {users}")

        pls = conn.execute(text("SELECT * FROM price_lists")).fetchall()
        print(f"PriceLists Count: {len(pls)}")
        print(f"PriceLists Data: {pls}")
except Exception as e:
    print(f"Error connecting: {e}")
