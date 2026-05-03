
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.getcwd())

from backend.database import SQLALCHEMY_DATABASE_URL
from backend.models.clinical import Appointment
from backend.models.patient import Patient

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    orphans = db.query(Appointment).outerjoin(Patient).filter(Patient.id == None).all()
    print(f"Found {len(orphans)} orphaned appointments.")
    for appt in orphans:
        print(f"Appointment ID: {appt.id}, Patient ID: {appt.patient_id}")
finally:
    db.close()
