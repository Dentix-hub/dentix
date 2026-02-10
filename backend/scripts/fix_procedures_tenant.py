import sys
import os

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import SessionLocal
from backend.models.clinical import Procedure


def fix_procedures_tenant():
    db = SessionLocal()
    try:
        # Fetch all procedures with tenant_id=1
        procs = db.query(Procedure).filter(Procedure.tenant_id == 1).all()
        print(f"Found {len(procs)} procedures with tenant_id=1.")

        for p in procs:
            p.tenant_id = None  # Make them global

        db.commit()
        print(f"Updated {len(procs)} procedures to be Global (tenant_id=NULL).")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_procedures_tenant()
