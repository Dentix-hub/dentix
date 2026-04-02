"""
Router for Laboratory and Lab Order management
إدارة المعامل وطلبات التحاليل
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .. import models, schemas
from ..cache import cache_response, invalidate_cache
from .auth import get_current_user, get_db
from backend.core.permissions import Permission, require_permission

router = APIRouter()

# Prefix for linking lab orders to treatments
TREATMENT_LINK_PREFIX = "Link:LabOrder:"


def _get_lab_procedure_name(work_type: str, material: str = None) -> str:
    """Generate procedure name for lab work treatment"""
    if material:
        return f"عمل معمل: {work_type} - {material}"
    return f"عمل معمل: {work_type}"


# Helper function with caching
@cache_response(ttl_seconds=300)  # Cache for 5 minutes
def _get_cached_laboratories(db: Session, tenant_id: int):
    return (
        db.query(models.Laboratory)
        .filter(models.Laboratory.tenant_id == tenant_id)
        .order_by(models.Laboratory.name)
        .all()
    )


# ==================== Laboratory Endpoints ====================


@router.get("/laboratories/", response_model=List[schemas.Laboratory])
def get_laboratories(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Get all laboratories for current tenant (Cached for 5 min)"""
    return _get_cached_laboratories(db, current_user.tenant_id)


@router.post("/laboratories/", response_model=schemas.Laboratory)
def create_laboratory(
    lab: schemas.LaboratoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Create a new laboratory"""
    db_lab = models.Laboratory(**lab.model_dump(), tenant_id=current_user.tenant_id)
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    # Invalidate cache
    invalidate_cache("_get_cached_laboratories")
    return db_lab


@router.get("/laboratories/{lab_id}", response_model=schemas.Laboratory)
def get_laboratory(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single laboratory by ID"""
    lab = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.id == lab_id,
            models.Laboratory.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")
    return lab


@router.put("/laboratories/{lab_id}", response_model=schemas.Laboratory)
def update_laboratory(
    lab_id: int,
    lab_update: schemas.LaboratoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a laboratory"""
    lab = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.id == lab_id,
            models.Laboratory.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    update_data = lab_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lab, key, value)

    db.commit()
    db.refresh(lab)
    invalidate_cache("_get_cached_laboratories")
    return lab


@router.delete("/laboratories/{lab_id}")
def delete_laboratory(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Delete a laboratory"""
    lab = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.id == lab_id,
            models.Laboratory.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    db.delete(lab)
    db.commit()
    invalidate_cache("_get_cached_laboratories")
    return {"message": "Laboratory deleted successfully"}


# ==================== Lab Order Endpoints ====================


@router.get("/lab-orders/", response_model=List[schemas.LabOrder])
def get_lab_orders(
    laboratory_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all lab orders for current tenant with optional filtering"""
    query = db.query(models.LabOrder).filter(
        models.LabOrder.tenant_id == current_user.tenant_id
    )

    if laboratory_id:
        query = query.filter(models.LabOrder.laboratory_id == laboratory_id)

    if status:
        query = query.filter(models.LabOrder.status == status)

    orders = query.order_by(models.LabOrder.order_date.desc()).all()

    # Add patient and lab names
    result = []
    for order in orders:
        order_dict = schemas.LabOrder.model_validate(order).model_dump()
        order_dict["patient_name"] = order.patient.name if order.patient else None
        order_dict["laboratory_name"] = (
            order.laboratory.name if order.laboratory else None
        )
        result.append(order_dict)
    return result


@router.post("/lab-orders/", response_model=schemas.LabOrder)
def create_lab_order(
    order: schemas.LabOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Create a new lab order and automatically create linked treatment for billing"""
    # Verify patient exists and belongs to tenant
    patient = (
        db.query(models.Patient)
        .filter(
            models.Patient.id == order.patient_id,
            models.Patient.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Verify laboratory exists and belongs to tenant
    lab = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.id == order.laboratory_id,
            models.Laboratory.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    db_order = models.LabOrder(
        **order.model_dump(),
        tenant_id=current_user.tenant_id,
        doctor_id=current_user.id,  # Assign current user as the doctor
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # === Auto-create linked Treatment for billing ===
    if db_order.price_to_patient and db_order.price_to_patient > 0:
        # Parse tooth_number to int if possible
        tooth_num = None
        if db_order.tooth_number:
            try:
                # Take first tooth if multiple (e.g., "11,12,13" -> 11)
                tooth_num = int(db_order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass

        linked_treatment = models.Treatment(
            patient_id=db_order.patient_id,
            tooth_number=tooth_num,
            diagnosis=f"تركيبة معملية - {lab.name}",
            procedure=_get_lab_procedure_name(db_order.work_type, db_order.material),
            doctor_id=db_order.doctor_id,
            cost=db_order.price_to_patient,
            discount=0.0,
            date=db_order.order_date,
            notes=f"{TREATMENT_LINK_PREFIX}{db_order.id}",
        )
        db.add(linked_treatment)
        db.commit()

    # Return with names
    result = schemas.LabOrder.model_validate(db_order).model_dump()
    result["patient_name"] = patient.name
    result["laboratory_name"] = lab.name
    return result


@router.get("/lab-orders/{order_id}", response_model=schemas.LabOrder)
def get_lab_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single lab order by ID"""
    order = (
        db.query(models.LabOrder)
        .filter(
            models.LabOrder.id == order_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    result = schemas.LabOrder.model_validate(order).model_dump()
    result["patient_name"] = order.patient.name if order.patient else None
    result["laboratory_name"] = order.laboratory.name if order.laboratory else None
    return result


@router.put("/lab-orders/{order_id}", response_model=schemas.LabOrder)
def update_lab_order(
    order_id: int,
    order_update: schemas.LabOrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a lab order and sync linked treatment"""
    order = (
        db.query(models.LabOrder)
        .filter(
            models.LabOrder.id == order_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    update_data = order_update.model_dump(exclude_unset=True)

    # If status is changing to completed, set received_date
    if update_data.get("status") == "completed" and order.status != "completed":
        update_data["received_date"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(order, key, value)

    # Self-heal: If doctor_id is missing, assign current user
    if not order.doctor_id:
        order.doctor_id = current_user.id

    db.commit()
    db.refresh(order)

    # === Sync linked Treatment for billing ===
    link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
    linked_treatment = (
        db.query(models.Treatment)
        .filter(models.Treatment.notes.contains(link_note))
        .first()
    )

    if linked_treatment:
        # Update existing linked treatment
        linked_treatment.cost = order.price_to_patient or 0
        linked_treatment.procedure = _get_lab_procedure_name(
            order.work_type, order.material
        )
        linked_treatment.doctor_id = order.doctor_id  # Ensure doctor_id is synced
        if order.laboratory:
            linked_treatment.diagnosis = f"تركيبة معملية - {order.laboratory.name}"
        db.commit()
    elif order.price_to_patient and order.price_to_patient > 0:
        # Create new linked treatment if price was added
        tooth_num = None
        if order.tooth_number:
            try:
                tooth_num = int(order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass

        lab_name = order.laboratory.name if order.laboratory else "معمل"
        new_treatment = models.Treatment(
            patient_id=order.patient_id,
            tooth_number=tooth_num,
            diagnosis=f"تركيبة معملية - {lab_name}",
            procedure=_get_lab_procedure_name(order.work_type, order.material),
            doctor_id=order.doctor_id,
            cost=order.price_to_patient,
            discount=0.0,
            date=order.order_date,
            notes=link_note,
        )
        db.add(new_treatment)
        db.commit()

    result = schemas.LabOrder.model_validate(order).model_dump()
    result["patient_name"] = order.patient.name if order.patient else None
    result["laboratory_name"] = order.laboratory.name if order.laboratory else None
    return result


@router.delete("/lab-orders/{order_id}")
def delete_lab_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """Delete a lab order and its linked treatment"""
    order = (
        db.query(models.LabOrder)
        .filter(
            models.LabOrder.id == order_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    # === Delete linked Treatment ===
    link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
    linked_treatment = (
        db.query(models.Treatment)
        .filter(models.Treatment.notes.contains(link_note))
        .first()
    )
    if linked_treatment:
        db.delete(linked_treatment)

    db.delete(order)
    db.commit()
    return {"message": "Lab order deleted successfully"}


@router.get("/patients/{patient_id}/lab_orders", response_model=List[schemas.LabOrder])
def get_patient_lab_orders(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all lab orders for a specific patient"""
    # Verify patient exists and belongs to tenant
    patient = (
        db.query(models.Patient)
        .filter(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    orders = (
        db.query(models.LabOrder)
        .filter(models.LabOrder.patient_id == patient_id)
        .order_by(models.LabOrder.order_date.desc())
        .all()
    )

    result = []
    for order in orders:
        order_dict = schemas.LabOrder.model_validate(order).model_dump()
        order_dict["patient_name"] = patient.name
        order_dict["laboratory_name"] = (
            order.laboratory.name if order.laboratory else None
        )
        result.append(order_dict)
    return result


@router.get("/lab-orders/stats/summary")
def get_lab_orders_stats(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Get lab orders statistics"""
    from sqlalchemy import func

    base_query = db.query(models.LabOrder).filter(
        models.LabOrder.tenant_id == current_user.tenant_id
    )

    total_orders = base_query.count()
    pending_orders = base_query.filter(models.LabOrder.status == "pending").count()
    in_progress_orders = base_query.filter(
        models.LabOrder.status == "in_progress"
    ).count()
    completed_orders = base_query.filter(models.LabOrder.status == "completed").count()

    total_cost = (
        db.query(func.sum(models.LabOrder.cost))
        .filter(models.LabOrder.tenant_id == current_user.tenant_id)
        .scalar()
        or 0
    )

    total_revenue = (
        db.query(func.sum(models.LabOrder.price_to_patient))
        .filter(models.LabOrder.tenant_id == current_user.tenant_id)
        .scalar()
        or 0
    )

    total_labs = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.tenant_id == current_user.tenant_id,
            models.Laboratory.is_active == True,
        )
        .count()
    )

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "in_progress_orders": in_progress_orders,
        "completed_orders": completed_orders,
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "profit": total_revenue - total_cost,
        "total_labs": total_labs,
    }


# ==================== Lab Financials & Stats ====================


@router.get("/laboratories/{lab_id}/stats")
def get_lab_stats(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get detailed statistics for a specific laboratory including balance"""
    from sqlalchemy import func

    # Verify lab exists
    lab = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.id == lab_id,
            models.Laboratory.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    # 1. Orders Stats
    base_query = db.query(models.LabOrder).filter(
        models.LabOrder.laboratory_id == lab_id,
        models.LabOrder.tenant_id == current_user.tenant_id,
    )

    total_orders = base_query.count()
    pending_orders = base_query.filter(models.LabOrder.status == "pending").count()
    completed_orders = base_query.filter(models.LabOrder.status == "completed").count()

    # Financials from Orders
    total_cost = (
        db.query(func.sum(models.LabOrder.cost))
        .filter(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        .scalar()
        or 0.0
    )

    total_revenue = (
        db.query(func.sum(models.LabOrder.price_to_patient))
        .filter(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == current_user.tenant_id,
        )
        .scalar()
        or 0.0
    )

    # 2. Payments Stats
    total_paid = (
        db.query(func.sum(models.LabPayment.amount))
        .filter(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == current_user.tenant_id,
        )
        .scalar()
        or 0.0
    )

    # Balance: Cost (what we owe lab) - Paid (what we paid)
    # Positive balance means we owe money. Negative means we overpaid (credit).
    balance = total_cost - total_paid

    return {
        "lab_id": lab_id,
        "lab_name": lab.name,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "total_cost": total_cost,  # Lab Fees
        "total_revenue": total_revenue,  # Collected from Patients
        "total_paid": total_paid,
        "balance": balance,
    }


@router.post("/laboratories/{lab_id}/payments", response_model=schemas.LabPayment)
def create_lab_payment(
    lab_id: int,
    payment: schemas.LabPaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Record a payment to a laboratory"""
    # Verify lab exists
    lab = (
        db.query(models.Laboratory)
        .filter(
            models.Laboratory.id == lab_id,
            models.Laboratory.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    db_payment = models.LabPayment(
        **payment.model_dump(), tenant_id=current_user.tenant_id
    )
    # Ensure lab_id matches URL
    db_payment.laboratory_id = lab_id

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/laboratories/{lab_id}/payments", response_model=List[schemas.LabPayment])
def get_lab_payments(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get payment history for a laboratory"""
    payments = (
        db.query(models.LabPayment)
        .filter(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == current_user.tenant_id,
        )
        .order_by(models.LabPayment.date.desc())
        .all()
    )
    return payments
