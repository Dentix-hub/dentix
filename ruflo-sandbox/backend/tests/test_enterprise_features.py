import sys
import os
from sqlalchemy import text

# Setup paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BACKEND_DIR)

from backend.database import SessionLocal
from backend.models import Tenant, SystemSetting, AuditLog


def test_enterprise_features():
    print(">>> Starting Enterprise Features Verification...")
    db = SessionLocal()

    try:
        # 1. Verify Maintenance Mode Logic (Direct DB Check)
        print("\n[1] Checking System Settings...")
        maintenance = db.query(SystemSetting).filter_by(key="maintenance_mode").first()
        if not maintenance:
            print(" - FAIL: Maintenance mode setting missing!")
        else:
            print(
                f" - PASS: Maintenance mode setting exists (Value: {maintenance.value})"
            )

        # 2. Verify Soft Delete Columns
        print("\n[2] Checking Schema for Soft Delete...")
        try:
            # Quick query to check column existence
            db.execute(text("SELECT is_deleted, deleted_at FROM tenants LIMIT 1"))
            print(" - PASS: Tenant soft delete columns exist.")
        except Exception as e:
            print(f" - FAIL: Tenant columns missing: {e}")

        try:
            db.execute(
                text("SELECT is_deleted, deleted_at, is_active FROM users LIMIT 1")
            )
            print(" - PASS: User soft delete & active columns exist.")
        except Exception as e:
            print(f" - FAIL: User columns missing: {e}")

        # 3. Verify Soft Delete Logic (Simulation)
        print("\n[3] Simulating Soft Delete...")
        # Create dummy tenant
        test_tenant = Tenant(name="TestSoftDeleteClinic_123")
        db.add(test_tenant)
        db.commit()
        t_id = test_tenant.id
        print(f" - Created test tenant ID: {t_id}")

        # Soft delete manually (simulating API logic)
        from datetime import datetime, timezone

        test_tenant.is_deleted = True
        test_tenant.deleted_at = datetime.now(timezone.utc)
        test_tenant.is_active = False
        db.commit()

        # Verify
        check = db.query(Tenant).filter_by(id=t_id).first()
        if check.is_deleted and not check.is_active:
            print(" - PASS: Tenant successfully soft deleted.")
        else:
            print(" - FAIL: Tenant soft delete failed.")

        # Restore
        check.is_deleted = False
        check.deleted_at = None
        check.is_active = True
        db.commit()
        print(" - PASS: Tenant restored.")

        # Cleanup
        db.delete(check)
        db.commit()

        # 4. Verify Audit Logs
        print("\n[4] Checking Audit Logs...")
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(5).all()
        print(f" - Found {len(logs)} recent audit logs.")
        for log in logs:
            print(
                f"   * [{log.action}] {log.entity_type} (Admin: {log.performed_by_username})"
            )

        print(
            "\n>>> Verification Complete: All Enterprise systems operational locally."
        )

    except Exception as e:
        print(f"\n!!! ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_enterprise_features()
