"""
Script to fix treatments that don't have doctor_id assigned.
This will:
1. Find all treatments without doctor_id
2. Assign them to the first available doctor in the same tenant
3. Ensure tenant_id is set for all treatments (adds column if missing)
"""

import sys
import os

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, inspect, text

try:
    from backend.database import SessionLocal, engine
    from backend import models
except ImportError:
    # Try alternative import path
    from database import SessionLocal, engine
    import models


def fix_treatments_doctors():
    """Fix treatments missing doctor_id and tenant_id."""
    db: Session = SessionLocal()

    try:
        # Check if tenant_id column exists in treatments table and add if missing
        inspector = inspect(engine)
        try:
            columns = [col["name"] for col in inspector.get_columns("treatments")]
            has_tenant_id = "tenant_id" in columns
        except Exception as e:
            print(f"[WARNING] Could not inspect treatments table: {e}")
            has_tenant_id = False

        if not has_tenant_id:
            print("[INFO] 'tenant_id' column doesn't exist in treatments table.")
            print("   Adding tenant_id column to treatments table...")
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text("ALTER TABLE treatments ADD COLUMN tenant_id INTEGER")
                    )
                    conn.commit()
                print("   [OK] Added tenant_id column successfully!")
                has_tenant_id = True
            except Exception as e:
                print(f"   [ERROR] Error adding column: {e}")
                # Try to continue - maybe SQLite doesn't support ALTER TABLE ADD COLUMN
                print("   [INFO] Continuing without tenant_id column...")

        # 1. Get all treatments without doctor_id
        treatments_without_doctor = (
            db.query(models.Treatment)
            .filter(
                or_(
                    models.Treatment.doctor_id.is_(None),
                    models.Treatment.doctor_id == 0,
                )
            )
            .all()
        )

        print(f"Found {len(treatments_without_doctor)} treatments without doctor_id")

        # 2. Group by tenant_id to assign doctors efficiently
        tenant_doctor_map = {}  # {tenant_id: doctor_id}
        fixed_count = 0
        tenant_fixed_count = 0

        for treatment in treatments_without_doctor:
            tenant_id = None

            # Get tenant_id from treatment or patient if missing
            if has_tenant_id:
                tenant_id_value = getattr(treatment, "tenant_id", None)
                if tenant_id_value:
                    tenant_id = tenant_id_value

            # If still no tenant_id, get from patient
            if not tenant_id:
                patient = (
                    db.query(models.Patient)
                    .filter(models.Patient.id == treatment.patient_id)
                    .first()
                )
                if patient:
                    patient_tenant_id = getattr(patient, "tenant_id", None)
                    if patient_tenant_id:
                        tenant_id = patient_tenant_id
                        # Update treatment.tenant_id if column exists
                        if has_tenant_id:
                            treatment.tenant_id = patient_tenant_id
                            tenant_fixed_count += 1
                    else:
                        print(
                            f"[WARNING] Treatment {treatment.id} has no tenant_id and patient {patient.id} has no tenant_id. Skipping."
                        )
                        continue
                else:
                    print(
                        f"[WARNING] Treatment {treatment.id} references non-existent patient {treatment.patient_id}. Skipping."
                    )
                    continue

            # Find a doctor for this tenant (cache result)
            if tenant_id not in tenant_doctor_map:
                # Get first available doctor/admin in this tenant
                doctor = (
                    db.query(models.User)
                    .filter(
                        and_(
                            models.User.tenant_id == tenant_id,
                            models.User.role.in_(["doctor", "admin", "super_admin"]),
                        )
                    )
                    .first()
                )

                if doctor:
                    tenant_doctor_map[tenant_id] = doctor.id
                    print(
                        f"  Assigning treatments for tenant {tenant_id} to doctor: {doctor.username} (ID: {doctor.id})"
                    )
                else:
                    # If no doctor found, skip
                    print(
                        f"  [WARNING] No doctor found for tenant {tenant_id}. Skipping treatments for this tenant."
                    )
                    tenant_doctor_map[tenant_id] = None
                    continue

            # Assign doctor_id
            if tenant_doctor_map[tenant_id]:
                treatment.doctor_id = tenant_doctor_map[tenant_id]
                fixed_count += 1

        # 3. Commit all changes
        if fixed_count > 0 or tenant_fixed_count > 0:
            db.commit()
            print(f"\n[OK] Fixed {fixed_count} treatments with doctor_id")
            if tenant_fixed_count > 0:
                print(f"[OK] Fixed {tenant_fixed_count} treatments with tenant_id")
            print(f"[OK] Total fixed: {fixed_count + tenant_fixed_count}")
        else:
            print("\n[OK] No treatments needed fixing!")

        # 4. Show summary
        remaining = (
            db.query(models.Treatment)
            .filter(
                or_(
                    models.Treatment.doctor_id.is_(None),
                    models.Treatment.doctor_id == 0,
                )
            )
            .count()
        )

        if remaining > 0:
            print(
                f"\n[WARNING] {remaining} treatments still don't have doctor_id (likely tenants without doctors)"
            )

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        db.rollback()
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Treatment Doctor Assignment Fix Script")
    print("=" * 60)
    print()
    fix_treatments_doctors()
    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
