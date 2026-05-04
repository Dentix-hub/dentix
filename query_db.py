import sys
from sqlalchemy import create_engine, text
from backend.database import SQLALCHEMY_DATABASE_URL

def main():
    if len(sys.argv) < 2:
        print("Usage: python query_db.py \"SELECT ...\"")
        return

    query_str = sys.argv[1]
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        query = text(query_str)
        result = conn.execute(query)
        if result.returns_rows:
            rows = result.fetchall()
            for row in rows:
                print(dict(row._mapping))
        else:
            conn.commit()
            print("Query executed successfully (no rows returned)")

if __name__ == "__main__":
    main()
