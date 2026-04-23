import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import SessionLocal
from backend.models.inventory import MaterialCategory, ProcedureMaterialWeight
from backend.models.clinical import Procedure
from sqlalchemy import or_

# Maps procedure name (exact match to seed_procedures.py) → list of (category_name_en, weight)
PROCEDURE_MATERIAL_DEFAULTS = {
    # ── Composite Fillings ──
    "حشو كومبوزيت -- Composite Filling Class I": [
        ("Composite Resin", 1.0),
        ("Dental Adhesive/Bonding", 1.0),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
        ("Anesthetic Needle", 1.0),
    ],
    "حشو كومبوزيت -- Composite Filling Class II": [
        ("Composite Resin", 1.5),
        ("Dental Adhesive/Bonding", 1.0),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
        ("Anesthetic Needle", 1.0),
    ],
    "حشو كومبوزيت -- Composite Filling Class III": [
        ("Composite Resin", 0.8),
        ("Dental Adhesive/Bonding", 1.0),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
    ],
    "حشو كومبوزيت -- Composite Filling Class IV": [
        ("Composite Resin", 1.8),
        ("Dental Adhesive/Bonding", 1.0),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
    ],
    "حشو كومبوزيت -- Composite Filling Class V": [
        ("Composite Resin", 0.7),
        ("Dental Adhesive/Bonding", 1.0),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
    ],
    "حشو تجميلي أمامي – Anterior Aesthetic Filling": [
        ("Composite Resin", 2.0),
        ("Dental Adhesive/Bonding", 1.2),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
    ],

    # ── Amalgam Fillings ──
    "حشو أملجم -- Amalgam Filling Class I": [
        ("Amalgam", 1.0),
        ("Anesthetic Cartridge", 1.0),
    ],
    "حشو أملجم -- Amalgam Filling Class II": [
        ("Amalgam", 1.5),
        ("Anesthetic Cartridge", 1.0),
    ],

    # ── Temporary & Re-fillings ──
    "حشو مؤقت – Temporary Filling": [
        ("Temporary Filling Material", 1.0),
        ("Anesthetic Cartridge", 0.5),
    ],
    "إعادة حشو – Re-filling": [
        ("Composite Resin", 1.2),
        ("Dental Adhesive/Bonding", 1.0),
        ("Acid Etchant", 1.0),
        ("Anesthetic Cartridge", 1.0),
    ],

    # ── Endodontics ──
    "حشو عصب – Root Canal Treatment": [
        ("Anesthetic Cartridge", 1.5),
        ("Anesthetic Needle", 1.0),
        ("Endodontic Files", 3.0),
        ("Sodium Hypochlorite", 2.0),
        ("EDTA Solution", 1.0),
        ("Paper Points", 3.0),
        ("Gutta Percha Points", 2.0),
        ("Root Canal Sealer", 1.0),
        ("Temporary Filling Material", 1.0),
        ("Rubber Dam", 1.0),
    ],
    "إعادة حشو عصب – Retreatment Root Canal": [
        ("Anesthetic Cartridge", 2.0),
        ("Endodontic Files", 4.0),
        ("Sodium Hypochlorite", 3.0),
        ("EDTA Solution", 1.5),
        ("Paper Points", 4.0),
        ("Gutta Percha Points", 2.0),
        ("Root Canal Sealer", 1.2),
        ("Rubber Dam", 1.0),
    ],

    # ── Extractions ──
    "خلع عادي – Simple Extraction": [
        ("Anesthetic Cartridge", 1.5),
        ("Anesthetic Needle", 1.0),
        ("Surgical Gauze", 2.0),
    ],
    "خلع جراحي – Surgical Extraction": [
        ("Anesthetic Cartridge", 2.0),
        ("Anesthetic Needle", 1.0),
        ("Surgical Gauze", 3.0),
        ("Suture Material", 1.0),
    ],
    "خلع ضرس عقل – Wisdom Tooth Extraction": [
        ("Anesthetic Cartridge", 2.5),
        ("Surgical Gauze", 3.0),
        ("Suture Material", 1.0),
    ],
    "خلع ضرس عقل مطمور جزئي – Partially Impacted Wisdom Tooth Extraction": [
        ("Anesthetic Cartridge", 3.0),
        ("Surgical Gauze", 4.0),
        ("Suture Material", 1.5),
        ("Hemostatic Agent", 1.0),
    ],
    "خلع ضرس عقل مطمور كلي – Fully Impacted Wisdom Tooth Extraction": [
        ("Anesthetic Cartridge", 3.0),
        ("Surgical Gauze", 5.0),
        ("Suture Material", 2.0),
        ("Hemostatic Agent", 1.5),
    ],
    "خلع سن لبني – Primary Tooth Extraction": [
        ("Anesthetic Cartridge", 0.5),
        ("Surgical Gauze", 1.0),
    ],
    "خلع بقايا جذور – Root Remnants Extraction": [
        ("Anesthetic Cartridge", 2.0),
        ("Surgical Gauze", 3.0),
        ("Suture Material", 1.0),
    ],

    # ── Crowns & Bridges ──
    "تاج بورسلين – Porcelain Crown": [
        ("Anesthetic Cartridge", 1.5),
        ("Impression Material (Alginate)", 1.0),
        ("Impression Material (Silicone)", 1.0),
        ("Temporary Cement", 1.0),
        ("Cotton Rolls", 2.0),
    ],
    "تاج زيركون – Zirconia Crown": [
        ("Anesthetic Cartridge", 1.5),
        ("Impression Material (Alginate)", 1.0),
        ("Impression Material (Silicone)", 1.0),
        ("Temporary Cement", 1.0),
        ("Cotton Rolls", 2.0),
    ],
    "تاج -- E-max Crown": [
        ("Anesthetic Cartridge", 1.5),
        ("Impression Material (Alginate)", 1.0),
        ("Impression Material (Silicone)", 1.0),
        ("Temporary Cement", 1.0),
        ("Cotton Rolls", 2.0),
    ],
    "تاج معدن – Metal Crown": [
        ("Anesthetic Cartridge", 1.5),
        ("Impression Material (Alginate)", 1.0),
        ("Impression Material (Silicone)", 1.0),
        ("Temporary Cement", 1.0),
        ("Cotton Rolls", 2.0),
    ],
    "تاج مؤقت – Temporary Crown": [
        ("Anesthetic Cartridge", 1.0),
        ("Temporary Cement", 1.0),
    ],
    "جسر ثابت – Fixed Bridge": [
        ("Anesthetic Cartridge", 2.0),
        ("Impression Material (Silicone)", 2.0),
        ("Temporary Cement", 1.5),
    ],
    "إعادة تثبيت تاج – Crown Recementation": [
        ("Permanent Cement", 1.0),
        ("Cotton Rolls", 1.0),
    ],

    # ── Post & Core Buildup ──
    "بوست وبناء لب – Post and Core Buildup": [
        ("Anesthetic Cartridge", 1.0),
        ("Fiber Post", 1.0),
        ("Core Buildup Material", 1.5),
        ("Acid Etchant", 1.0),
        ("Dental Adhesive/Bonding", 1.0),
        ("Permanent Cement", 1.0),
    ],

    # ── Dentures ──
    "طقم كامل أكريليك – Complete Acrylic Denture": [
        ("Impression Material (Alginate)", 3.0),
    ],
    "طقم جزئي أكريليك – Partial Acrylic Denture": [
        ("Impression Material (Alginate)", 2.0),
    ],
    "طقم جزئي معدني – Partial Metal Denture": [
        ("Impression Material (Alginate)", 2.0),
        ("Impression Material (Silicone)", 1.0),
    ],
    "طقم مرن – Flexible Denture": [
        ("Impression Material (Alginate)", 2.0),
    ],

    # ── Preventive & Diagnostic ──
    "تنظيف جير – Scaling": [
        ("Polishing Paste", 1.0),
        ("Polishing Cup/Brush", 1.0),
        ("Fluoride Varnish", 1.0),
    ],
    "كشف – Examination": [
        ("Cotton Rolls", 1.0),
    ],
    # Follow-up Session: no default materials
}


def seed_procedure_material_defaults():
    db = SessionLocal()
    try:
        # Build category lookup: name_en → id
        categories = db.query(MaterialCategory).all()
        cat_map = {c.name_en: c.id for c in categories}

        # Build procedure lookup: name → id
        procedures = db.query(Procedure).filter(
            or_(Procedure.tenant_id.is_(None),)
        ).all()
        proc_map = {p.name: p.id for p in procedures}

        added_count = 0
        skipped_count = 0

        print("Seeding procedure-material defaults...")
        for proc_name, materials in PROCEDURE_MATERIAL_DEFAULTS.items():
            proc_id = proc_map.get(proc_name)
            if not proc_id:
                print(f"  ⚠ Procedure not found: {proc_name}")
                skipped_count += 1
                continue

            for cat_name_en, weight in materials:
                cat_id = cat_map.get(cat_name_en)
                if not cat_id:
                    print(f"  ⚠ Category not found: {cat_name_en}")
                    skipped_count += 1
                    continue

                # Check if already exists (procedure_id + category_id, global tenant_id=NULL)
                exists = db.query(ProcedureMaterialWeight).filter(
                    ProcedureMaterialWeight.procedure_id == proc_id,
                    ProcedureMaterialWeight.category_id == cat_id,
                    ProcedureMaterialWeight.tenant_id.is_(None),
                ).first()

                if exists:
                    continue

                pmw = ProcedureMaterialWeight(
                    procedure_id=proc_id,
                    category_id=cat_id,
                    material_id=None,  # Global defaults use category, not specific material
                    tenant_id=None,     # Global — applies to all clinics
                    weight=weight,
                )
                db.add(pmw)
                added_count += 1

        db.commit()
        print(f"Done! Added {added_count} new procedure-material defaults. Skipped {skipped_count}.")

    except Exception as e:
        print(f"Error seeding procedure-material defaults: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_procedure_material_defaults()
