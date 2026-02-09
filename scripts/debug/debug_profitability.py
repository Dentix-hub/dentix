import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.database import SessionLocal, get_db
from backend import models
from backend.services.inventory_service import inventory_service
from datetime import datetime, timedelta
from sqlalchemy import func

def debug_cogs():
    db = SessionLocal()
    try:
        # Get a valid admin user (or any user)
        user = db.query(models.User).filter(models.User.role == "admin").first()
        if not user:
            print("No admin user found")
            return
            
        print(f"Testing for Tenant: {user.tenant_id}")
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        print("Calculating COGS...")
        try:
            cogs = inventory_service.get_cogs_summary(
                start_date=start_date,
                end_date=end_date,
                tenant_id=user.tenant_id,
                db=db
            )
            print(f"COGS: {cogs}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_cogs()
