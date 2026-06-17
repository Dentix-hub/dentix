import sys
import os
import asyncio
from sqlalchemy import select, text

# Add project root to path to allow importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.append(project_root)

from backend.database import AsyncSessionLocal, async_engine
from backend import models, crud


async def purge_deleted_patients():
    print(f"Engine URL: {async_engine.url}")

    async with AsyncSessionLocal() as db:
        try:
            print("--- DIAGNOSTIC START ---")
            # Check connection
            try:
                # Query strictly raw SQL to identify DB file
                result = (await db.execute(text("PRAGMA database_list;"))).fetchall()
                print(f"Connected to Databases: {result}")
            except Exception as e:
                print(f"Failed to check DB list: {e}")

            # Get count of total patients
            total_stmt = select(models.Patient)
            res_total = await db.execute(total_stmt)
            total_patients = len(res_total.scalars().all())

            # Get soft deleted patients
            deleted_stmt = select(models.Patient).filter(models.Patient.is_deleted)
            res_deleted = await db.execute(deleted_stmt)
            deleted_patients = res_deleted.scalars().all()

            print(f"Total Patients in DB: {total_patients}")
            print(f"Soft-Deleted Patients found: {len(deleted_patients)}")

            if len(deleted_patients) > 0:
                print("Purging now...")
                for p in deleted_patients:
                    try:
                        await crud.delete_patient_permanently(db, p.id, p.tenant_id)
                        print(f"Purged: {p.name}")
                    except Exception as e:
                        print(f"Failed to purge {p.name}: {e}")
            else:
                print("No soft-deleted patients found to purge.")

            print("--- DIAGNOSTIC END ---")

        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(purge_deleted_patients())
