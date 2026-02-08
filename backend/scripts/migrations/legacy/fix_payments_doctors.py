"""
Script to fix payments that don't have doctor_id assigned.
This will:
1. Find all payments without doctor_id
2. Assign them to the doctor from the patient's most recent treatment
3. Ensure tenant_id is set for all payments
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


def fix_payments_doctors():
    """Fix payments missing doctor_id and tenant_id."""
    db: Session = SessionLocal()
    
    try:
        # Check if doctor_id column exists in payments table and add if missing
        inspector = inspect(engine)
        try:
            columns = [col['name'] for col in inspector.get_columns('payments')]
            has_doctor_id = 'doctor_id' in columns
            has_tenant_id = 'tenant_id' in columns
        except Exception as e:
            print(f"[WARNING] Could not inspect payments table: {e}")
            has_doctor_id = False
            has_tenant_id = False
        
        if not has_doctor_id:
            print("[INFO] 'doctor_id' column doesn't exist in payments table.")
            print("   Adding doctor_id column to payments table...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE payments ADD COLUMN doctor_id INTEGER REFERENCES users(id)"))
                    conn.commit()
                print("   [OK] Added doctor_id column successfully!")
                has_doctor_id = True
            except Exception as e:
                print(f"   [ERROR] Error adding column: {e}")
                print("   [INFO] Continuing without doctor_id column...")
        
        if not has_tenant_id:
            print("[INFO] 'tenant_id' column doesn't exist in payments table.")
            print("   Adding tenant_id column to payments table...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE payments ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)"))
                    conn.commit()
                print("   [OK] Added tenant_id column successfully!")
                has_tenant_id = True
            except Exception as e:
                print(f"   [ERROR] Error adding column: {e}")
                print("   [INFO] Continuing without tenant_id column...")
        
        # 1. Get all payments without doctor_id
        payments_without_doctor = db.query(models.Payment).filter(
            or_(
                models.Payment.doctor_id.is_(None),
                models.Payment.doctor_id == 0
            )
        ).all()
        
        print(f"Found {len(payments_without_doctor)} payments without doctor_id")
        
        fixed_count = 0
        tenant_fixed_count = 0
        
        for payment in payments_without_doctor:
            # Get tenant_id from patient if missing
            tenant_id = None
            if has_tenant_id:
                tenant_id_value = getattr(payment, 'tenant_id', None)
                if tenant_id_value:
                    tenant_id = tenant_id_value
            
            if not tenant_id:
                patient = db.query(models.Patient).filter(
                    models.Patient.id == payment.patient_id
                ).first()
                if patient:
                    patient_tenant_id = getattr(patient, 'tenant_id', None)
                    if patient_tenant_id:
                        tenant_id = patient_tenant_id
                        if has_tenant_id:
                            payment.tenant_id = patient_tenant_id
                            tenant_fixed_count += 1
                    else:
                        print(f"[WARNING] Payment {payment.id} has no tenant_id and patient {patient.id} has no tenant_id. Skipping.")
                        continue
                else:
                    print(f"[WARNING] Payment {payment.id} references non-existent patient {payment.patient_id}. Skipping.")
                    continue
            
            # Find doctor from most recent treatment for this patient
            recent_treatment = db.query(models.Treatment).filter(
                models.Treatment.patient_id == payment.patient_id,
                models.Treatment.doctor_id.isnot(None)
            ).order_by(models.Treatment.date.desc()).first()
            
            if recent_treatment and recent_treatment.doctor_id:
                payment.doctor_id = recent_treatment.doctor_id
                fixed_count += 1
            else:
                # Try to find any doctor from tenant
                if tenant_id:
                    doctor = db.query(models.User).filter(
                        and_(
                            models.User.tenant_id == tenant_id,
                            models.User.role.in_(["doctor", "admin", "super_admin"])
                        )
                    ).first()
                    if doctor:
                        payment.doctor_id = doctor.id
                        fixed_count += 1
                        print(f"  Assigned payment {payment.id} to doctor {doctor.username} (from tenant default)")
                    else:
                        print(f"[WARNING] No doctor found for payment {payment.id}. Skipping.")
        
        # 3. Commit all changes
        if fixed_count > 0 or tenant_fixed_count > 0:
            db.commit()
            print(f"\n[OK] Fixed {fixed_count} payments with doctor_id")
            if tenant_fixed_count > 0:
                print(f"[OK] Fixed {tenant_fixed_count} payments with tenant_id")
            print(f"[OK] Total fixed: {fixed_count + tenant_fixed_count}")
        else:
            print("\n[OK] No payments needed fixing!")
        
        # 4. Show summary
        remaining = db.query(models.Payment).filter(
            or_(
                models.Payment.doctor_id.is_(None),
                models.Payment.doctor_id == 0
            )
        ).count()
        
        if remaining > 0:
            print(f"\n[WARNING] {remaining} payments still don't have doctor_id (likely patients without treatments)")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Payment Doctor Assignment Fix Script")
    print("=" * 60)
    print()
    fix_payments_doctors()
    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
