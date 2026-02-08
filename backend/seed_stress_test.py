"""
Seeding Script for Stress Testing (k6)
Populates the database with high volume data:
- 8 Clinics
- 30 Doctors
- ~960 Patients (120 per clinic)
- Historical Appointments & Treatments
"""
import sys
import os
import random
import codecs
from datetime import datetime, timedelta

# Add project root to path (parent of backend)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend import models, auth

# Force utf-8 for stdout if possible
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    except:
        pass

# Constants
CLINIC_COUNT = 20
DOCTORS_TOTAL = 100
PATIENTS_PER_CLINIC = 500

FIRST_NAMES = ["Ahmed", "Mohamed", "Mahmoud", "Ali", "Sara", "Mona", "Nour", "Laila", "Khaled", "Youssef", "Karim", "Hana", "Mariam", "Omar"]
LAST_NAMES = ["Ali", "Ibrahim", "Hassan", "Elsayed", "Mohamed", "Abdullah", "Osman", "Kamel", "Zaki", "Rady"]

PROCEDURES = [
    ("Checkup", 100),
    ("Filling", 300),
    ("Root Canal", 800),
    ("Extraction", 200),
    ("Cleaning", 250),
    ("Whitening", 1500)
]

def get_random_date(days_back=365):
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back))

def seed_stress_data():
    db = SessionLocal()
    try:
        print(f"🚀 Starting STRESS TEST Seeding...")
        print(f"Targets: {CLINIC_COUNT} Clinics, {DOCTORS_TOTAL} Doctors, {CLINIC_COUNT * PATIENTS_PER_CLINIC} Patients")

        tenants = []
        doctors_created = 0

        # 1. Create 8 Clinics (Tenants)
        for i in range(1, CLINIC_COUNT + 1):
            clinic_name = f"Stress Clinic {i}"
            tenant = db.query(models.Tenant).filter(models.Tenant.name == clinic_name).first()
            if not tenant:
                tenant = models.Tenant(
                    name=clinic_name,
                    plan="enterprise",
                    subscription_end_date=datetime.utcnow() + timedelta(days=365)
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)
                print(f"✅ Created Clinic: {clinic_name} (ID: {tenant.id})")
            else:
                print(f"ℹ️ Clinic exists: {clinic_name} (ID: {tenant.id})")
            
            tenants.append(tenant)

            # 2. Create Admin for Clinic
            admin_username = f"admin_stress_{tenant.id}"
            if not db.query(models.User).filter(models.User.username == admin_username).first():
                user = models.User(
                    username=admin_username,
                    hashed_password=auth.get_password_hash("123456"),
                    role="manager",
                    tenant_id=tenant.id
                )
                db.add(user)
                db.commit()

            # 3. Create Doctors (Distribute 30 doctors across 8 clinics ~ 3-4 per clinic)
            # We want exactly 30 total, so let's just add 3-4 per clinic
            doctors_for_this_clinic = []
            target_docs = 4 if i <= 6 else 3 # 6*4 + 2*3 = 24+6 = 30. Correct.
            
            for d in range(target_docs):
                doc_username = f"dr_stress_{tenant.id}_{d+1}"
                doctor = db.query(models.User).filter(models.User.username == doc_username).first()
                if not doctor:
                    doctor = models.User(
                        username=doc_username,
                        hashed_password=auth.get_password_hash("123456"),
                        role="doctor",
                        tenant_id=tenant.id
                    )
                    db.add(doctor)
                    db.commit()
                    db.refresh(doctor)
                    doctors_created += 1
                doctors_for_this_clinic.append(doctor)
            
            print(f"   - assigned {len(doctors_for_this_clinic)} doctors")

            # 4. Create Patients & Medical History
            print(f"   - seeding {PATIENTS_PER_CLINIC} patients...")
            
            # Batch size for commits to avoid memory issues
            batch_size = 50
            patients_buffer = []
            
            for p in range(PATIENTS_PER_CLINIC):
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} {random.randint(1,9999)}"
                patient = models.Patient(
                    name=name,
                    age=random.randint(10, 80),
                    phone=f"01{random.randint(100000000, 999999999)}",
                    address="Cairo, stress test st.",
                    tenant_id=tenant.id,
                    notes="Stress Test User"
                )
                db.add(patient)
                # Flush to get ID
                db.flush() 
                db.refresh(patient)

                # Add some history (Treatments/Appointments)
                if doctors_for_this_clinic:
                    doc = random.choice(doctors_for_this_clinic)
                    
                    # 1-3 Past Appointments
                    for _ in range(random.randint(1, 3)):
                        appt_date = get_random_date()
                        appt = models.Appointment(
                            patient_id=patient.id,
                            doctor_id=doc.id,
                            # title="Checkup", # Removed - not in model
                            date_time=appt_date, # Changed from start_time
                            # end_time=appt_date + timedelta(minutes=30), # Removed - check model
                            status="completed",
                            notes="Checkup", # Added notes instead of title
                            # tenant_id=tenant.id # Removed - not in model based on inspection, wait, let me check clinical.py again. 
                            # clinical.py line 4: class Appointment(Base)... 
                            # It DOES NOT have tenant_id in the snippet I saw! 
                            # It has patient, doctor, price_list, date_time, status, notes, is_deleted, deleted_at.
                            # references relationships.
                        )
                        db.add(appt)

                    # 1-5 Treatments
                    for _ in range(random.randint(1, 5)):
                        proc, cost = random.choice(PROCEDURES)
                        treat_date = get_random_date()
                        treatment = models.Treatment(
                            patient_id=patient.id,
                            doctor_id=doc.id,
                            procedure=proc,
                            cost=cost,
                            date=treat_date,
                            # status="completed", # Removed - not in model
                            diagnosis="Stress Test Diagnosis"
                        )
                        db.add(treatment)

                if p > 0 and p % batch_size == 0:
                    db.commit()
            
            db.commit() # Final commit for clinic
            print(f"   ✅ Clinic {tenant.id} seeded.")

        print("\n------------------------------------------------")
        print(f"🎉 Seeding Complete!")
        print(f"Total Clinics: {len(tenants)}")
        print(f"Total Doctors: {doctors_created}")
        print(f"Total Patients: ~{CLINIC_COUNT * PATIENTS_PER_CLINIC}")
        print("------------------------------------------------")

    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_stress_data()
