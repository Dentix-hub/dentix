import sys
import os

# Add project root to path to allow importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.append(project_root)

from backend.database import SessionLocal, sync_engine
from backend import models, crud


def purge_deleted_patients():
    print(f"Engine URL: {sync_engine.url}")

    db = SessionLocal()
    try:
        print("--- DIAGNOSTIC START ---")
        # Check connection
        try:
            # Query strictly raw SQL to identify DB file
            from sqlalchemy import text

            result = db.execute(text("PRAGMA database_list;")).fetchall()
            print(f"Connected to Databases: {result}")
        except Exception as e:
            print(f"Failed to check DB list: {e}")

        total_patients = db.query(models.Patient).count()
        deleted_patients = (
            db.query(models.Patient).filter(models.Patient.is_deleted).all()
        )

        print(f"Total Patients in DB: {total_patients}")
        print(f"Soft-Deleted Patients found: {len(deleted_patients)}")

        if len(deleted_patients) > 0:
            print("Purging now...")
            for p in deleted_patients:
                try:
                    crud.delete_patient_permanently(db, p.id, p.tenant_id)
                    print(f"Purged: {p.name}")
                except Exception as e:
                    print(f"Failed to purge {p.name}: {e}")
        else:
            print("No soft-deleted patients found to purge.")

        print("--- DIAGNOSTIC END ---")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    purge_deleted_patients()
