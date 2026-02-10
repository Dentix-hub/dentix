import sys
import os
from sqlalchemy import create_engine, text

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.append(project_root)


def check_db(file_path):
    if not os.path.exists(file_path):
        return

    url = f"sqlite:///{file_path}"
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            # Check if tables exist
            tables = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table';")
            ).fetchall()
            table_names = [t[0] for t in tables]

            if "patients" not in table_names:
                print(f"[EMPTY SCHEMA] {file_path}")
                return

            # Count patients
            total_patients = conn.execute(
                text("SELECT count(*) FROM patients")
            ).scalar()
            deleted_patients = conn.execute(
                text("SELECT count(*) FROM patients WHERE is_deleted=1")
            ).scalar()

            # Count users
            total_users = 0
            if "users" in table_names:
                total_users = conn.execute(text("SELECT count(*) FROM users")).scalar()

            print(f"[FOUND] {file_path}")
            print(f"   - Users: {total_users}")
            print(f"   - Patients: {total_patients} (Deleted: {deleted_patients})")
            print("-" * 30)

    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")


def main():
    print("Scanning database files for activity...")
    candidates = [
        os.path.join(project_root, "clinic.db"),
        os.path.join(backend_dir, "clinic.db"),
    ]

    for db_path in candidates:
        check_db(db_path)


if __name__ == "__main__":
    main()
