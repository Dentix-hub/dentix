import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import SessionLocal
from backend.models.inventory import MaterialCategory

MATERIAL_CATEGORIES = [
    # (name_en, name_ar, default_type, default_unit)
    ("Composite Resin", "كمبوزيت", "DIVISIBLE", "g"),
    ("Dental Adhesive/Bonding", "بوندينج", "DIVISIBLE", "ml"),
    ("Acid Etchant", "حامض إتشانت", "DIVISIBLE", "ml"),
    ("Amalgam", "أملجم", "DIVISIBLE", "g"),
    ("Temporary Filling Material", "حشو مؤقت", "DIVISIBLE", "g"),
    ("Glass Ionomer Cement", "جلاس أيونومر", "DIVISIBLE", "g"),
    ("Anesthetic Cartridge", "بنج", "NON_DIVISIBLE", "cartridge"),
    ("Anesthetic Needle", "إبرة بنج", "NON_DIVISIBLE", "piece"),
    ("Gutta Percha Points", "جوتابيركا", "NON_DIVISIBLE", "piece"),
    ("Endodontic Files", "أبر عصب", "NON_DIVISIBLE", "piece"),
    ("Root Canal Sealer", "سيلر حشو عصب", "DIVISIBLE", "g"),
    ("Sodium Hypochlorite", "هايبوكلوريت", "DIVISIBLE", "ml"),
    ("EDTA Solution", "EDTA", "DIVISIBLE", "ml"),
    ("Paper Points", "بيبر بوينت", "NON_DIVISIBLE", "piece"),
    ("Suture Material", "خيط جراحي", "NON_DIVISIBLE", "piece"),
    ("Surgical Gauze", "شاش جراحي", "NON_DIVISIBLE", "piece"),
    ("Hemostatic Agent", "مادة مرقئة", "NON_DIVISIBLE", "piece"),
    ("Impression Material (Alginate)", "ألجينات", "DIVISIBLE", "g"),
    ("Impression Material (Silicone)", "سيليكون طبعة", "DIVISIBLE", "ml"),
    ("Temporary Cement", "أسمنت مؤقت", "DIVISIBLE", "g"),
    ("Permanent Cement", "أسمنت دائم", "DIVISIBLE", "g"),
    ("Polishing Paste", "بيست تلميع", "DIVISIBLE", "g"),
    ("Polishing Cup/Brush", "فرشاة تلميع", "NON_DIVISIBLE", "piece"),
    ("Fluoride Varnish", "فلورايد", "DIVISIBLE", "ml"),
    ("Rubber Dam", "رابر دام", "NON_DIVISIBLE", "piece"),
    ("Cotton Rolls", "قطن رول", "NON_DIVISIBLE", "piece"),
    ("Fiber Post", "فايبر بوست", "NON_DIVISIBLE", "piece"),
    ("Core Buildup Material", "مادة بناء اللب", "DIVISIBLE", "g"),
]


def seed_material_categories():
    db = SessionLocal()
    try:
        added_count = 0
        existing_count = 0

        print("Seeding material categories...")
        for name_en, name_ar, default_type, default_unit in MATERIAL_CATEGORIES:
            exists = db.query(MaterialCategory).filter(MaterialCategory.name_en == name_en).first()
            if exists:
                existing_count += 1
                continue

            cat = MaterialCategory(
                name_en=name_en,
                name_ar=name_ar,
                default_type=default_type,
                default_unit=default_unit,
            )
            db.add(cat)
            added_count += 1

        db.commit()
        print(f"Done! Added {added_count} new categories. Skipped {existing_count} existing.")

    except Exception as e:
        print(f"Error seeding material categories: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_material_categories()
