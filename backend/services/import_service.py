"""
Tenant Import Service

Imports tenant data from a JSON backup file.
This performs a FULL REPLACEMENT: deletes all existing tenant data, then imports from backup.
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from .. import models
from ..models.price_list import InsuranceProvider, PriceList, PriceListItem
from ..models.financial import LabPayment


def parse_datetime(value: str) -> datetime:
    """Parse ISO format datetime string."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def parse_date(value: str):
    """Parse ISO format date string."""
    if value is None:
        return None
    try:
        from datetime import date
        return date.fromisoformat(value)
    except (ValueError, AttributeError):
        return None


def validate_backup_file(data: Dict, tenant_id: int) -> Dict:
    """
    Validate backup file structure and tenant ownership.
    
    Returns:
        Dict with 'valid' bool and 'error' string if invalid
    """
    if not isinstance(data, dict):
        return {"valid": False, "error": "Invalid backup file format"}
    
    if "version" not in data:
        return {"valid": False, "error": "Missing version field"}
    
    if "tenant_id" not in data:
        return {"valid": False, "error": "Missing tenant_id field"}
    
    if data["tenant_id"] != tenant_id:
        return {
            "valid": False, 
            "error": f"Backup belongs to tenant {data['tenant_id']}, but you are tenant {tenant_id}"
        }
    
    if "data" not in data or not isinstance(data["data"], dict):
        return {"valid": False, "error": "Missing or invalid data field"}
    
    return {"valid": True, "error": None}


def delete_tenant_data(db: Session, tenant_id: int) -> Dict[str, int]:
    """
    Delete all data for a specific tenant.
    Order matters due to foreign key constraints.
    
    Returns:
        Dict with table names and count of deleted records
    """
    deleted_counts = {}
    
    # Order: child tables first, parent tables last
    
    # 1. MaterialSessions (via StockItem)
    stock_item_ids = [si.id for si in db.query(models.StockItem.id).filter(
        models.StockItem.tenant_id == tenant_id
    ).all()]
    if stock_item_ids:
        count = db.query(models.MaterialSession).filter(
            models.MaterialSession.stock_item_id.in_(stock_item_ids)
        ).delete(synchronize_session=False)
        deleted_counts["material_sessions"] = count
        
        # StockMovements
        count = db.query(models.StockMovement).filter(
            models.StockMovement.stock_item_id.in_(stock_item_ids)
        ).delete(synchronize_session=False)
        deleted_counts["stock_movements"] = count
    
    # 2. StockItems
    count = db.query(models.StockItem).filter(
        models.StockItem.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["stock_items"] = count
    
    # 3. Batches
    count = db.query(models.Batch).filter(
        models.Batch.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["batches"] = count
    
    # 4. Materials
    count = db.query(models.Material).filter(
        models.Material.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["materials"] = count
    
    # 5. Warehouses
    count = db.query(models.Warehouse).filter(
        models.Warehouse.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["warehouses"] = count
    
    # 6. ProcedureMaterialWeights
    count = db.query(models.ProcedureMaterialWeight).filter(
        models.ProcedureMaterialWeight.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["procedure_material_weights"] = count
    
    # 7. PriceListItems (via PriceList)
    price_list_ids = [pl.id for pl in db.query(PriceList.id).filter(
        PriceList.tenant_id == tenant_id
    ).all()]
    if price_list_ids:
        count = db.query(PriceListItem).filter(
            PriceListItem.price_list_id.in_(price_list_ids)
        ).delete(synchronize_session=False)
        deleted_counts["price_list_items"] = count
    
    # 8. PriceLists
    count = db.query(PriceList).filter(
        PriceList.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["price_lists"] = count
    
    # 9. InsuranceProviders
    count = db.query(InsuranceProvider).filter(
        InsuranceProvider.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["insurance_providers"] = count
    
    # 10. LabPayments
    count = db.query(LabPayment).filter(
        LabPayment.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["lab_payments"] = count
    
    # 11. LabOrders
    count = db.query(models.LabOrder).filter(
        models.LabOrder.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["lab_orders"] = count
    
    # 12. Laboratories
    count = db.query(models.Laboratory).filter(
        models.Laboratory.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["laboratories"] = count
    
    # 13. SalaryPayments
    count = db.query(models.SalaryPayment).filter(
        models.SalaryPayment.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["salary_payments"] = count
    
    # 14. SavedMedications
    count = db.query(models.SavedMedication).filter(
        models.SavedMedication.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["saved_medications"] = count
    
    # 15. Expenses
    count = db.query(models.Expense).filter(
        models.Expense.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["expenses"] = count
    
    # 16. Payments
    count = db.query(models.Payment).filter(
        models.Payment.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["payments"] = count
    
    # 17. Treatments
    count = db.query(models.Treatment).filter(
        models.Treatment.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["treatments"] = count
    
    # 18. Procedures
    count = db.query(models.Procedure).filter(
        models.Procedure.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["procedures"] = count
    
    # 19. Prescriptions, ToothStatus, Attachments, Appointments (via Patient cascade)
    # Get patient IDs first
    patient_ids = [p.id for p in db.query(models.Patient.id).filter(
        models.Patient.tenant_id == tenant_id
    ).all()]
    
    if patient_ids:
        # Prescriptions
        count = db.query(models.Prescription).filter(
            models.Prescription.patient_id.in_(patient_ids)
        ).delete(synchronize_session=False)
        deleted_counts["prescriptions"] = count
        
        # ToothStatus
        count = db.query(models.ToothStatus).filter(
            models.ToothStatus.patient_id.in_(patient_ids)
        ).delete(synchronize_session=False)
        deleted_counts["tooth_statuses"] = count
        
        # Attachments
        count = db.query(models.Attachment).filter(
            models.Attachment.patient_id.in_(patient_ids)
        ).delete(synchronize_session=False)
        deleted_counts["attachments"] = count
        
        # Appointments
        count = db.query(models.Appointment).filter(
            models.Appointment.patient_id.in_(patient_ids)
        ).delete(synchronize_session=False)
        deleted_counts["appointments"] = count
    
    # 20. Patients
    count = db.query(models.Patient).filter(
        models.Patient.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["patients"] = count
    
    # 21. Users (tenant staff - NOT super_admin)
    count = db.query(models.User).filter(
        models.User.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    deleted_counts["users"] = count
    
    return deleted_counts


def import_tenant_data(db: Session, tenant_id: int, backup_data: Dict) -> Dict:
    """
    Import tenant data from backup.
    This is a FULL REPLACEMENT operation.
    
    Args:
        db: Database session
        tenant_id: The tenant ID to import data for
        backup_data: Parsed JSON backup data
        
    Returns:
        Dict with import statistics
    """
    data = backup_data.get("data", {})
    imported_counts = {}
    
    # ID mapping for foreign key references
    # old_id -> new_id
    id_maps = {
        "users": {},
        "patients": {},
        "laboratories": {},
        "procedures": {},
        "price_lists": {},
        "insurance_providers": {},
        "warehouses": {},
        "materials": {},
        "batches": {},
        "stock_items": {},
    }
    
    # 1. Import Users
    for user_data in data.get("users", []):
        old_id = user_data.pop("id", None)
        user_data["tenant_id"] = tenant_id
        # Parse datetime fields
        for dt_field in ["last_failed_login", "account_locked_until", "deleted_at"]:
            if dt_field in user_data:
                user_data[dt_field] = parse_datetime(user_data[dt_field])
        if "hire_date" in user_data:
            user_data["hire_date"] = parse_date(user_data["hire_date"])
        
        user = models.User(**user_data)
        db.add(user)
        db.flush()
        if old_id:
            id_maps["users"][old_id] = user.id
    imported_counts["users"] = len(data.get("users", []))
    
    # 2. Import Patients
    for patient_data in data.get("patients", []):
        old_id = patient_data.pop("id", None)
        patient_data["tenant_id"] = tenant_id
        patient_data["created_at"] = parse_datetime(patient_data.get("created_at"))
        patient_data["deleted_at"] = parse_datetime(patient_data.get("deleted_at"))
        # Map doctor_id if exists
        if patient_data.get("assigned_doctor_id"):
            patient_data["assigned_doctor_id"] = id_maps["users"].get(
                patient_data["assigned_doctor_id"], None
            )
        # Remove price_list reference for now (will be mapped later if needed)
        patient_data.pop("default_price_list_id", None)
        
        patient = models.Patient(**patient_data)
        db.add(patient)
        db.flush()
        if old_id:
            id_maps["patients"][old_id] = patient.id
    imported_counts["patients"] = len(data.get("patients", []))
    
    # 3. Import Laboratories
    for lab_data in data.get("laboratories", []):
        old_id = lab_data.pop("id", None)
        lab_data["tenant_id"] = tenant_id
        lab_data["created_at"] = parse_datetime(lab_data.get("created_at"))
        
        lab = models.Laboratory(**lab_data)
        db.add(lab)
        db.flush()
        if old_id:
            id_maps["laboratories"][old_id] = lab.id
    imported_counts["laboratories"] = len(data.get("laboratories", []))
    
    # 4. Import Procedures
    for proc_data in data.get("procedures", []):
        old_id = proc_data.pop("id", None)
        proc_data["tenant_id"] = tenant_id
        
        proc = models.Procedure(**proc_data)
        db.add(proc)
        db.flush()
        if old_id:
            id_maps["procedures"][old_id] = proc.id
    imported_counts["procedures"] = len(data.get("procedures", []))
    
    # 5. Import InsuranceProviders
    for ip_data in data.get("insurance_providers", []):
        old_id = ip_data.pop("id", None)
        ip_data["tenant_id"] = tenant_id
        ip_data["created_at"] = parse_datetime(ip_data.get("created_at"))
        
        ip = InsuranceProvider(**ip_data)
        db.add(ip)
        db.flush()
        if old_id:
            id_maps["insurance_providers"][old_id] = ip.id
    imported_counts["insurance_providers"] = len(data.get("insurance_providers", []))
    
    # 6. Import PriceLists
    for pl_data in data.get("price_lists", []):
        old_id = pl_data.pop("id", None)
        pl_data["tenant_id"] = tenant_id
        pl_data["created_at"] = parse_datetime(pl_data.get("created_at"))
        pl_data["updated_at"] = parse_datetime(pl_data.get("updated_at"))
        pl_data["effective_from"] = parse_date(pl_data.get("effective_from"))
        pl_data["effective_to"] = parse_date(pl_data.get("effective_to"))
        # Map insurance_provider_id
        if pl_data.get("insurance_provider_id"):
            pl_data["insurance_provider_id"] = id_maps["insurance_providers"].get(
                pl_data["insurance_provider_id"], None
            )
        
        pl = PriceList(**pl_data)
        db.add(pl)
        db.flush()
        if old_id:
            id_maps["price_lists"][old_id] = pl.id
    imported_counts["price_lists"] = len(data.get("price_lists", []))
    
    # 7. Import PriceListItems
    for pli_data in data.get("price_list_items", []):
        pli_data.pop("id", None)
        pli_data["price_list_id"] = id_maps["price_lists"].get(pli_data.get("price_list_id"))
        pli_data["procedure_id"] = id_maps["procedures"].get(pli_data.get("procedure_id"))
        pli_data["created_at"] = parse_datetime(pli_data.get("created_at"))
        pli_data["updated_at"] = parse_datetime(pli_data.get("updated_at"))
        
        if pli_data["price_list_id"] and pli_data["procedure_id"]:
            pli = PriceListItem(**pli_data)
            db.add(pli)
    imported_counts["price_list_items"] = len(data.get("price_list_items", []))
    
    # 8. Import Warehouses
    for wh_data in data.get("warehouses", []):
        old_id = wh_data.pop("id", None)
        wh_data["tenant_id"] = tenant_id
        
        wh = models.Warehouse(**wh_data)
        db.add(wh)
        db.flush()
        if old_id:
            id_maps["warehouses"][old_id] = wh.id
    imported_counts["warehouses"] = len(data.get("warehouses", []))
    
    # 9. Import Materials
    for mat_data in data.get("materials", []):
        old_id = mat_data.pop("id", None)
        mat_data["tenant_id"] = tenant_id
        
        mat = models.Material(**mat_data)
        db.add(mat)
        db.flush()
        if old_id:
            id_maps["materials"][old_id] = mat.id
    imported_counts["materials"] = len(data.get("materials", []))
    
    # 10. Import Batches
    for batch_data in data.get("batches", []):
        old_id = batch_data.pop("id", None)
        batch_data["tenant_id"] = tenant_id
        batch_data["material_id"] = id_maps["materials"].get(batch_data.get("material_id"))
        batch_data["expiry_date"] = parse_date(batch_data.get("expiry_date"))
        batch_data["created_at"] = parse_datetime(batch_data.get("created_at"))
        
        if batch_data["material_id"]:
            batch = models.Batch(**batch_data)
            db.add(batch)
            db.flush()
            if old_id:
                id_maps["batches"][old_id] = batch.id
    imported_counts["batches"] = len(data.get("batches", []))
    
    # 11. Import StockItems
    for si_data in data.get("stock_items", []):
        old_id = si_data.pop("id", None)
        si_data["tenant_id"] = tenant_id
        si_data["warehouse_id"] = id_maps["warehouses"].get(si_data.get("warehouse_id"))
        si_data["batch_id"] = id_maps["batches"].get(si_data.get("batch_id"))
        
        if si_data["warehouse_id"] and si_data["batch_id"]:
            si = models.StockItem(**si_data)
            db.add(si)
            db.flush()
            if old_id:
                id_maps["stock_items"][old_id] = si.id
    imported_counts["stock_items"] = len(data.get("stock_items", []))
    
    # 12. Import Appointments
    for appt_data in data.get("appointments", []):
        appt_data.pop("id", None)
        appt_data["patient_id"] = id_maps["patients"].get(appt_data.get("patient_id"))
        appt_data["doctor_id"] = id_maps["users"].get(appt_data.get("doctor_id"))
        appt_data["price_list_id"] = id_maps["price_lists"].get(appt_data.get("price_list_id"))
        appt_data["date_time"] = parse_datetime(appt_data.get("date_time"))
        appt_data["deleted_at"] = parse_datetime(appt_data.get("deleted_at"))
        
        if appt_data["patient_id"]:
            appt = models.Appointment(**appt_data)
            db.add(appt)
    imported_counts["appointments"] = len(data.get("appointments", []))
    
    # 13. Import Treatments
    for treat_data in data.get("treatments", []):
        treat_data.pop("id", None)
        treat_data["tenant_id"] = tenant_id
        treat_data["patient_id"] = id_maps["patients"].get(treat_data.get("patient_id"))
        treat_data["doctor_id"] = id_maps["users"].get(treat_data.get("doctor_id"))
        treat_data["price_list_id"] = id_maps["price_lists"].get(treat_data.get("price_list_id"))
        treat_data["date"] = parse_datetime(treat_data.get("date"))
        
        if treat_data["patient_id"]:
            treat = models.Treatment(**treat_data)
            db.add(treat)
    imported_counts["treatments"] = len(data.get("treatments", []))
    
    # 14. Import Payments
    for pay_data in data.get("payments", []):
        pay_data.pop("id", None)
        pay_data["tenant_id"] = tenant_id
        pay_data["patient_id"] = id_maps["patients"].get(pay_data.get("patient_id"))
        pay_data["doctor_id"] = id_maps["users"].get(pay_data.get("doctor_id"))
        pay_data["date"] = parse_datetime(pay_data.get("date"))
        
        if pay_data["patient_id"]:
            pay = models.Payment(**pay_data)
            db.add(pay)
    imported_counts["payments"] = len(data.get("payments", []))
    
    # 15. Import Expenses
    for exp_data in data.get("expenses", []):
        exp_data.pop("id", None)
        exp_data["tenant_id"] = tenant_id
        exp_data["date"] = parse_date(exp_data.get("date"))
        
        exp = models.Expense(**exp_data)
        db.add(exp)
    imported_counts["expenses"] = len(data.get("expenses", []))
    
    # 16. Import remaining tables (simplified for brevity)
    # Prescriptions, ToothStatus, Attachments, LabOrders, LabPayments, SalaryPayments, SavedMedications, etc.
    
    for pres_data in data.get("prescriptions", []):
        pres_data.pop("id", None)
        pres_data["patient_id"] = id_maps["patients"].get(pres_data.get("patient_id"))
        pres_data["date"] = parse_datetime(pres_data.get("date"))
        if pres_data["patient_id"]:
            db.add(models.Prescription(**pres_data))
    imported_counts["prescriptions"] = len(data.get("prescriptions", []))
    
    for ts_data in data.get("tooth_statuses", []):
        ts_data.pop("id", None)
        ts_data["patient_id"] = id_maps["patients"].get(ts_data.get("patient_id"))
        if ts_data["patient_id"]:
            db.add(models.ToothStatus(**ts_data))
    imported_counts["tooth_statuses"] = len(data.get("tooth_statuses", []))
    
    for att_data in data.get("attachments", []):
        att_data.pop("id", None)
        att_data["patient_id"] = id_maps["patients"].get(att_data.get("patient_id"))
        att_data["created_at"] = parse_datetime(att_data.get("created_at"))
        if att_data["patient_id"]:
            db.add(models.Attachment(**att_data))
    imported_counts["attachments"] = len(data.get("attachments", []))
    
    for lo_data in data.get("lab_orders", []):
        lo_data.pop("id", None)
        lo_data["tenant_id"] = tenant_id
        lo_data["patient_id"] = id_maps["patients"].get(lo_data.get("patient_id"))
        lo_data["laboratory_id"] = id_maps["laboratories"].get(lo_data.get("laboratory_id"))
        lo_data["doctor_id"] = id_maps["users"].get(lo_data.get("doctor_id"))
        lo_data["order_date"] = parse_datetime(lo_data.get("order_date"))
        lo_data["delivery_date"] = parse_datetime(lo_data.get("delivery_date"))
        lo_data["received_date"] = parse_datetime(lo_data.get("received_date"))
        if lo_data["patient_id"]:
            db.add(models.LabOrder(**lo_data))
    imported_counts["lab_orders"] = len(data.get("lab_orders", []))
    
    for lp_data in data.get("lab_payments", []):
        lp_data.pop("id", None)
        lp_data["tenant_id"] = tenant_id
        lp_data["laboratory_id"] = id_maps["laboratories"].get(lp_data.get("laboratory_id"))
        lp_data["date"] = parse_datetime(lp_data.get("date"))
        if lp_data["laboratory_id"]:
            db.add(LabPayment(**lp_data))
    imported_counts["lab_payments"] = len(data.get("lab_payments", []))
    
    for sp_data in data.get("salary_payments", []):
        sp_data.pop("id", None)
        sp_data["tenant_id"] = tenant_id
        sp_data["user_id"] = id_maps["users"].get(sp_data.get("user_id"))
        sp_data["payment_date"] = parse_datetime(sp_data.get("payment_date"))
        if sp_data["user_id"]:
            db.add(models.SalaryPayment(**sp_data))
    imported_counts["salary_payments"] = len(data.get("salary_payments", []))
    
    for sm_data in data.get("saved_medications", []):
        sm_data.pop("id", None)
        sm_data["tenant_id"] = tenant_id
        sm_data["created_at"] = parse_datetime(sm_data.get("created_at"))
        db.add(models.SavedMedication(**sm_data))
    imported_counts["saved_medications"] = len(data.get("saved_medications", []))
    
    return imported_counts


def restore_tenant_from_json(db: Session, tenant_id: int, json_content: str) -> Dict:
    """
    Full restore of tenant data from JSON backup.
    
    This is a DESTRUCTIVE operation that:
    1. Validates the backup file
    2. Deletes ALL existing tenant data
    3. Imports all data from backup
    
    Args:
        db: Database session
        tenant_id: The tenant ID to restore data for
        json_content: JSON string of backup data
        
    Returns:
        Dict with restore statistics or error
    """
    # 1. Parse JSON
    try:
        backup_data = json.loads(json_content)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    
    # 2. Validate
    validation = validate_backup_file(backup_data, tenant_id)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}
    
    # 3. Delete existing data
    try:
        deleted_counts = delete_tenant_data(db, tenant_id)
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Failed to delete existing data: {str(e)}"}
    
    # 4. Import new data
    try:
        imported_counts = import_tenant_data(db, tenant_id, backup_data)
        db.commit()
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Failed to import data: {str(e)}"}
    
    return {
        "success": True,
        "deleted": deleted_counts,
        "imported": imported_counts,
        "backup_version": backup_data.get("version"),
        "backup_date": backup_data.get("exported_at")
    }
