from sqlalchemy import create_engine, text
from backend.database import SQLALCHEMY_DATABASE_URL
from datetime import datetime

def main():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        query = text("SELECT created_at, message, path FROM system_errors ORDER BY created_at DESC LIMIT 10;")
        rows = conn.execute(query).fetchall()
        for row in rows:
            print("-" * 50)
            data = dict(row._mapping)
            print(f"TIME: {data.get('created_at')}")
            print(f"PATH: {data.get('path')}")
            print(f"MESSAGE: {data.get('message')}")

if __name__ == "__main__":
    main()
