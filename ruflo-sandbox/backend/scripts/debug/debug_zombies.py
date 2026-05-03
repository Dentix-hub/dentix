import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend import models


def check_zombie_tenants():
    db = SessionLocal()
    try:
        print("\n--- TENANT STATUS REPORT ---")
        print(
            f"{'ID':<5} | {'Name':<20} | {'Active?':<8} | {'Deleted?':<8} | {'Plan':<10}"
        )
        print("-" * 60)

        tenants = db.query(models.Tenant).all()
        for t in tenants:
            is_deleted = getattr(t, "is_deleted", "N/A")
            print(
                f"{t.id:<5} | {t.name[:20]:<20} | {str(t.is_active):<8} | {str(is_deleted):<8} | {t.plan}"
            )

        print("\n\n--- USER LOGIN CAPABILITY REPORT ---")
        print(
            f"{'User':<15} | {'Role':<10} | {'Tenant':<15} | {'Can Login?':<10} | {'Reason'}"
        )
        print("-" * 80)

        users = db.query(models.User).all()
        for u in users:
            can_login = "YES"
            reason = "OK"

            if u.role == "super_admin":
                reason = "Super Admin (Bypass)"
            elif not u.tenant:
                can_login = "??"
                reason = "No Tenant Linked"
            else:
                if getattr(u.tenant, "is_deleted", False):
                    can_login = "NO"
                    reason = "Tenant Deleted"
                elif not u.tenant.is_active:
                    can_login = "NO"
                    reason = "Tenant Inactive"

                # Check User status
                if hasattr(u, "is_active") and not u.is_active:
                    can_login = "NO"
                    reason = "User Inactive"

            print(
                f"{u.username:<15} | {u.role:<10} | {str(u.tenant.name if u.tenant else 'None'):<15} | {can_login:<10} | {reason}"
            )

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    check_zombie_tenants()
