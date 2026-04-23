
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from backend.models.user import User, Base
from backend.database import SQLALCHEMY_DATABASE_URL

# Test with SQLite in memory
engine = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

def test_arabic_username():
    print("Testing Arabic Username in SQLite...")
    username_in_db = "أحمد"
    # Create user
    user = User(username=username_in_db, email="test@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    # Test cases
    test_cases = [
        ("أحمد", "Exact match"),
        ("أحمد ", "Trailing space"),
        (" أحمد", "Leading space"),
        ("أَحْمَد", "With Tashkeel (Harakat)"),
        ("احمد", "Without Hamza"),
    ]

    for input_val, description in test_cases:
        # Search using the same logic as crud/auth.py
        result = session.query(User).filter(
            func.lower(User.username) == input_val.lower()
        ).first()

        status = "✅ Found" if result else "❌ Not Found"
        print(f"Input: '{input_val}' ({description}) -> {status}")

if __name__ == "__main__":
    test_arabic_username()
