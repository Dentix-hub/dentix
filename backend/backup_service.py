# import sqlite3 (removed for production)
from sqlalchemy.orm import Session
from sqlalchemy import DateTime, Date
from datetime import datetime, date
from . import models

# Map table name to Model
TABLE_MODEL_MAP = {
    "users": models.User,
    "procedures": models.Procedure,
    "patients": models.Patient,
    "appointments": models.Appointment,
    "tooth_status": models.ToothStatus,
    "treatments": models.Treatment,
    "payments": models.Payment,
    "attachments": models.Attachment,
    "expenses": models.Expense,
    "prescriptions": models.Prescription,
    "tenants": models.Tenant,
    "subscription_plans": models.SubscriptionPlan,
    "subscription_payments": models.SubscriptionPayment,
}

ORDERED_TABLES = [
    "subscription_plans",
    "tenants",
    "subscription_payments",
    "users",
    "procedures",
    "patients",
    "expenses",
    "appointments",
    "tooth_status",
    "treatments",
    "payments",
    "attachments",
    "prescriptions",
]


def parse_value(model, key, value):
    if value is None:
        return None
    try:
        col = model.__table__.columns.get(key)
        if col is not None:
            # Handle empty strings which crash datetime parser
            if isinstance(value, str) and value.strip() == "":
                return None

            if isinstance(col.type, DateTime) and isinstance(value, str):
                return datetime.fromisoformat(value.replace(" ", "T"))
            elif isinstance(col.type, Date) and isinstance(value, str):
                if "T" in value:
                    return datetime.fromisoformat(value).date()
                return datetime.strptime(value, "%Y-%m-%d").date()
    except:
        # On parse failure, return None instead of original string to avoid DB TypeErrors
        return None
    return value


def import_from_sqlite(db: Session, sqlite_path: str):
    """
    Deprecated/Removed for Production Safety.
    SQLite is no longer supported.
    """
    raise NotImplementedError("SQLite import is removed in production.")


def import_from_json(db: Session, json_data: dict):
    stats = {t: {"restored": 0, "errors": 0} for t in ORDERED_TABLES}

    for table_name in ORDERED_TABLES:
        if table_name not in json_data:
            continue
        model = TABLE_MODEL_MAP[table_name]
        raw_records = json_data[table_name]

        if not raw_records:
            continue

        # 1. Pre-process all records (Validation & Parsing)
        clean_records = []
        valid_cols = set(c.name for c in model.__table__.columns)

        for r in raw_records:
            try:
                # Filter valid columns only
                d = {k: v for k, v in r.items() if k in valid_cols}
                # Parse Dates/Types
                for k, v in d.items():
                    d[k] = parse_value(model, k, v)
                clean_records.append(d)
            except Exception:
                stats[table_name]["errors"] += 1

        if not clean_records:
            continue

        # 2. Identify Existing IDs (Bulk lookup)
        # This prevents N queries. We fetch all IDs involved in this batch or all IDs in table.
        # Fetching all IDs in table is O(Total_Rows), fetching IDs in batch is O(Batch_Size).
        # We'll use "Fetch all IDs" for simplicity as SaaS tables aren't massive yet.
        # Optimization: Filter only IDs present in dataset.
        incoming_ids = [rec["id"] for rec in clean_records if "id" in rec]
        existing_ids_set = set()

        if incoming_ids:
            # Query in chunks if needed, but for now direct 'in_'
            # Using chunks of 900 for SQLite limits
            chunk_size = 900
            for i in range(0, len(incoming_ids), chunk_size):
                chunk = incoming_ids[i : i + chunk_size]
                found = db.query(model.id).filter(model.id.in_(chunk)).all()
                existing_ids_set.update(f[0] for f in found)

        # 3. Segregate Insert vs Update
        to_insert = []
        to_update = []

        for rec in clean_records:
            # If ID is missing, treat as new insert (DB will auto-increment)
            if rec.get("id") in existing_ids_set:
                to_update.append(rec)
            else:
                to_insert.append(rec)

        # 4. Execute Bulk Operations
        try:
            if to_insert:
                db.bulk_insert_mappings(model, to_insert)
                stats[table_name]["restored"] += len(to_insert)

            if to_update:
                db.bulk_update_mappings(model, to_update)
                stats[table_name]["restored"] += len(to_update)

            db.flush()
        except Exception as e:
            print(f"Bulk Error in {table_name}: {e}")
            stats[table_name]["errors"] += len(clean_records)
            db.rollback()  # Rollback this table, try next

    db.commit()
    return stats


def create_json_dump(db: Session, tenant_id: int = None):
    dump_data = {}
    for table_name in ORDERED_TABLES:
        model = TABLE_MODEL_MAP[table_name]
        query = db.query(model)

        # Apply Tenant Filter if applicable
        # (Logic consolidated below to handle both direct and indirect relationships)

        # Special handling for tables linked via patient if no direct tenant_id
        # e.g. details that belong to a patient of that tenant
        # But our schema says: patients has tenant_id.
        # appointments, treatments, payments, etc usually link to patient.
        # DO we have tenant_id on ALL tables?
        # Let's check schema again.
        # Patients, Appointments, Users have tenant_id.
        # Treatments, Payments rely on Patient? No, usually we added tenant_id to them in previous steps?
        # In main.py migration:
        # add_column_safe("patients", "tenant_id ...")
        # add_column_safe("appointments", "tenant_id ...")
        # add_column_safe("users", "tenant_id ...")
        # Treatments, Payments, ToothStatus, Attachments, Prescriptions do NOT have tenant_id in that migration list.
        # They depend on Patient.

        # So we need safer filtering strategy:
        # If model has tenant_id -> filter by it.
        # If model has patient_id -> join Patient and filter by Patient.tenant_id

        if tenant_id is not None:
            if hasattr(model, "tenant_id"):
                query = query.filter(model.tenant_id == tenant_id)
            elif hasattr(model, "patient_id"):
                query = query.join(models.Patient).filter(
                    models.Patient.tenant_id == tenant_id
                )

        records = query.all()
        list_data = []
        for r in records:
            d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
            for k, v in d.items():
                if isinstance(v, (datetime, date)):
                    d[k] = v.isoformat()
            list_data.append(d)
        dump_data[table_name] = list_data
    return dump_data
