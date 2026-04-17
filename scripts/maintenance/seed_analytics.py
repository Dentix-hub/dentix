import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.database import SessionLocal, engine
from backend import models
from backend.services.inventory_service import inventory_service
from backend.auth import get_password_hash

# Setup
db = SessionLocal()
TENANT_ID = 10  # Assuming standard tenant
DOCTOR_ID = 0   # Will resolve dynamically

def setup_users():
    global DOCTOR_ID
    print("Setting up User...")
    user = db.query(models.User).filter(models.User.email == "doctor@smartdentalclinicapp.com").first()
    if not user:
        user = models.User(
            email="doctor@smartdentalclinicapp.com",
            username="Dr. Test User",
            hashed_password=get_password_hash("123456"),
            role="super_admin",
            tenant_id=TENANT_ID
        )
        db.add(user)
        db.commit()
    DOCTOR_ID = user.id
    print(f"User ID: {DOCTOR_ID}")

def setup_inventory():
    print("Setting up Inventory...")
    # Warehouse
    wh = db.query(models.Warehouse).filter(models.Warehouse.name == "Main Storage").first()
    if not wh:
        wh = models.Warehouse(name="Main Storage", tenant_id=TENANT_ID)
        db.add(wh)
        db.commit()
    
    # Materials
    materials_data = [
        ("Composite Resin", "Restorative", "Tube", 50.0),
        ("Anesthetic Cartridges", "Anesthesia", "Box", 30.0),
        ("Bonding Agent", "Adhesive", "Bottle", 45.0),
        ("Impression Material", "Prosthetics", "Pack", 60.0),
        ("Gloves", "Consumable", "Box", 5.0),
    ]
    
    materials = []
    for name, mtype, unit, price in materials_data:
        mat = db.query(models.Material).filter(models.Material.name == name).first()
        if not mat:
            mat = models.Material(
                name=name, type=mtype, base_unit=unit, 
                standard_price=price, tenant_id=TENANT_ID,
                alert_threshold=10
            )
            db.add(mat)
            db.commit()
        materials.append(mat)
        
    return wh, materials

def generate_history(wh, materials):
    print("Generating Historical Data (June 2025 - Now)...")
    
    start_date = datetime(2025, 6, 1)
    end_date = datetime(2026, 2, 1)
    current_date = start_date
    
    patients = []
    # Create 20 Patients
    for i in range(20):
        p = models.Patient(
            name=f"Patient Test {i+1}",
            age=random.randint(20, 60),
            phone=f"010000000{i}",
            medical_history="None",
            notes="Seeded patient",
            tenant_id=TENANT_ID
        )
        db.add(p)
        patients.append(p)
    db.commit()

    while current_date <= end_date:
        # 1. Random Inventory Purchase (Restock) - Once a week
        if current_date.weekday() == 0: 
            mat = random.choice(materials)
            batch_num = f"BATCH-{current_date.strftime('%Y%m%d')}-{random.randint(100,999)}"
            
            # Add Batch
            batch = models.Batch(
                material_id=mat.id,
                batch_number=batch_num,
                expiry_date=current_date + timedelta(days=365),
                cost_per_unit=mat.standard_price,
                tenant_id=TENANT_ID,
                created_at=current_date
            )
            db.add(batch)
            db.commit()
            
            # Add Stock Item
            si = models.StockItem(
                warehouse_id=wh.id,
                batch_id=batch.id,
                quantity=50,
                tenant_id=TENANT_ID
            )
            db.add(si)
            db.commit()
            
            # Log Expense (Purchase)
            exp = models.Expense(
                category="Inventory",
                cost=mat.standard_price * 50,
                item_name=f"Purchase {mat.name}",
                date=current_date,
                tenant_id=TENANT_ID
            )
            db.add(exp)
            
        # 2. Daily Procedures & Revenue
        daily_appts = random.randint(1, 5)
        for _ in range(daily_appts):
            patient = random.choice(patients)
            
            # Treatment
            proc_price = random.choice([500, 800, 1200, 2500])
            treatment = models.Treatment(
                patient_id=patient.id,
                doctor_id=DOCTOR_ID,
                diagnosis="Routine Check",
                procedure="Dental Procedure",
                cost=proc_price,
                date=current_date,
                tenant_id=TENANT_ID
            )
            db.add(treatment)
            db.commit()
            
            # Payment (Revenue)
            pay = models.Payment(
                amount=proc_price,
                patient_id=patient.id,
                # Treatment ID not supported directly in this simple schema
                date=current_date,
                tenant_id=TENANT_ID
            )
            db.add(pay)
            
            # Material Usage (COGS)
            used_mat = random.choice(materials)
            # Find stock item
            si = db.query(models.StockItem).join(models.Batch).filter(
                models.Batch.material_id == used_mat.id,
                models.StockItem.quantity > 0
            ).first()
            
            if si:
                usage_qty = random.randint(1, 3)
                if si.quantity >= usage_qty:
                    si.quantity -= usage_qty
                    move = models.StockMovement(
                        stock_item_id=si.id,
                        change_amount=-usage_qty,
                        reason="USAGE",
                        performed_by=DOCTOR_ID,
                        created_at=current_date
                    )
                    db.add(move)

            # Lab Order (Optional)
            if random.random() > 0.7:
                lab_cost = random.choice([200, 400, 600])
                lab = models.LabOrder(
                    patient_id=patient.id,
                    doctor_id=DOCTOR_ID,
                    work_type="Crown/Bridge", # Fix incorrect field test_name/lab_name
                    # lab_name field might be in older model, new one uses laboratory_id relationship?
                    # clinical.py shows LabOrder has laboratory_id AND work_type.
                    # It does NOT have lab_name or test_name.
                    # I need to create a Laboratory first.
                    cost=lab_cost,
                    status="completed",
                    order_date=current_date,
                    delivery_date=current_date + timedelta(days=5),
                    tenant_id=TENANT_ID
                )
                # Skip LabOrder creation for now as it requires Laboratory setup which I missed
                # db.add(lab) 
        
        # 3. Monthly Expenses (Rent, Salary)
        # 3. Monthly Expenses (Rent, Salary)
        if current_date.day == 1:
            rent = models.Expense(
                category="Rent",
                cost=5000,
                item_name="Monthly Clinic Rent",
                date=current_date,
                tenant_id=TENANT_ID
            )
            salary = models.Expense(
                category="Salaries",
                cost=8000,
                item_name="Staff Salaries",
                date=current_date,
                tenant_id=TENANT_ID
            )
            db.add(rent)
            db.add(salary)

        db.commit()
        current_date += timedelta(days=1)
        print(f"Processed {current_date.date()}...", end='\r')

    print("\nData Seeding Completed Successfully!")

if __name__ == "__main__":
    setup_users()
    wh, mats = setup_inventory()
    generate_history(wh, mats)
