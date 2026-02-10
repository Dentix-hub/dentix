import sys
import os
from sqlalchemy import create_engine, text

# Setup paths
sys.path.append(os.getcwd())

from backend.database import SQLALCHEMY_DATABASE_URL


def migrate_security_phase4():
    print(">>> Applying Phase 4 Security Migration (User Sessions)...")

    engine = create_engine(SQLALCHEMY_DATABASE_URL)

    with engine.connect() as conn:
        try:
            # 1. Create user_sessions
            print("Creating 'user_sessions' table...")
            conn.execute(
                text("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token_hash VARCHAR,
                ip_address VARCHAR,
                user_agent VARCHAR,
                device_info VARCHAR,
                last_active_at DATETIME,
                expires_at DATETIME,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """)
            )

            # 2. Create login_history
            print("Creating 'login_history' table...")
            conn.execute(
                text("""
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ip_address VARCHAR,
                user_agent VARCHAR,
                status VARCHAR,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """)
            )

            # 3. Create blocked_ips
            print("Creating 'blocked_ips' table...")
            conn.execute(
                text("""
            CREATE TABLE IF NOT EXISTS blocked_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address VARCHAR UNIQUE,
                reason VARCHAR,
                blocked_by VARCHAR,
                blocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME
            )
            """)
            )

            # 4. Add Columns to Users
            print("Adding columns to 'users' table...")
            # SQLite does not support IF NOT EXISTS for columns in older versions, so we use try/catch block approach or simple separate statements
            # We'll try to add them one by one. If they exist, it will fail harmlessly (if we catch it) or we can check pragma.
            # Simplified approach: catch error per column.

            columns = [
                ("failed_login_attempts", "INTEGER DEFAULT 0"),
                ("last_failed_login", "DATETIME"),
                ("account_locked_until", "DATETIME"),
                ("is_2fa_enabled", "BOOLEAN DEFAULT 0"),
                ("otp_secret", "VARCHAR"),
            ]

            for col_name, col_type in columns:
                try:
                    conn.execute(
                        text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    )
                    print(f"Added column {col_name}")
                except Exception as e:
                    print(f"Column {col_name} might already exist or failed: {e}")

            # Create Indexes
            print("Creating indexes...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions (user_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_user_sessions_token_hash ON user_sessions (token_hash)"
                )
            )

            conn.commit()
            print("Migration Phase 4 Successful!")
        except Exception as e:
            print(f"Migration Failed: {e}")


if __name__ == "__main__":
    migrate_security_phase4()
