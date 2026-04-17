import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from backend.models.base import Base
from backend.models import clinical, patient, inventory, financial, user, tenant
from backend.services.inventory_learning_service import InventoryLearningService
from backend.auth import get_password_hash

# Configuration
DB_URL = "sqlite:///./clinic.db"
TENANT_ID = 1
START_DATE = datetime.now() - timedelta(days=90)

# Connect
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def log(msg):
    print(f"[SEED] {msg}")

def safe_commit():
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")

# --- 0. CLEAN SLATE (Transactional Data Only) ---
log("Cleaning old transactional data...")
# Delete in specific order to avoid FK constraints
db.query(financial.Payment).delete()
db.query(clinical.LabOrder).delete()
db.query(clinical.Treatment).delete()
db.query(clinical.Appointment).delete()
db.query(inventory.MaterialLearningLog).delete()
db.query(inventory.MaterialSession).delete()
# We don't delete StockItems/Batches to avoid complex inventory resets, 
# assuming previous run stock is fine or we just add to it.
safe_commit()


# --- 1. Check User & Tenant ---
log("Checking User & Tenant...")
tenant_obj = db.query(tenant.Tenant).filter_by(id=TENANT_ID).first()
if not tenant_obj:
    tenant_obj = tenant.Tenant(id=TENANT_ID, name="Dentix Demo", plan="PRO")
    db.add(tenant_obj)
    safe_commit()

doctor = db.query(user.User).filter(user.User.email == "doctor@smartdentalclinicapp.com").first()
if not doctor:
    doctor = user.User(
        email="doctor@smartdentalclinicapp.com",
        username="Dr. Dentix",
        hashed_password=get_password_hash("123456"),
        role="doctor",
        tenant_id=TENANT_ID,
        is_active=True
    )
    db.add(doctor)
    safe_commit()
    doctor = db.query(user.User).filter(user.User.email == "doctor@smartdentalclinicapp.com").first()

log(f"Doctor ID: {doctor.id}")

# --- 2. Create Laboratories ---
log("Creating Laboratories...")
labs = []
lab_names = [
    {"name": "Alpha Dental Lab", "specialties": "Crowns, Bridges"},
    {"name": "Future Smile Lab", "specialties": "Dentures, Ortho"}
]
for l_data in lab_names:
    lab = db.query(clinical.Laboratory).filter_by(name=l_data["name"]).first()
    if not lab:
        lab = clinical.Laboratory(
            name=l_data["name"], 
            phone=f"010{random.randint(10000000, 99999999)}",
            contact_person="Lab Manager",
            specialties=l_data["specialties"],
            tenant_id=TENANT_ID
        )
        db.add(lab)
        safe_commit()
        db.refresh(lab)
    labs.append(lab)


# --- 3. Create Procedures & Pricing ---
log("Creating Procedures...")
procedures_data = [
    {"name": "Restoration Class I", "price": 500.0, "weight_score": 1.0, "real_usage_g": 0.2, "real_usage_ml": 0.05},
    {"name": "Restoration Class II", "price": 750.0, "weight_score": 1.5, "real_usage_g": 0.35, "real_usage_ml": 0.08},
    {"name": "Post RCT Filling", "price": 1200.0, "weight_score": 2.0, "real_usage_g": 0.5, "real_usage_ml": 0.1},
    {"name": "Build up", "price": 900.0, "weight_score": 3.0, "real_usage_g": 0.8, "real_usage_ml": 0.15},
    {"name": "Extraction Simple", "price": 300.0, "weight_score": 0, "real_usage_g": 0, "real_usage_ml": 0},
    {"name": "Root Canal Treatment", "price": 1500.0, "weight_score": 0, "real_usage_g": 0, "real_usage_ml": 0},
    # Lab Procedures
    {"name": "PFM Crown", "price": 2000.0, "weight_score": 0, "real_usage_g": 0, "real_usage_ml": 0, "is_lab": True, "lab_cost": 800.0},
    {"name": "Zirconia Crown", "price": 3500.0, "weight_score": 0, "real_usage_g": 0, "real_usage_ml": 0, "is_lab": True, "lab_cost": 1500.0},
    {"name": "Acrylic Denture", "price": 4000.0, "weight_score": 0, "real_usage_g": 0, "real_usage_ml": 0, "is_lab": True, "lab_cost": 1200.0},
]

proc_map = {}
for p_data in procedures_data:
    proc = db.query(clinical.Procedure).filter_by(name=p_data["name"]).first()
    if not proc:
        proc = clinical.Procedure(name=p_data["name"], price=p_data["price"], tenant_id=TENANT_ID)
        db.add(proc)
        safe_commit()
        db.refresh(proc)
    proc_map[p_data["name"]] = proc

# --- 4. Create Materials & Batches ---
log("Creating Materials...")
# Materials
composite = db.query(inventory.Material).filter_by(name="Composite A2").first()
if not composite:
    composite = inventory.Material(
        name="Composite A2", type="DIVISIBLE", base_unit="g", 
        packaging_ratio=4.0, alert_threshold=5, tenant_id=TENANT_ID
    )
    db.add(composite)
    safe_commit()

bond = db.query(inventory.Material).filter_by(name="Bond 3M").first()
if not bond:
    bond = inventory.Material(
        name="Bond 3M", type="DIVISIBLE", base_unit="ml", 
        packaging_ratio=5.0, alert_threshold=1, tenant_id=TENANT_ID
    )
    db.add(bond)
    safe_commit()

# Batches & Stock
warehouse = db.query(inventory.Warehouse).filter_by(tenant_id=TENANT_ID).first()
if not warehouse:
    warehouse = inventory.Warehouse(name="Main Clinic Store", tenant_id=TENANT_ID)
    db.add(warehouse)
    safe_commit()

def ensure_stock(material, qty, cost_unit, supplier):
    batch = db.query(inventory.Batch).filter_by(batch_number=f"BATCH-{material.id}-INIT").first()
    if not batch:
        batch = inventory.Batch(
            material_id=material.id, tenant_id=TENANT_ID,
            batch_number=f"BATCH-{material.id}-INIT",
            expiry_date=datetime.now() + timedelta(days=365),
            supplier=supplier, cost_per_unit=cost_unit
        )
        db.add(batch)
        safe_commit()
    
    stock = db.query(inventory.StockItem).filter_by(batch_id=batch.id).first()
    if not stock:
        stock = inventory.StockItem(
            warehouse_id=warehouse.id, batch_id=batch.id, tenant_id=TENANT_ID,
            quantity=qty
        )
        db.add(stock)
        safe_commit()
    return stock

comp_stock = ensure_stock(composite, 50.0, 150.0, "Dental Supplier Co") # Increased stock
bond_stock = ensure_stock(bond, 20.0, 200.0, "3M Distributor")

# Link Procedures to Materials (Planner Weights)
log("Linking Weights...")
for p_data in procedures_data:
    if p_data["weight_score"] > 0:
        proc = proc_map[p_data["name"]]
        
        # Link Composite
        link_c = db.query(inventory.ProcedureMaterialWeight).filter_by(procedure_id=proc.id, material_id=composite.id).first()
        if not link_c:
            link_c = inventory.ProcedureMaterialWeight(
                procedure_id=proc.id, material_id=composite.id, tenant_id=TENANT_ID,
                weight=p_data["weight_score"]
            )
            db.add(link_c)
        
        # Link Bond
        link_b = db.query(inventory.ProcedureMaterialWeight).filter_by(procedure_id=proc.id, material_id=bond.id).first()
        if not link_b:
            link_b = inventory.ProcedureMaterialWeight(
                procedure_id=proc.id, material_id=bond.id, tenant_id=TENANT_ID,
                weight=p_data["weight_score"]
            )
            db.add(link_b)
safe_commit()

# --- 5. Create Patients ---
log("Creating Patients...")
first_names = ["Ahmed", "Mohamed", "Sara", "Noura", "Ali", "Omar", "Laila", "Khaled", "Mona", "Youssef"]
last_names = ["Hassan", "Ibrahim", "Ali", "Mahmoud", "Saeed", "Kamel", "Fawzy", "Nasser"]

patients = []
for i in range(30):
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    pat = db.query(patient.Patient).filter(patient.Patient.name == name).first()
    if not pat:
        pat = patient.Patient(
            name=name, age=random.randint(18, 70), 
            phone=f"010{random.randint(10000000, 99999999)}",
            tenant_id=TENANT_ID, assigned_doctor_id=doctor.id
        )
        db.add(pat)
        safe_commit()
        db.refresh(pat)
    patients.append(pat)

# --- 6. Simulate Timeline (Treatments, Labs, Inventory) ---
log("Simulating 3 Months of Activity with Lab Orders...")
learning_service = InventoryLearningService(db)

current_date = START_DATE
session_comp = None
session_bond = None

while current_date < datetime.now():
    # 3-6 treatments per day
    daily_treatments = random.randint(3, 6)
    day_treatments_real_usage_comp = 0.0
    day_treatments_real_usage_bond = 0.0
    
    for _ in range(daily_treatments):
        pat = random.choice(patients)
        proc_data = random.choice(procedures_data)
        
        # Create Appointment
        appt_args = {
            "patient_id": pat.id, 
            "doctor_id": doctor.id, 
            "date_time": current_date + timedelta(hours=random.randint(9, 17)),
            "status": "Completed"
        }
        if hasattr(clinical.Appointment, 'tenant_id'):
            appt_args["tenant_id"] = TENANT_ID
            
        appt = clinical.Appointment(**appt_args)
        db.add(appt)
        safe_commit()
        
        # Create Treatment
        tret = clinical.Treatment(
            patient_id=pat.id, doctor_id=doctor.id,
            procedure=proc_data["name"],
            cost=proc_data["price"],
            date=current_date, 
            tenant_id=TENANT_ID
        )
        db.add(tret)
        
        # Add Payment
        pay = financial.Payment(
            patient_id=pat.id, doctor_id=doctor.id,
            amount=proc_data["price"], date=current_date, tenant_id=TENANT_ID
        )
        db.add(pay)
        
        # LAB ORDER LOGIC
        if proc_data.get("is_lab"):
            lab = random.choice(labs)
            lab_order = clinical.LabOrder(
                patient_id=pat.id,
                laboratory_id=lab.id,
                doctor_id=doctor.id,
                work_type=proc_data["name"],
                price_to_patient=proc_data["price"],
                cost=proc_data.get("lab_cost", 500.0),
                status="received", # Mark as completed
                order_date=current_date,
                received_date=current_date + timedelta(days=5),
                tenant_id=TENANT_ID,
                tooth_number=str(random.randint(11, 48))
            )
            db.add(lab_order)
            log(f"Added Lab Order: {proc_data['name']} for {pat.name} at {lab.name}")

        # Inventory Consumption
        if proc_data.get("weight_score", 0) > 0:
            day_treatments_real_usage_comp += proc_data["real_usage_g"]
            day_treatments_real_usage_bond += proc_data["real_usage_ml"]
            
    safe_commit()

    # Inventory Cycle: Close and Re-open sessions every 7 days
    if current_date.weekday() == 6: # Sunday
        # Composite Session
        c_sess = inventory.MaterialSession(
            stock_item_id=comp_stock.id,
            opened_at=current_date - timedelta(days=6),
            status="ACTIVE", doctor_id=doctor.id
        )
        db.add(c_sess)
        safe_commit()
        
        learning_service.close_session(c_sess.id, total_consumed=day_treatments_real_usage_comp * 7 * random.uniform(0.9, 1.1), user_id=doctor.id)
        
        # Bond Session
        b_sess = inventory.MaterialSession(
            stock_item_id=bond_stock.id,
            opened_at=current_date - timedelta(days=6),
            status="ACTIVE", doctor_id=doctor.id
        )
        db.add(b_sess)
        safe_commit()
        learning_service.close_session(b_sess.id, total_consumed=day_treatments_real_usage_bond * 7 * random.uniform(0.9, 1.1), user_id=doctor.id)
        
        log(f"Week ending {current_date.date()}: Closed AI Sessions.")

    current_date += timedelta(days=1)

log("Seeding with Lab Data Completed Successfully!")
