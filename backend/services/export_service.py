"""
Tenant Export Service

Exports all data belonging to a specific tenant as JSON for backup purposes.
This is separate from the full pg_dump which is reserved for Super Admin only.
"""

import json
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy import select

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
    if isinstance(value, Decimal):
        # Numeric columns yield Decimal; plain json.dumps would fail.
        return float(value)
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


async def export_tenant_data(db: AsyncSession, tenant_id: int) -> Dict:
    """
    Export all data for a specific tenant as a JSON-serializable dictionary.

    Args:
        db: Async database session
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
    res = await db.execute(
        select(models.User)
        .filter(models.User.tenant_id == tenant_id, models.User.is_deleted == False)
    )
    users = res.scalars().all()
    export_data["data"]["users"] = [
        model_to_dict(u, exclude_fields=["active_session_id"]) for u in users
    ]

    # 2. Patients
    res = await db.execute(
        select(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id, models.Patient.is_deleted == False)
    )
    patients = res.scalars().all()
    export_data["data"]["patients"] = [model_to_dict(p) for p in patients]

    # 3. Appointments
    res = await db.execute(
        select(models.Appointment)
        .join(models.Patient)
        .filter(
            models.Patient.tenant_id == tenant_id,
            models.Appointment.is_deleted == False,
        )
    )
    appointments = res.scalars().all()
    export_data["data"]["appointments"] = [model_to_dict(a) for a in appointments]

    # 4. Treatments
    res = await db.execute(
        select(models.Treatment).filter(models.Treatment.tenant_id == tenant_id)
    )
    treatments = res.scalars().all()
    export_data["data"]["treatments"] = [model_to_dict(t) for t in treatments]

    # 5. ToothStatus
    res = await db.execute(
        select(models.ToothStatus)
        .join(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id)
    )
    tooth_statuses = res.scalars().all()
    export_data["data"]["tooth_statuses"] = [model_to_dict(ts) for ts in tooth_statuses]

    # 6. Prescriptions
    res = await db.execute(
        select(models.Prescription)
        .join(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id)
    )
    prescriptions = res.scalars().all()
    export_data["data"]["prescriptions"] = [model_to_dict(p) for p in prescriptions]

    # 7. Attachments
    res = await db.execute(
        select(models.Attachment)
        .join(models.Patient)
        .filter(models.Patient.tenant_id == tenant_id)
    )
    attachments = res.scalars().all()
    export_data["data"]["attachments"] = [model_to_dict(a) for a in attachments]

    # 8. Payments
    res = await db.execute(
        select(models.Payment).filter(models.Payment.tenant_id == tenant_id)
    )
    payments = res.scalars().all()
    export_data["data"]["payments"] = [model_to_dict(p) for p in payments]

    # 9. Expenses
    res = await db.execute(
        select(models.Expense).filter(models.Expense.tenant_id == tenant_id)
    )
    expenses = res.scalars().all()
    export_data["data"]["expenses"] = [model_to_dict(e) for e in expenses]

    # 10. SalaryPayments
    res = await db.execute(
        select(models.SalaryPayment).filter(models.SalaryPayment.tenant_id == tenant_id)
    )
    salary_payments = res.scalars().all()
    export_data["data"]["salary_payments"] = [
        model_to_dict(sp) for sp in salary_payments
    ]

    # 11. Laboratories
    res = await db.execute(
        select(models.Laboratory).filter(models.Laboratory.tenant_id == tenant_id)
    )
    laboratories = res.scalars().all()
    export_data["data"]["laboratories"] = [model_to_dict(lab) for lab in laboratories]

    # 12. LabOrders
    res = await db.execute(
        select(models.LabOrder).filter(models.LabOrder.tenant_id == tenant_id)
    )
    lab_orders = res.scalars().all()
    export_data["data"]["lab_orders"] = [model_to_dict(lo) for lo in lab_orders]

    # 13. LabPayments (via Laboratory)
    from ..models.financial import LabPayment
    res = await db.execute(
        select(LabPayment).filter(LabPayment.tenant_id == tenant_id)
    )
    lab_payments = res.scalars().all()
    export_data["data"]["lab_payments"] = [model_to_dict(lp) for lp in lab_payments]

    # 14. Procedures
    res = await db.execute(
        select(models.Procedure).filter(models.Procedure.tenant_id == tenant_id)
    )
    procedures = res.scalars().all()
    export_data["data"]["procedures"] = [model_to_dict(p) for p in procedures]

    # 15. SavedMedications
    res = await db.execute(
        select(models.SavedMedication).filter(models.SavedMedication.tenant_id == tenant_id)
    )
    saved_medications = res.scalars().all()
    export_data["data"]["saved_medications"] = [
        model_to_dict(sm) for sm in saved_medications
    ]

    # 16. InsuranceProviders
    from ..models.price_list import InsuranceProvider, PriceList, PriceListItem
    res = await db.execute(
        select(InsuranceProvider).filter(InsuranceProvider.tenant_id == tenant_id)
    )
    insurance_providers = res.scalars().all()
    export_data["data"]["insurance_providers"] = [
        model_to_dict(ip) for ip in insurance_providers
    ]

    # 17. PriceLists
    res = await db.execute(
        select(PriceList).filter(PriceList.tenant_id == tenant_id)
    )
    price_lists = res.scalars().all()
    export_data["data"]["price_lists"] = [model_to_dict(pl) for pl in price_lists]

    # 18. PriceListItems (via PriceList)
    price_list_ids = [pl.id for pl in price_lists]
    if price_list_ids:
        res = await db.execute(
            select(PriceListItem).filter(PriceListItem.price_list_id.in_(price_list_ids))
        )
        price_list_items = res.scalars().all()
        export_data["data"]["price_list_items"] = [
            model_to_dict(pli) for pli in price_list_items
        ]
    else:
        export_data["data"]["price_list_items"] = []

    # 19. Warehouses
    res = await db.execute(
        select(models.Warehouse).filter(models.Warehouse.tenant_id == tenant_id)
    )
    warehouses = res.scalars().all()
    export_data["data"]["warehouses"] = [model_to_dict(w) for w in warehouses]

    # 20. Materials
    res = await db.execute(
        select(models.Material).filter(models.Material.tenant_id == tenant_id)
    )
    materials = res.scalars().all()
    export_data["data"]["materials"] = [model_to_dict(m) for m in materials]

    # 21. Batches
    res = await db.execute(
        select(models.Batch).filter(models.Batch.tenant_id == tenant_id)
    )
    batches = res.scalars().all()
    export_data["data"]["batches"] = [model_to_dict(b) for b in batches]

    # 22. StockItems
    res = await db.execute(
        select(models.StockItem).filter(models.StockItem.tenant_id == tenant_id)
    )
    stock_items = res.scalars().all()
    export_data["data"]["stock_items"] = [model_to_dict(si) for si in stock_items]

    # 23. MaterialSessions (via StockItem)
    stock_item_ids = [si.id for si in stock_items]
    if stock_item_ids:
        res = await db.execute(
            select(models.MaterialSession).filter(models.MaterialSession.stock_item_id.in_(stock_item_ids))
        )
        material_sessions = res.scalars().all()
        export_data["data"]["material_sessions"] = [
            model_to_dict(ms) for ms in material_sessions
        ]
    else:
        export_data["data"]["material_sessions"] = []

    # 24. StockMovements (via StockItem)
    if stock_item_ids:
        res = await db.execute(
            select(models.StockMovement).filter(models.StockMovement.stock_item_id.in_(stock_item_ids))
        )
        stock_movements = res.scalars().all()
        export_data["data"]["stock_movements"] = [
            model_to_dict(sm) for sm in stock_movements
        ]
    else:
        export_data["data"]["stock_movements"] = []

    # 25. ProcedureMaterialWeights
    res = await db.execute(
        select(models.ProcedureMaterialWeight).filter(models.ProcedureMaterialWeight.tenant_id == tenant_id)
    )
    procedure_material_weights = res.scalars().all()
    export_data["data"]["procedure_material_weights"] = [
        model_to_dict(pmw) for pmw in procedure_material_weights
    ]

    return export_data


async def export_tenant_to_json(db: AsyncSession, tenant_id: int) -> str:
    """
    Export tenant data as a JSON string.

    Args:
        db: Async database session
        tenant_id: The tenant ID to export data for

    Returns:
        JSON string of all tenant data
    """
    data = await export_tenant_data(db, tenant_id)
    return json.dumps(data, ensure_ascii=False, indent=2)
