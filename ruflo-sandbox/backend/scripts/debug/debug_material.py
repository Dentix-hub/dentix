import sys
import os

sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models.inventory import Material

db = SessionLocal()
mat = db.query(Material).get(8)  # ID 8 from previous output
print(
    f"ID: {mat.id}, Name: {mat.name}, Unit: {mat.base_unit}, Ratio: {mat.packaging_ratio}"
)
