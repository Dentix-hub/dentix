"""
Tenant Export Service

Exports all data belonging to a specific tenant as JSON for backup purposes.
This is separate from the full pg_dump which is reserved for Super Admin only.
"""

import json
from datetime import datetime, date, timezone
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect

from .. import models


def serialize_value(value: Any) -> Any:
    """Convert SQLAlchemy values to JSON-serializable types."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def model_to_dict(obj: Any, exclude_fields: List[str] = None) -> Dict:
    """Convert SQLAlchemy model instance to dictionary."""
    if obj is None:
        return None

    exclude_fields = exclude_fields or []
    mapper = inspect(obj.__class__)

    result = {}
    for column in mapper.columns:
        if column.key not in exclude_fields:
            value = getattr(obj, column.key)
            result[column.key] = serialize_value(value)

    return result


def export_tenant_data(db: Session, tenant_id: int) -> Dict:
    """
    Export all data for a specific tenant as a JSON-serializable dictionary.

    Args:
        db: Database session
        tenant_id: The tenant ID to export data for

    Returns:
        Dictionary containing all tenant data
    """
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "data": {},
    }

    # 1. Users (tenant staff)
    users = (
        db.query(models.User)
        .filter(models.User.tenant_id == tenant_id, models.User.is_deleted == False)  # noqa: E712
        .all()
    )
    export_data["data"]["users"] = [
        model_to_dict(u, exclude_fields=["active_session_id"]) for u in users
    ]

    # 2. Patients
    patients = (
        db.query(models.Patient)
        .filter(
            models.Patient.tenant_id == tenant_id, models.Patient.is_deleted == False  # noqa: E712
        )
        .all()
    )
    export_data["data"]["patients"] = [model_to_dict(p) for p in patients]

    # 3. Appointments
    appointments = (
        db.query(models.Appointment)
        .join(models.Patient)
        .filter(
            models.Patient.tenant_id == tenant_id,
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        .all()
    )
    export_data["data"]["appointments"] = [model_to_dict(a) for a in appointments]

    # 4. Treatments
    treatments = (
        db.query(models.Treatment).filter(models.Treatment.tenant_id == tenant_id).all()
    )
    export_data["data"]["treatments"] = [model_to_dict(t) for t in treatments]

    # 5. ToothStatus
    tooth_statuses = (
        db.query(models.ToothStatus)
        .join(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["tooth_statuses"] = [model_to_dict(ts) for ts in tooth_statuses]

    # 6. Prescriptions
    prescriptions = (
        db.query(models.Prescription)
        .join(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["prescriptions"] = [model_to_dict(p) for p in prescriptions]

    # 7. Attachments
    attachments = (
        db.query(models.Attachment)
        .join(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["attachments"] = [model_to_dict(a) for a in attachments]

    # 8. Payments
    payments = (
        db.query(models.Payment).filter(models.Payment.tenant_id == tenant_id).all()
    )
    export_data["data"]["payments"] = [model_to_dict(p) for p in payments]

    # 9. Expenses
    expenses = (
        db.query(models.Expense).filter(models.Expense.tenant_id == tenant_id).all()
    )
    export_data["data"]["expenses"] = [model_to_dict(e) for e in expenses]

    # 10. SalaryPayments
    salary_payments = (
        db.query(models.SalaryPayment)
        .filter(models.SalaryPayment.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["salary_payments"] = [
        model_to_dict(sp) for sp in salary_payments
    ]

    # 11. Laboratories
    laboratories = (
        db.query(models.Laboratory)
        .filter(models.Laboratory.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["laboratories"] = [model_to_dict(lab) for lab in laboratories]

    # 12. LabOrders
    lab_orders = (
        db.query(models.LabOrder).filter(models.LabOrder.tenant_id == tenant_id).all()
    )
    export_data["data"]["lab_orders"] = [model_to_dict(lo) for lo in lab_orders]

    # 13. LabPayments (via Laboratory)
    from ..models.financial import LabPayment

    lab_payments = db.query(LabPayment).filter(LabPayment.tenant_id == tenant_id).all()
    export_data["data"]["lab_payments"] = [model_to_dict(lp) for lp in lab_payments]

    # 14. Procedures
    procedures = (
        db.query(models.Procedure).filter(models.Procedure.tenant_id == tenant_id).all()
    )
    export_data["data"]["procedures"] = [model_to_dict(p) for p in procedures]

    # 15. SavedMedications
    saved_medications = (
        db.query(models.SavedMedication)
        .filter(models.SavedMedication.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["saved_medications"] = [
        model_to_dict(sm) for sm in saved_medications
    ]

    # 16. InsuranceProviders
    from ..models.price_list import InsuranceProvider, PriceList, PriceListItem

    insurance_providers = (
        db.query(InsuranceProvider)
        .filter(InsuranceProvider.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["insurance_providers"] = [
        model_to_dict(ip) for ip in insurance_providers
    ]

    # 17. PriceLists
    price_lists = db.query(PriceList).filter(PriceList.tenant_id == tenant_id).all()
    export_data["data"]["price_lists"] = [model_to_dict(pl) for pl in price_lists]

    # 18. PriceListItems (via PriceList)
    price_list_ids = [pl.id for pl in price_lists]
    if price_list_ids:
        price_list_items = (
            db.query(PriceListItem)
            .filter(PriceListItem.price_list_id.in_(price_list_ids))
            .all()
        )
        export_data["data"]["price_list_items"] = [
            model_to_dict(pli) for pli in price_list_items
        ]
    else:
        export_data["data"]["price_list_items"] = []

    # 19. Warehouses
    warehouses = (
        db.query(models.Warehouse).filter(models.Warehouse.tenant_id == tenant_id).all()
    )
    export_data["data"]["warehouses"] = [model_to_dict(w) for w in warehouses]

    # 20. Materials
    materials = (
        db.query(models.Material).filter(models.Material.tenant_id == tenant_id).all()
    )
    export_data["data"]["materials"] = [model_to_dict(m) for m in materials]

    # 21. Batches
    batches = db.query(models.Batch).filter(models.Batch.tenant_id == tenant_id).all()
    export_data["data"]["batches"] = [model_to_dict(b) for b in batches]

    # 22. StockItems
    stock_items = (
        db.query(models.StockItem).filter(models.StockItem.tenant_id == tenant_id).all()
    )
    export_data["data"]["stock_items"] = [model_to_dict(si) for si in stock_items]

    # 23. MaterialSessions (via StockItem)
    stock_item_ids = [si.id for si in stock_items]
    if stock_item_ids:
        material_sessions = (
            db.query(models.MaterialSession)
            .filter(models.MaterialSession.stock_item_id.in_(stock_item_ids))
            .all()
        )
        export_data["data"]["material_sessions"] = [
            model_to_dict(ms) for ms in material_sessions
        ]
    else:
        export_data["data"]["material_sessions"] = []

    # 24. StockMovements (via StockItem)
    if stock_item_ids:
        stock_movements = (
            db.query(models.StockMovement)
            .filter(models.StockMovement.stock_item_id.in_(stock_item_ids))
            .all()
        )
        export_data["data"]["stock_movements"] = [
            model_to_dict(sm) for sm in stock_movements
        ]
    else:
        export_data["data"]["stock_movements"] = []

    # 25. ProcedureMaterialWeights
    procedure_material_weights = (
        db.query(models.ProcedureMaterialWeight)
        .filter(models.ProcedureMaterialWeight.tenant_id == tenant_id)
        .all()
    )
    export_data["data"]["procedure_material_weights"] = [
        model_to_dict(pmw) for pmw in procedure_material_weights
    ]

    return export_data


def export_tenant_to_json(db: Session, tenant_id: int) -> str:
    """
    Export tenant data as a JSON string.

    Args:
        db: Database session
        tenant_id: The tenant ID to export data for

    Returns:
        JSON string of all tenant data
    """
    data = export_tenant_data(db, tenant_id)
    return json.dumps(data, ensure_ascii=False, indent=2)
