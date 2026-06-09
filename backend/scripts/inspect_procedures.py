import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inspect_procedures")

def load_dotenv():
    # Try to load .env from current directory or parent
    paths = [".env", "../.env", "../../.env"]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
            logger.info(f"Loaded environment variables from {path}")
            break

def main():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set.")
        sys.exit(0)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    try:
        logger.info(f"Connecting to: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # 1. Inspect procedures table
            res = conn.execute(text("SELECT id, name, tenant_id, price FROM procedures")).fetchall()
            logger.info(f"--- PROCEDURES ({len(res)}) ---")
            for r in res[:20]:
                logger.info(f"ID: {r[0]} | Name: {r[1]} | Tenant: {r[2]} | Price: {r[3]}")
            if len(res) > 20:
                logger.info("... and more")
                
            # 2. Inspect tenants
            res_tenants = conn.execute(text("SELECT id, name FROM tenants")).fetchall()
            logger.info(f"--- TENANTS ({len(res_tenants)}) ---")
            for r in res_tenants:
                logger.info(f"ID: {r[0]} | Name: {r[1]}")
                
            # 3. Inspect default price lists
            res_pl = conn.execute(text("SELECT id, name, tenant_id, is_default FROM price_lists")).fetchall()
            logger.info(f"--- PRICE LISTS ({len(res_pl)}) ---")
            for r in res_pl:
                logger.info(f"ID: {r[0]} | Name: {r[1]} | Tenant: {r[2]} | Default: {r[3]}")
                
            # 4. Inspect price list items count
            res_items = conn.execute(text("SELECT price_list_id, COUNT(*) FROM price_list_items GROUP BY price_list_id")).fetchall()
            logger.info(f"--- PRICE LIST ITEMS COUNT ---")
            for r in res_items:
                logger.info(f"Price List ID: {r[0]} | Count: {r[1]}")
                
    except Exception as e:
        logger.error(f"Error inspecting procedures: {e}", exc_info=True)

if __name__ == "__main__":
    main()
