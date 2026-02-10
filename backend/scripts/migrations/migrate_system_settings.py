from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Production mode enforced.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)


def run_migration():
    print("Starting System Settings migration...")
    with engine.connect() as conn:
        try:
            print("Creating system_settings table...")
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key VARCHAR PRIMARY KEY,
                    value VARCHAR,
                    description VARCHAR,
                    updated_at DATETIME
                )
            """)
            )
            print(" - Created system_settings table")

            # Seed default settings
            conn.execute(
                text("""
                INSERT INTO system_settings (key, value, description, updated_at)
                VALUES 
                ('maintenance_mode', 'false', 'Enable maintenance mode to block non-admin logins', CURRENT_TIMESTAMP),
                ('global_announcement', '', 'Global banner text shown to all users', CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO NOTHING
            """)
            )
            print(" - Seeded default settings")

            conn.commit()
            print("Migration completed.")
        except Exception as e:
            print(f"Migration error: {e}")


if __name__ == "__main__":
    run_migration()
