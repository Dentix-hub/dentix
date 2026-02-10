"""
STAGING RESET SCRIPT
DANGER: This script wipes the entire database and reseeds only essential system data.
Use this to prepare the system for a fresh staging deployment.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import database, models
from backend.core import seeding


def reset_database():
    print("⚠️  [DANGER] STARTING DATABASE RESET FOR STAGING...")
    print("    This will DELETE ALL CLINICS, PATIENTS, and USERS.")

    # confirmation = input("Type 'CONFIRM_RESET' to proceed: ")
    # if confirmation != "CONFIRM_RESET":
    #     print("❌ Aborted.")
    #     return

    try:
        # 1. Drop All Tables
        print("🗑️  Dropping all tables...")
        models.Base.metadata.drop_all(bind=database.engine)

        # 2. Create All Tables
        print("🏗️  Creating fresh schema...")
        models.Base.metadata.create_all(bind=database.engine)

        # 3. Seed Essential Data Only
        print("🌱 Seeding essential system data...")

        # Subscription Plans
        seeding.seed_subscription_plans()

        # Super Admin Only
        seeding.create_first_admin()

        print("✅ [SUCCESS] Staging Reset Complete.")
        print("   - All old clinics deleted.")
        print("   - System Admin created.")
        print("   - Subscription Plans active.")

    except Exception as e:
        print(f"❌ [ERROR] Reset failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reset_database()
