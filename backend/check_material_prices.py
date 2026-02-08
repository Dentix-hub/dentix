from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.inventory import Material

def check_prices():
    db: Session = SessionLocal()
    try:
        materials = db.query(Material).all()
        print(f"{'ID':<5} {'Name':<30} {'Type':<15} {'Price':<10}")
        print("-" * 65)
        for m in materials:
            print(f"{m.id:<5} {m.name[:28]:<30} {m.type[:13]:<15} {m.standard_price}")
    finally:
        db.close()

if __name__ == "__main__":
    check_prices()
