import sys
import os

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import SessionLocal
from backend.models.clinical import Procedure

PROCEDURES_LIST = [
    "حشو كومبوزيت -- Composite Filling Class I",
    "حشو كومبوزيت -- Composite Filling Class II",
    "حشو كومبوزيت -- Composite Filling Class III",
    "حشو كومبوزيت -- Composite Filling Class IV",
    "حشو كومبوزيت -- Composite Filling Class V",
    "حشو أملجم -- Amalgam Filling Class I",
    "حشو أملجم -- Amalgam Filling Class II",
    "حشو مؤقت – Temporary Filling",
    "إعادة حشو – Re-filling",
    "حشو تجميلي أمامي – Anterior Aesthetic Filling",
    "حشو عصب – Root Canal Treatment",
    "إعادة حشو عصب – Retreatment Root Canal",
    "خلع عادي – Simple Extraction",
    "خلع جراحي – Surgical Extraction",
    "خلع ضرس عقل – Wisdom Tooth Extraction",
    "خلع ضرس عقل مطمور جزئي – Partially Impacted Wisdom Tooth Extraction",
    "خلع ضرس عقل مطمور كلي – Fully Impacted Wisdom Tooth Extraction",
    "خلع سن لبني – Primary Tooth Extraction",
    "خلع بقايا جذور – Root Remnants Extraction",
    "تاج بورسلين – Porcelain Crown",
    "تاج زيركون – Zirconia Crown",
    "تاج -- E-max Crown",
    "تاج معدن – Metal Crown",
    "تاج مؤقت – Temporary Crown",
    "جسر ثابت – Fixed Bridge",
    "إعادة تثبيت تاج – Crown Recementation",
    "طقم كامل أكريليك – Complete Acrylic Denture",
    "طقم جزئي أكريليك – Partial Acrylic Denture",
    "طقم جزئي معدني – Partial Metal Denture",
    "طقم مرن – Flexible Denture",
    "تنظيف جير – Scaling",
    "كشف – Examination",
    "جلسة متابعة – Follow-up Session",
    "بوست وبناء لب – Post and Core Buildup",
]


def seed_procedures():
    db = SessionLocal()
    try:
        tenant_id = None  # Global procedures
        added_count = 0
        existing_count = 0

        print("Checking procedures...")
        for proc_name in PROCEDURES_LIST:
            # Check if exists
            exists = db.query(Procedure).filter(Procedure.name == proc_name).first()
            if exists:
                existing_count += 1
                continue

            # Create new
            new_proc = Procedure(name=proc_name, price=0.0, tenant_id=tenant_id)
            db.add(new_proc)
            added_count += 1

        db.commit()
        print(
            f"Done! Added {added_count} new procedures. Skipped {existing_count} existing."
        )

    except Exception as e:
        print(f"Error seeding procedures: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_procedures()
