from sqlalchemy import create_engine, text
from backend.database import SQLALCHEMY_DATABASE_URL

def main():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        query = text("SELECT message, stack_trace, path FROM system_errors ORDER BY created_at DESC LIMIT 5;")
        rows = conn.execute(query).fetchall()
        for row in rows:
            print("-" * 50)
            data = dict(row._mapping)
            print(f"PATH: {data.get('path')}")
            print(f"MESSAGE: {data.get('message')}")
            print(f"STACK TRACE:\n{data.get('stack_trace')}")

if __name__ == "__main__":
    main()
