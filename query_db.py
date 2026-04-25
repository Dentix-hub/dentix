from sqlalchemy import create_engine, text
from backend.database import SQLALCHEMY_DATABASE_URL

def main():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        query = text("SELECT name, logo, plan FROM tenants;")
        rows = conn.execute(query).fetchall()
        for row in rows:
            print(dict(row._mapping))

if __name__ == "__main__":
    main()
