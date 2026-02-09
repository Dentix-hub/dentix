import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import sys

# Adjust path to find backend module
sys.path.append(os.getcwd())

from backend.database import SQLALCHEMY_DATABASE_URL

print(f"Testing connection to: {SQLALCHEMY_DATABASE_URL}")

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print(f"Connection successful: {result.fetchone()}")
        
        # Try a table query
        result = connection.execute(text("SELECT count(*) FROM users"))
        print(f"Users count: {result.fetchone()[0]}")
        
except Exception as e:
    print(f"DB Error: {e}")
