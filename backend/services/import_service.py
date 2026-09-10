"""
Tenant Import Service

Imports tenant data from a JSON backup file.
This performs a FULL REPLACEMENT: deletes all existing tenant data, then imports from backup.
"""

import json
from datetime import datetime
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .. import models
from ..models.price_list import InsuranceProvider, PriceList, PriceListItem
from ..models.financial import LabPayment
from ..crud.patient import delete_tenant_clinical_rows


def parse_datetime(value: str) -> datetime:
    """Parse ISO format datetime string."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
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
            "error": f"Backup belongs to tenant {data['tenant_id']}, but you are tenant {tenant_id}",
        }

    if "data" not in data or not isinstance(data["data"], dict):
        return {"valid": False, "error": "Missing or invalid data field"}

    return {"valid": True, "error": None}


async def delete_tenant_data(db: AsyncSession, tenant_id: int) -> Dict[str, int]:
    """
    Delete all data for a specific tenant.
    Order matters due to foreign key constraints.

    Returns:
        Dict with table names and count of deleted records
    """
    deleted_counts = {}

    # Order: child tables first, parent tables last

    # Clinical VNext patient-owned aggregates use restrictive patient foreign
    # keys. Remove them tenant-wide before the legacy cleanup reaches patients.
    deleted_counts.update(await delete_tenant_clinical_rows(db, tenant_id))

    # Tenant-owned workflow templates
    stmt_wt = delete(models.WorkflowTemplate).where(models.WorkflowTemplate.tenant_id == tenant_id)
    res_wt = await db.execute(stmt_wt)
    deleted_counts["workflow_templates"] = res_wt.rowcount

    # 1. MaterialSessions (via StockItem)
    stmt_stock_items = select(models.StockItem.id).where(models.StockItem.tenant_id == tenant_id)
    res_stock_items = await db.execute(stmt_stock_items)
    stock_item_ids = list(res_stock_items.scalars().all())

    if stock_item_ids:
        stmt = delete(models.MaterialSession).where(models.MaterialSession.stock_item_id.in_(stock_item_ids))
        res = await db.execute(stmt)
        deleted_counts["material_sessions"] = res.rowcount

        # StockMovements
        stmt = delete(models.StockMovement).where(models.StockMovement.stock_item_id.in_(stock_item_ids))
        res = await db.execute(stmt)
        deleted_counts["stock_movements"] = res.rowcount

    # 2. StockItems
    stmt = delete(models.StockItem).where(models.StockItem.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["stock_items"] = res.rowcount

    # 3. Batches
    stmt = delete(models.Batch).where(models.Batch.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["batches"] = res.rowcount

    # 4. Materials
    stmt = delete(models.Material).where(models.Material.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["materials"] = res.rowcount

    # 5. Warehouses
    stmt = delete(models.Warehouse).where(models.Warehouse.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["warehouses"] = res.rowcount

    # 6. ProcedureMaterialWeights
    stmt = delete(models.ProcedureMaterialWeight).where(models.ProcedureMaterialWeight.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["procedure_material_weights"] = res.rowcount

    # 7. PriceListItems (via PriceList)
    stmt_price_lists = select(PriceList.id).where(PriceList.tenant_id == tenant_id)
    res_price_lists = await db.execute(stmt_price_lists)
    price_list_ids = list(res_price_lists.scalars().all())

    if price_list_ids:
        stmt = delete(PriceListItem).where(PriceListItem.price_list_id.in_(price_list_ids))
        res = await db.execute(stmt)
        deleted_counts["price_list_items"] = res.rowcount

    # 8. PriceLists
    stmt = delete(PriceList).where(PriceList.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["price_lists"] = res.rowcount

    # 9. InsuranceProviders
    stmt = delete(InsuranceProvider).where(InsuranceProvider.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["insurance_providers"] = res.rowcount

    # 10. LabPayments
    stmt = delete(LabPayment).where(LabPayment.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["lab_payments"] = res.rowcount

    # 11. LabOrders
    stmt = delete(models.LabOrder).where(models.LabOrder.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["lab_orders"] = res.rowcount

    # 12. Laboratories
    stmt = delete(models.Laboratory).where(models.Laboratory.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["laboratories"] = res.rowcount

    # 13. SalaryPayments
    stmt = delete(models.SalaryPayment).where(models.SalaryPayment.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["salary_payments"] = res.rowcount

    # 14. SavedMedications
    stmt = delete(models.SavedMedication).where(models.SavedMedication.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["saved_medications"] = res.rowcount

    # 15. Expenses
    stmt = delete(models.Expense).where(models.Expense.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["expenses"] = res.rowcount

    # 16. Payments
    stmt = delete(models.Payment).where(models.Payment.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["payments"] = res.rowcount

    # 17. Treatments
    stmt = delete(models.Treatment).where(models.Treatment.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["treatments"] = res.rowcount

    # 18. Procedures
    stmt = delete(models.Procedure).where(models.Procedure.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["procedures"] = res.rowcount

    # 19. Prescriptions, ToothStatus, Attachments, Appointments (via Patient cascade)
    stmt_patients = select(models.Patient.id).where(models.Patient.tenant_id == tenant_id)
    res_patients = await db.execute(stmt_patients)
    patient_ids = list(res_patients.scalars().all())

    if patient_ids:
        # Prescriptions
        stmt = delete(models.Prescription).where(models.Prescription.patient_id.in_(patient_ids))
        res = await db.execute(stmt)
        deleted_counts["prescriptions"] = res.rowcount

        # ToothStatus
        stmt = delete(models.ToothStatus).where(models.ToothStatus.patient_id.in_(patient_ids))
        res = await db.execute(stmt)
        deleted_counts["tooth_statuses"] = res.rowcount

        # Attachments
        stmt = delete(models.Attachment).where(models.Attachment.patient_id.in_(patient_ids))
        res = await db.execute(stmt)
        deleted_counts["attachments"] = res.rowcount

        # Appointments
        stmt = delete(models.Appointment).where(models.Appointment.patient_id.in_(patient_ids))
        res = await db.execute(stmt)
        deleted_counts["appointments"] = res.rowcount

    # 20. Patients
    stmt = delete(models.Patient).where(models.Patient.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["patients"] = res.rowcount

    # 21. Users (tenant staff - NOT super_admin)
    stmt = delete(models.User).where(models.User.tenant_id == tenant_id)
    res = await db.execute(stmt)
    deleted_counts["users"] = res.rowcount

    return deleted_counts


async def import_tenant_data(db: AsyncSession, tenant_id: int, backup_data: Dict) -> Dict:
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
        "appointments": {},
        "attachments": {},
        "workflow_templates": {},
        "clinical_work_items": {},
        "clinical_treatment_plans": {},
        "clinical_treatment_plan_phases": {},
        "care_sessions": {},
        "care_session_steps": {},
        "clinical_events": {},
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
        await db.flush()
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
        await db.flush()
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
        await db.flush()
        if old_id:
            id_maps["laboratories"][old_id] = lab.id
    imported_counts["laboratories"] = len(data.get("laboratories", []))

    # 4. Import Procedures
    for proc_data in data.get("procedures", []):
        old_id = proc_data.pop("id", None)
        proc_data["tenant_id"] = tenant_id

        proc = models.Procedure(**proc_data)
        db.add(proc)
        await db.flush()
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
        await db.flush()
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
        await db.flush()
        if old_id:
            id_maps["price_lists"][old_id] = pl.id
    imported_counts["price_lists"] = len(data.get("price_lists", []))

    # 7. Import PriceListItems
    for pli_data in data.get("price_list_items", []):
        pli_data.pop("id", None)
        pli_data["price_list_id"] = id_maps["price_lists"].get(
            pli_data.get("price_list_id")
        )
        pli_data["procedure_id"] = id_maps["procedures"].get(
            pli_data.get("procedure_id")
        )
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
        await db.flush()
        if old_id:
            id_maps["warehouses"][old_id] = wh.id
    imported_counts["warehouses"] = len(data.get("warehouses", []))

    # 9. Import Materials
    for mat_data in data.get("materials", []):
        old_id = mat_data.pop("id", None)
        mat_data["tenant_id"] = tenant_id

        mat = models.Material(**mat_data)
        db.add(mat)
        await db.flush()
        if old_id:
            id_maps["materials"][old_id] = mat.id
    imported_counts["materials"] = len(data.get("materials", []))

    # 10. Import Batches
    for batch_data in data.get("batches", []):
        old_id = batch_data.pop("id", None)
        batch_data["tenant_id"] = tenant_id
        batch_data["material_id"] = id_maps["materials"].get(
            batch_data.get("material_id")
        )
        batch_data["expiry_date"] = parse_date(batch_data.get("expiry_date"))
        batch_data["created_at"] = parse_datetime(batch_data.get("created_at"))

        if batch_data["material_id"]:
            batch = models.Batch(**batch_data)
            db.add(batch)
            await db.flush()
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
            await db.flush()
            if old_id:
                id_maps["stock_items"][old_id] = si.id
    imported_counts["stock_items"] = len(data.get("stock_items", []))

    # 12. Import Appointments
    for appt_data in data.get("appointments", []):
        old_id = appt_data.pop("id", None)
        appt_data["patient_id"] = id_maps["patients"].get(appt_data.get("patient_id"))
        appt_data["doctor_id"] = id_maps["users"].get(appt_data.get("doctor_id"))
        appt_data["price_list_id"] = id_maps["price_lists"].get(
            appt_data.get("price_list_id")
        )
        appt_data["date_time"] = parse_datetime(appt_data.get("date_time"))
        appt_data["deleted_at"] = parse_datetime(appt_data.get("deleted_at"))

        if appt_data["patient_id"]:
            appt = models.Appointment(**appt_data)
            db.add(appt)
            await db.flush()
            if old_id:
                id_maps["appointments"][old_id] = appt.id
    imported_counts["appointments"] = len(data.get("appointments", []))

    # 13. Import Treatments
    for treat_data in data.get("treatments", []):
        treat_data.pop("id", None)
        treat_data["tenant_id"] = tenant_id
        treat_data["patient_id"] = id_maps["patients"].get(treat_data.get("patient_id"))
        treat_data["doctor_id"] = id_maps["users"].get(treat_data.get("doctor_id"))
        treat_data["price_list_id"] = id_maps["price_lists"].get(
            treat_data.get("price_list_id")
        )
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

    for pres_data in data.get("prescriptions", []):
        pres_data.pop("id", None)
        pres_data["tenant_id"] = tenant_id
        pres_data["patient_id"] = id_maps["patients"].get(pres_data.get("patient_id"))
        pres_data["date"] = parse_datetime(pres_data.get("date"))
        if pres_data["patient_id"]:
            db.add(models.Prescription(**pres_data))
    imported_counts["prescriptions"] = len(data.get("prescriptions", []))

    for ts_data in data.get("tooth_statuses", []):
        ts_data.pop("id", None)
        ts_data["tenant_id"] = tenant_id
        ts_data["patient_id"] = id_maps["patients"].get(ts_data.get("patient_id"))
        if ts_data["patient_id"]:
            db.add(models.ToothStatus(**ts_data))
    imported_counts["tooth_statuses"] = len(data.get("tooth_statuses", []))

    for att_data in data.get("attachments", []):
        old_id = att_data.pop("id", None)
        att_data["tenant_id"] = tenant_id
        att_data["patient_id"] = id_maps["patients"].get(att_data.get("patient_id"))
        att_data["created_at"] = parse_datetime(att_data.get("created_at"))
        if att_data["patient_id"]:
            att = models.Attachment(**att_data)
            db.add(att)
            await db.flush()
            if old_id:
                id_maps["attachments"][old_id] = att.id
    imported_counts["attachments"] = len(data.get("attachments", []))

    for lo_data in data.get("lab_orders", []):
        lo_data.pop("id", None)
        lo_data["tenant_id"] = tenant_id
        lo_data["patient_id"] = id_maps["patients"].get(lo_data.get("patient_id"))
        lo_data["laboratory_id"] = id_maps["laboratories"].get(
            lo_data.get("laboratory_id")
        )
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
        lp_data["laboratory_id"] = id_maps["laboratories"].get(
            lp_data.get("laboratory_id")
        )
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

    # 26. Import WorkflowTemplates
    for wt_data in data.get("workflow_templates", []):
        old_id = wt_data.pop("id", None)
        wt_data["tenant_id"] = tenant_id
        wt_data["created_at"] = parse_datetime(wt_data.get("created_at"))
        wt_data["updated_at"] = parse_datetime(wt_data.get("updated_at"))
        wt = models.WorkflowTemplate(**wt_data)
        db.add(wt)
        await db.flush()
        if old_id:
            id_maps["workflow_templates"][old_id] = wt.id
    imported_counts["workflow_templates"] = len(data.get("workflow_templates", []))

    # 27. Import ClinicalWorkItems
    for wi_data in data.get("clinical_work_items", []):
        old_id = wi_data.pop("id", None)
        wi_data["tenant_id"] = tenant_id
        wi_data["patient_id"] = id_maps["patients"].get(wi_data.get("patient_id"))
        if wi_data.get("created_by_user_id"):
            wi_data["created_by_user_id"] = id_maps["users"].get(wi_data.get("created_by_user_id"))
        wi_data["created_at"] = parse_datetime(wi_data.get("created_at"))
        wi_data["updated_at"] = parse_datetime(wi_data.get("updated_at"))
        if wi_data["patient_id"]:
            wi = models.ClinicalWorkItem(**wi_data)
            db.add(wi)
            await db.flush()
            if old_id:
                id_maps["clinical_work_items"][old_id] = wi.id
    imported_counts["clinical_work_items"] = len(data.get("clinical_work_items", []))

    # 28. Import ClinicalWorkItemTargets
    for cwit_data in data.get("clinical_work_item_targets", []):
        cwit_data.pop("id", None)
        cwit_data["tenant_id"] = tenant_id
        cwit_data["work_item_id"] = id_maps["clinical_work_items"].get(cwit_data.get("work_item_id"))
        cwit_data["created_at"] = parse_datetime(cwit_data.get("created_at"))
        if cwit_data["work_item_id"]:
            cwit = models.ClinicalWorkItemTarget(**cwit_data)
            db.add(cwit)
    imported_counts["clinical_work_item_targets"] = len(data.get("clinical_work_item_targets", []))

    # 29. Import ClinicalTreatmentPlans
    for tp_data in data.get("clinical_treatment_plans", []):
        old_id = tp_data.pop("id", None)
        tp_data["tenant_id"] = tenant_id
        tp_data["patient_id"] = id_maps["patients"].get(tp_data.get("patient_id"))
        if tp_data.get("created_by_user_id"):
            tp_data["created_by_user_id"] = id_maps["users"].get(tp_data.get("created_by_user_id"))
        tp_data["created_at"] = parse_datetime(tp_data.get("created_at"))
        tp_data["updated_at"] = parse_datetime(tp_data.get("updated_at"))
        if tp_data["patient_id"]:
            tp = models.ClinicalTreatmentPlan(**tp_data)
            db.add(tp)
            await db.flush()
            if old_id:
                id_maps["clinical_treatment_plans"][old_id] = tp.id
    imported_counts["clinical_treatment_plans"] = len(data.get("clinical_treatment_plans", []))

    # 30. Import ClinicalTreatmentPlanPhases
    for tpp_data in data.get("clinical_treatment_plan_phases", []):
        old_id = tpp_data.pop("id", None)
        tpp_data["tenant_id"] = tenant_id
        tpp_data["plan_id"] = id_maps["clinical_treatment_plans"].get(tpp_data.get("plan_id"))
        tpp_data["created_at"] = parse_datetime(tpp_data.get("created_at"))
        tpp_data["updated_at"] = parse_datetime(tpp_data.get("updated_at"))
        if tpp_data["plan_id"]:
            tpp = models.ClinicalTreatmentPlanPhase(**tpp_data)
            db.add(tpp)
            await db.flush()
            if old_id:
                id_maps["clinical_treatment_plan_phases"][old_id] = tpp.id
    imported_counts["clinical_treatment_plan_phases"] = len(data.get("clinical_treatment_plan_phases", []))

    # 31. Import ClinicalTreatmentPlanItems
    for tpi_data in data.get("clinical_treatment_plan_items", []):
        tpi_data.pop("id", None)
        tpi_data["tenant_id"] = tenant_id
        tpi_data["phase_id"] = id_maps["clinical_treatment_plan_phases"].get(tpi_data.get("phase_id"))
        tpi_data["work_item_id"] = id_maps["clinical_work_items"].get(tpi_data.get("work_item_id"))
        tpi_data["created_at"] = parse_datetime(tpi_data.get("created_at"))
        tpi_data["updated_at"] = parse_datetime(tpi_data.get("updated_at"))
        if tpi_data["phase_id"] and tpi_data["work_item_id"]:
            tpi = models.ClinicalTreatmentPlanItem(**tpi_data)
            db.add(tpi)
    imported_counts["clinical_treatment_plan_items"] = len(data.get("clinical_treatment_plan_items", []))

    # 32. Import CareSessions
    for cs_data in data.get("care_sessions", []):
        old_id = cs_data.pop("id", None)
        cs_data["tenant_id"] = tenant_id
        cs_data["patient_id"] = id_maps["patients"].get(cs_data.get("patient_id"))
        if cs_data.get("appointment_id"):
            cs_data["appointment_id"] = id_maps["appointments"].get(cs_data.get("appointment_id"))
        if cs_data.get("provider_user_id"):
            cs_data["provider_user_id"] = id_maps["users"].get(cs_data.get("provider_user_id"))
        cs_data["started_at"] = parse_datetime(cs_data.get("started_at"))
        cs_data["finished_at"] = parse_datetime(cs_data.get("finished_at"))
        cs_data["created_at"] = parse_datetime(cs_data.get("created_at"))
        cs_data["updated_at"] = parse_datetime(cs_data.get("updated_at"))
        if cs_data["patient_id"]:
            cs = models.CareSession(**cs_data)
            db.add(cs)
            await db.flush()
            if old_id:
                id_maps["care_sessions"][old_id] = cs.id
    imported_counts["care_sessions"] = len(data.get("care_sessions", []))

    # 33. Import CareSessionSteps
    for css_data in data.get("care_session_steps", []):
        old_id = css_data.pop("id", None)
        css_data["tenant_id"] = tenant_id
        css_data["care_session_id"] = id_maps["care_sessions"].get(css_data.get("care_session_id"))
        if css_data.get("work_item_id"):
            css_data["work_item_id"] = id_maps["clinical_work_items"].get(css_data.get("work_item_id"))
        css_data["started_at"] = parse_datetime(css_data.get("started_at"))
        css_data["completed_at"] = parse_datetime(css_data.get("completed_at"))
        css_data["created_at"] = parse_datetime(css_data.get("created_at"))
        css_data["updated_at"] = parse_datetime(css_data.get("updated_at"))
        if css_data["care_session_id"]:
            css = models.CareSessionStep(**css_data)
            db.add(css)
            await db.flush()
            if old_id:
                id_maps["care_session_steps"][old_id] = css.id
    imported_counts["care_session_steps"] = len(data.get("care_session_steps", []))

    # 34. Import CareObservations
    for co_data in data.get("care_observations", []):
        co_data.pop("id", None)
        co_data["tenant_id"] = tenant_id
        co_data["patient_id"] = id_maps["patients"].get(co_data.get("patient_id"))
        co_data["care_session_id"] = id_maps["care_sessions"].get(co_data.get("care_session_id"))
        if co_data.get("step_id"):
            co_data["step_id"] = id_maps["care_session_steps"].get(co_data.get("step_id"))
        if co_data.get("work_item_id"):
            co_data["work_item_id"] = id_maps["clinical_work_items"].get(co_data.get("work_item_id"))
        if co_data.get("recorded_by_user_id"):
            co_data["recorded_by_user_id"] = id_maps["users"].get(co_data.get("recorded_by_user_id"))
        co_data["recorded_at"] = parse_datetime(co_data.get("recorded_at"))
        co_data["created_at"] = parse_datetime(co_data.get("created_at"))
        if co_data["patient_id"] and co_data["care_session_id"]:
            co = models.CareObservation(**co_data)
            db.add(co)
    imported_counts["care_observations"] = len(data.get("care_observations", []))

    # 35. Import ClinicalEvents
    for ce_data in data.get("clinical_events", []):
        old_id = ce_data.pop("id", None)
        ce_data["tenant_id"] = tenant_id
        ce_data["patient_id"] = id_maps["patients"].get(ce_data.get("patient_id"))
        if ce_data.get("work_item_id"):
            ce_data["work_item_id"] = id_maps["clinical_work_items"].get(ce_data.get("work_item_id"))
        if ce_data.get("care_session_id"):
            ce_data["care_session_id"] = id_maps["care_sessions"].get(ce_data.get("care_session_id"))
        if ce_data.get("actor_user_id"):
            ce_data["actor_user_id"] = id_maps["users"].get(ce_data.get("actor_user_id"))
        ce_data["occurred_at"] = parse_datetime(ce_data.get("occurred_at"))
        ce_data["created_at"] = parse_datetime(ce_data.get("created_at"))
        if ce_data["patient_id"]:
            ce = models.ClinicalEvent(**ce_data)
            db.add(ce)
            await db.flush()
            if old_id:
                id_maps["clinical_events"][old_id] = ce.id
    imported_counts["clinical_events"] = len(data.get("clinical_events", []))

    # 36. Import ClinicalEventTargets
    for cet_data in data.get("clinical_event_targets", []):
        cet_data.pop("id", None)
        cet_data["tenant_id"] = tenant_id
        cet_data["event_id"] = id_maps["clinical_events"].get(cet_data.get("event_id"))
        cet_data["created_at"] = parse_datetime(cet_data.get("created_at"))
        if cet_data["event_id"]:
            cet = models.ClinicalEventTarget(**cet_data)
            db.add(cet)
    imported_counts["clinical_event_targets"] = len(data.get("clinical_event_targets", []))

    # 37. Import NextVisitRequests
    for nvr_data in data.get("next_visit_requests", []):
        nvr_data.pop("id", None)
        nvr_data["tenant_id"] = tenant_id
        nvr_data["patient_id"] = id_maps["patients"].get(nvr_data.get("patient_id"))
        if nvr_data.get("care_session_id"):
            nvr_data["care_session_id"] = id_maps["care_sessions"].get(nvr_data.get("care_session_id"))
        if nvr_data.get("work_item_id"):
            nvr_data["work_item_id"] = id_maps["clinical_work_items"].get(nvr_data.get("work_item_id"))
        if nvr_data.get("requested_by_user_id"):
            nvr_data["requested_by_user_id"] = id_maps["users"].get(nvr_data.get("requested_by_user_id"))
        nvr_data["preferred_time_window_start"] = parse_datetime(nvr_data.get("preferred_time_window_start"))
        nvr_data["preferred_time_window_end"] = parse_datetime(nvr_data.get("preferred_time_window_end"))
        nvr_data["created_at"] = parse_datetime(nvr_data.get("created_at"))
        nvr_data["updated_at"] = parse_datetime(nvr_data.get("updated_at"))
        if nvr_data["patient_id"]:
            nvr = models.NextVisitRequest(**nvr_data)
            db.add(nvr)
    imported_counts["next_visit_requests"] = len(data.get("next_visit_requests", []))

    # 38. Import ClinicalAttachmentLinks
    for cal_data in data.get("clinical_attachment_links", []):
        cal_data.pop("id", None)
        cal_data["tenant_id"] = tenant_id
        cal_data["attachment_id"] = id_maps["attachments"].get(cal_data.get("attachment_id"))
        cal_data["patient_id"] = id_maps["patients"].get(cal_data.get("patient_id"))
        if cal_data.get("work_item_id"):
            cal_data["work_item_id"] = id_maps["clinical_work_items"].get(cal_data.get("work_item_id"))
        if cal_data.get("care_session_id"):
            cal_data["care_session_id"] = id_maps["care_sessions"].get(cal_data.get("care_session_id"))
        if cal_data.get("clinical_event_id"):
            cal_data["clinical_event_id"] = id_maps["clinical_events"].get(cal_data.get("clinical_event_id"))
        cal_data["created_at"] = parse_datetime(cal_data.get("created_at"))
        if cal_data["attachment_id"] and cal_data["patient_id"]:
            cal = models.ClinicalAttachmentLink(**cal_data)
            db.add(cal)
    imported_counts["clinical_attachment_links"] = len(data.get("clinical_attachment_links", []))

    # 39. Import ClinicalProjectionCoverages
    for cpc_data in data.get("clinical_projection_coverages", []):
        cpc_data.pop("id", None)
        cpc_data["tenant_id"] = tenant_id
        cpc_data["patient_id"] = id_maps["patients"].get(cpc_data.get("patient_id"))
        cpc_data["created_at"] = parse_datetime(cpc_data.get("created_at"))
        cpc_data["updated_at"] = parse_datetime(cpc_data.get("updated_at"))
        if cpc_data["patient_id"]:
            cpc = models.ClinicalProjectionCoverage(**cpc_data)
            db.add(cpc)
    imported_counts["clinical_projection_coverages"] = len(data.get("clinical_projection_coverages", []))

    return imported_counts


async def restore_tenant_from_json(db: AsyncSession, tenant_id: int, json_content: str) -> Dict:
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
        deleted_counts = await delete_tenant_data(db, tenant_id)
    except Exception as e:
        await db.rollback()
        return {"success": False, "error": f"Failed to delete existing data: {str(e)}"}

    # 4. Import new data
    try:
        imported_counts = await import_tenant_data(db, tenant_id, backup_data)
        await db.commit()
    except Exception as e:
        await db.rollback()
        return {"success": False, "error": f"Failed to import data: {str(e)}"}

    return {
        "success": True,
        "deleted": deleted_counts,
        "imported": imported_counts,
        "backup_version": backup_data.get("version"),
        "backup_date": backup_data.get("exported_at"),
    }
