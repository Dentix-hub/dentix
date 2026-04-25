from sqlalchemy import create_engine, text
from backend.database import SQLALCHEMY_DATABASE_URL

def main():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        query = text("SELECT name, plan FROM tenants LIMIT 100;")
        result = conn.execute(query)
        for row in result.fetchmany(100):
            print({"name": row.name, "plan": row.plan})

if __name__ == "__main__":
    main()
