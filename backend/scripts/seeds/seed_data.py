"""
Seeding Script for Smart Clinic
Populates the database with realistic test data for multiple clinics.
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

# Force utf-8 for stdout if possible, though we will avoid non-ascii logs
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    except:
        pass

# Arabic Data Helpers (Kept for DB data only)
FIRST_NAMES = [
    "أحمد",
    "محمد",
    "محمود",
    "علي",
    "سارة",
    "منى",
    "نور",
    "ليلى",
    "خالد",
    "يوسف",
    "كريم",
    "هنا",
    "مريم",
    "عمر",
]
LAST_NAMES = [
    "علي",
    "إبراهيم",
    "حسن",
    "السيد",
    "محمد",
    "عبدالله",
    "عثمان",
    "كامل",
    "زكي",
    "راضي",
]
PROCEDURES = [
    ("كشف", 100),
    ("حشو عادي", 300),
    ("حشو عصب", 800),
    ("خلع بسيط", 200),
    ("خلع جراحي", 500),
    ("تنظيف جير", 250),
    ("تبييض أسنان", 1500),
    ("تركيبة زيركون", 1200),
    ("زراعة سن", 5000),
]
CLINICS = ["عيادة النخبة", "مركز الشفاء", "عيادة المستقبل"]


def get_random_date(days_back=90):
    """Get a random date within the last n days."""
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back))


def seed_data():
    db = SessionLocal()
    try:
        print("Starting seeding process...")

        tenants = []
        for i, clinic_name in enumerate(CLINICS):
            # 1. Create Tenant
            tenant = (
                db.query(models.Tenant)
                .filter(models.Tenant.name == clinic_name)
                .first()
            )
            if not tenant:
                tenant = models.Tenant(
                    name=clinic_name,
                    plan="premium",
                    subscription_end_date=datetime.utcnow() + timedelta(days=365),
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)
                print(f"Created Clinic ID: {tenant.id}")
            else:
                print(f"Clinic already exists ID: {tenant.id}")
            tenants.append(tenant)

            # 2. Create Doctors & Staff
            roles = [
                ("manager", "admin"),
                ("dr_ahmed", "doctor"),
                ("dr_sara", "doctor"),
                ("nurse", "assistant"),
                ("recep", "receptionist"),
            ]
            doctors = []

            for username_prefix, role in roles:
                username = f"{username_prefix}_{tenant.id}"
                user = (
                    db.query(models.User)
                    .filter(models.User.username == username)
                    .first()
                )
                if not user:
                    hashed_pw = auth.get_password_hash("123456")
                    user = models.User(
                        username=username,
                        hashed_password=hashed_pw,
                        role=role,
                        tenant_id=tenant.id,
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    print(f"   Created User: {username} ({role})")

                if role == "doctor":
                    doctors.append(user)

            # 3. Create Patients
            for i in range(10):  # 10 patients per clinic
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                patient = models.Patient(
                    name=name,
                    age=random.randint(5, 70),
                    phone=f"01{''.join([str(random.randint(0, 9)) for _ in range(9)])}",
                    address="القاهرة, مصر",
                    tenant_id=tenant.id,
                    notes="تمت الإضافة آلياً",
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

                # 4. Create Treatments & Payments
                # Ensure we have doctors to assign treatments to
                if not doctors:
                    continue

                for _ in range(random.randint(1, 5)):  # 1-5 treatments per patient
                    proc_name, proc_price = random.choice(PROCEDURES)
                    doctor = random.choice(doctors)

                    treatment_date = get_random_date()
                    treatment = models.Treatment(
                        patient_id=patient.id,
                        doctor_id=doctor.id,
                        procedure=proc_name,
                        cost=proc_price,
                        discount=0,
                        date=treatment_date,
                        tooth_number=random.randint(1, 32),
                        diagnosis="تسوس",
                        notes="Generated test data",
                    )
                    db.add(treatment)
                    db.commit()

                    # 70% chance to pay
                    if random.random() > 0.3:
                        payment = models.Payment(
                            patient_id=patient.id,
                            amount=proc_price,  # Full payment
                            date=treatment_date + timedelta(hours=1),
                            notes="دفع نقدي",
                        )
                        db.add(payment)
                        db.commit()

                print(f"   Created Patient ID: {patient.id} with treatments")

            # 5. Create Laboratories & Lab Orders
            LABS = ["معمل ألفا", "معمل النور", "معمل الدقة"]
            lab_objs = []
            for lab_name in LABS:
                lab = (
                    db.query(models.Laboratory)
                    .filter(
                        models.Laboratory.name == lab_name,
                        models.Laboratory.tenant_id == tenant.id,
                    )
                    .first()
                )
                if not lab:
                    lab = models.Laboratory(
                        name=lab_name,
                        phone=f"012{''.join([str(random.randint(0, 9)) for _ in range(8)])}",
                        address="وسط البلد",
                        tenant_id=tenant.id,
                    )
                    db.add(lab)
                    db.commit()
                    db.refresh(lab)
                    print(f"   Created Lab: {lab_name}")
                lab_objs.append(lab)

            # Assign random lab orders to some patients
            patients = (
                db.query(models.Patient)
                .filter(models.Patient.tenant_id == tenant.id)
                .all()
            )
            for patient in patients:
                if random.random() > 0.7:  # 30% of patients have lab work
                    lab = random.choice(lab_objs)
                    # Pick a random doctor from the clinic
                    doctor = random.choice(doctors) if doctors else None

                    lab_order = models.LabOrder(
                        patient_id=patient.id,
                        laboratory_id=lab.id,
                        doctor_id=doctor.id if doctor else None,
                        work_type=random.choice(
                            ["تركيبة بورسلين", "طقم كامل", "زيركون"]
                        ),
                        cost=random.randint(500, 2000),  # Lab cost
                        price_to_patient=random.randint(
                            1500, 4000
                        ),  # Price charged to patient
                        status="completed",
                        order_date=get_random_date(),
                        tenant_id=tenant.id,
                    )
                    db.add(lab_order)
                    db.commit()
                    print(
                        f"   Created Lab Order for Patient ID: {patient.id} - Cost: {lab_order.cost}"
                    )

        print("\nSeeding Completed Successfully!")
        print("------------------------------------------------")
        print("Login Credentials (Password: 123456):")
        for t in tenants:
            print(f"Clinic ID: {t.id}")
            print(f"  - Admin: manager_{t.id}")
            print(f"  - Doctor: dr_ahmed_{t.id}")
        print("------------------------------------------------")

    except Exception as e:
        print(f"Error seeding data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
