import sys
import os
import random
from datetime import datetime, timedelta

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from backend.database import SessionLocal
from backend import models
from passlib.context import CryptContext


# Init password context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def seed_data():
    db = SessionLocal()
    try:
        print("Starting seeding...")

        # 1. Create Tenant
        clinic_name = f"Test Clinic {random.randint(1000, 9999)}"
        tenant = models.Tenant(
            name=clinic_name,
            subscription_status="active",
            plan="enterprise",
            subscription_end_date=datetime.utcnow() + timedelta(days=365),
            is_active=True,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"Created Tenant: {tenant.name} (ID: {tenant.id})")

        # 2. Create Doctors
        doctors_data = [
            {"name": "Dr. Ahmed", "commission": 20.0, "salary": 5000.0, "fee": 50.0},
            {"name": "Dr. Sara", "commission": 30.0, "salary": 7000.0, "fee": 75.0},
            {"name": "Dr. Mohamed", "commission": 40.0, "salary": 9000.0, "fee": 100.0},
        ]

        created_doctors = []

        for dr in doctors_data:
            username = (
                f"{dr['name'].replace(' ', '_').lower()}_{random.randint(100, 999)}"
            )
            password = "password123"
            user = models.User(
                username=username,
                hashed_password=get_password_hash(password),
                role="doctor",
                tenant_id=tenant.id,
                commission_percent=dr["commission"],
                fixed_salary=dr["salary"],
                per_appointment_fee=dr["fee"],
                hire_date=datetime.utcnow().date(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_doctors.append(user)
            print(
                f"Created Doctor: {dr['name']} ({username}) - Commission: {dr['commission']}%"
            )

        # 3. Create Patients & Treatments & Payments
        procedures_list = [
            ("Cleaning", 300),
            ("Filling", 500),
            ("Root Canal", 1500),
            ("Extraction", 400),
            ("Crown", 2000),
            ("Whitening", 2500),
            ("Implant", 8000),
            ("Braces", 12000),
        ]

        for doctor in created_doctors:
            print(f"Generating data for {doctor.username}...")
            # Create 10-15 patients for each doctor
            num_patients = random.randint(10, 15)

            for i in range(num_patients):
                f"Patient {random.randint(1, 9999)} details"
                patient = models.Patient(
                    name=f"Patient_{doctor.id}_{i + 1}_{random.randint(100, 999)}",
                    age=random.randint(18, 70),
                    phone=f"010{random.randint(10000000, 99999999)}",
                    tenant_id=tenant.id,
                    notes=f"Created for doctor {doctor.username}",
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

                # Add 1-3 treatments
                num_treatments = random.randint(1, 3)
                for _ in range(num_treatments):
                    proc_name, proc_cost = random.choice(procedures_list)
                    # Add some randomness to cost
                    actual_cost = proc_cost + random.choice([-50, 0, 50, 100])
                    discount = random.choice([0, 0, 0, 100, 200])  # Occasional discount

                    tx_date = datetime.utcnow() - timedelta(days=random.randint(0, 30))

                    treatment = models.Treatment(
                        patient_id=patient.id,
                        doctor_id=doctor.id,
                        tenant_id=tenant.id,
                        procedure=proc_name,
                        cost=actual_cost,
                        discount=discount,
                        date=tx_date,
                        diagnosis="Test Diagnosis",
                        notes="Generated test data",
                    )
                    db.add(treatment)

                    # Add Payment (Doctor gets credited)
                    # Maybe full payment or partial
                    payment_amount = actual_cost - discount
                    if random.random() > 0.8:  # 20% chance of partial payment
                        payment_amount = payment_amount * 0.5

                    payment = models.Payment(
                        patient_id=patient.id,
                        doctor_id=doctor.id,
                        tenant_id=tenant.id,
                        amount=payment_amount,
                        date=tx_date,  # Same day payment
                        notes="Payment for " + proc_name,
                    )
                    db.add(payment)

                db.commit()

        print("Seeding completed successfully!")
        print("Login with any doctor username and password 'password123'")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
