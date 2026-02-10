import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend import database, models


def seed_support_settings():
    """
    Seed default support settings if they don't exist.
    """
    db = database.SessionLocal()
    try:
        print("[SEED] Checking Support Settings...")

        defaults = {
            "support_phone": "+20 120 130 1415",
            "support_whatsapp": "201201301415",
            "support_email": "support@smartclinic.com",
            "support_working_hours": "9:00 AM - 10:00 PM",
        }

        seeded_count = 0
        for key, value in defaults.items():
            existing = (
                db.query(models.SystemSetting)
                .filter(models.SystemSetting.key == key)
                .first()
            )
            if not existing:
                setting = models.SystemSetting(
                    key=key, value=value, description=f"Default {key.replace('_', ' ')}"
                )
                db.add(setting)
                seeded_count += 1
                print(f" - Added {key}")
            else:
                pass  # Already exists

        if seeded_count > 0:
            db.commit()
            print(f"[SEED] Successfully seeded {seeded_count} new settings.")
        else:
            print("[SEED] All support settings already exist.")

    except Exception as e:
        print(f"[ERROR] Failed to seed settings: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_support_settings()
