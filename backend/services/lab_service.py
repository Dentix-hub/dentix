"""
Lab Service

Central service for laboratory and lab order operations:
- Laboratory CRUD
- Lab order lifecycle (create → send → receive → complete)
- Lab order ↔ treatment synchronization for billing
- Lab payments and balance tracking
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend import models, schemas

logger = logging.getLogger(__name__)

TREATMENT_LINK_PREFIX = "Link:LabOrder:"


def _get_lab_procedure_name(work_type: str, material: str = None) -> str:
    """Generate procedure name for lab work treatment."""
    if material:
        return f"عمل معمل: {work_type} - {material}"
    return f"عمل معمل: {work_type}"


class LabService:
    """Central lab logic - SINGLE SOURCE OF TRUTH."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # --- Laboratory CRUD ---

    def get_laboratories(self) -> List[models.Laboratory]:
        return (
            self.db.query(models.Laboratory)
            .filter(models.Laboratory.tenant_id == self.tenant_id)
            .order_by(models.Laboratory.name)
            .all()
        )

    def get_laboratory(self, lab_id: int) -> Optional[models.Laboratory]:
        return (
            self.db.query(models.Laboratory)
            .filter(
                models.Laboratory.id == lab_id,
                models.Laboratory.tenant_id == self.tenant_id,
            )
            .first()
        )

    def create_laboratory(self, data: schemas.LaboratoryCreate) -> models.Laboratory:
        lab = models.Laboratory(**data.model_dump(), tenant_id=self.tenant_id)
        self.db.add(lab)
        self.db.commit()
        self.db.refresh(lab)
        return lab

    def update_laboratory(
        self, lab_id: int, data: schemas.LaboratoryUpdate
    ) -> models.Laboratory:
        lab = self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(lab, key, value)

        self.db.commit()
        self.db.refresh(lab)
        return lab

    def delete_laboratory(self, lab_id: int) -> bool:
        lab = self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")
        self.db.delete(lab)
        self.db.commit()
        return True

    # --- Lab Orders ---

    def get_lab_orders(
        self, laboratory_id: int = None, status: str = None
    ) -> List[models.LabOrder]:
        query = self.db.query(models.LabOrder).filter(
            models.LabOrder.tenant_id == self.tenant_id
        )
        if laboratory_id:
            query = query.filter(models.LabOrder.laboratory_id == laboratory_id)
        if status:
            query = query.filter(models.LabOrder.status == status)
        return query.order_by(models.LabOrder.order_date.desc()).all()

    def get_lab_order(self, order_id: int) -> Optional[models.LabOrder]:
        return (
            self.db.query(models.LabOrder)
            .filter(
                models.LabOrder.id == order_id,
                models.LabOrder.tenant_id == self.tenant_id,
            )
            .first()
        )

    def create_lab_order(
        self, data: schemas.LabOrderCreate, doctor_id: int
    ) -> models.LabOrder:
        """Create lab order with automatic linked treatment for billing."""
        # Verify patient
        patient = (
            self.db.query(models.Patient)
            .filter(
                models.Patient.id == data.patient_id,
                models.Patient.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not patient:
            raise ValueError("Patient not found")

        # Verify laboratory
        lab = (
            self.db.query(models.Laboratory)
            .filter(
                models.Laboratory.id == data.laboratory_id,
                models.Laboratory.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not lab:
            raise ValueError("Laboratory not found")

        db_order = models.LabOrder(
            **data.model_dump(),
            tenant_id=self.tenant_id,
            doctor_id=doctor_id,
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)

        # Auto-create linked treatment
        if db_order.price_to_patient and db_order.price_to_patient > 0:
            self._create_linked_treatment(db_order, lab)

        return db_order

    def update_lab_order(
        self, order_id: int, data: schemas.LabOrderUpdate
    ) -> models.LabOrder:
        """Update lab order and sync linked treatment."""
        order = self.get_lab_order(order_id)
        if not order:
            raise ValueError("Lab order not found")

        update_data = data.model_dump(exclude_unset=True)

        # If status changes to completed, set received_date
        if update_data.get("status") == "completed" and order.status != "completed":
            update_data["received_date"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(order, key, value)

        if not order.doctor_id:
            order.doctor_id = order.doctor_id

        self.db.commit()
        self.db.refresh(order)

        # Sync linked treatment
        self._sync_linked_treatment(order)

        return order

    def delete_lab_order(self, order_id: int) -> bool:
        """Delete lab order and its linked treatment."""
        order = self.get_lab_order(order_id)
        if not order:
            raise ValueError("Lab order not found")

        # Delete linked treatment
        link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
        linked_treatment = (
            self.db.query(models.Treatment)
            .filter(models.Treatment.notes.contains(link_note))
            .first()
        )
        if linked_treatment:
            self.db.delete(linked_treatment)

        self.db.delete(order)
        self.db.commit()
        return True

    def get_patient_lab_orders(self, patient_id: int) -> List[models.LabOrder]:
        return (
            self.db.query(models.LabOrder)
            .filter(models.LabOrder.patient_id == patient_id)
            .order_by(models.LabOrder.order_date.desc())
            .all()
        )

    # --- Linked Treatment Sync ---

    def _create_linked_treatment(self, order: models.LabOrder, lab: models.Laboratory):
        """Create a linked treatment for lab order billing."""
        tooth_num = None
        if order.tooth_number:
            try:
                tooth_num = int(order.tooth_number.split(",")[0].strip())
            except (ValueError, AttributeError):
                pass

        linked_treatment = models.Treatment(
            patient_id=order.patient_id,
            tooth_number=tooth_num,
            diagnosis=f"تركيبة معملية - {lab.name}",
            procedure=_get_lab_procedure_name(order.work_type, order.material),
            doctor_id=order.doctor_id,
            cost=order.price_to_patient,
            discount=0.0,
            date=order.order_date,
            notes=f"{TREATMENT_LINK_PREFIX}{order.id}",
        )
        self.db.add(linked_treatment)
        self.db.commit()

    def _sync_linked_treatment(self, order: models.LabOrder):
        """Update or create linked treatment for lab order."""
        link_note = f"{TREATMENT_LINK_PREFIX}{order.id}"
        linked_treatment = (
            self.db.query(models.Treatment)
            .filter(models.Treatment.notes.contains(link_note))
            .first()
        )

        if linked_treatment:
            linked_treatment.cost = order.price_to_patient or 0
            linked_treatment.procedure = _get_lab_procedure_name(
                order.work_type, order.material
            )
            linked_treatment.doctor_id = order.doctor_id
            if order.laboratory:
                linked_treatment.diagnosis = f"تركيبة معملية - {order.laboratory.name}"
            self.db.commit()
        elif order.price_to_patient and order.price_to_patient > 0:
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
            self.db.add(new_treatment)
            self.db.commit()

    # --- Statistics ---

    def get_stats_summary(self) -> Dict[str, Any]:
        base_query = self.db.query(models.LabOrder).filter(
            models.LabOrder.tenant_id == self.tenant_id
        )

        total_orders = base_query.count()
        pending_orders = base_query.filter(models.LabOrder.status == "pending").count()
        in_progress = base_query.filter(models.LabOrder.status == "in_progress").count()
        completed = base_query.filter(models.LabOrder.status == "completed").count()

        total_cost = (
            self.db.query(func.sum(models.LabOrder.cost))
            .filter(models.LabOrder.tenant_id == self.tenant_id)
            .scalar()
            or 0
        )
        total_revenue = (
            self.db.query(func.sum(models.LabOrder.price_to_patient))
            .filter(models.LabOrder.tenant_id == self.tenant_id)
            .scalar()
            or 0
        )
        total_labs = (
            self.db.query(models.Laboratory)
            .filter(
                models.Laboratory.tenant_id == self.tenant_id,
                models.Laboratory.is_active,
            )
            .count()
        )

        return {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "in_progress_orders": in_progress,
            "completed_orders": completed,
            "total_cost": float(total_cost),
            "total_revenue": float(total_revenue),
            "profit": float(total_revenue - total_cost),
            "total_labs": total_labs,
        }

    def get_lab_stats(self, lab_id: int) -> Dict[str, Any]:
        lab = self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        base_query = self.db.query(models.LabOrder).filter(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )

        total_orders = base_query.count()
        pending = base_query.filter(models.LabOrder.status == "pending").count()
        completed = base_query.filter(models.LabOrder.status == "completed").count()

        total_cost = (
            self.db.query(func.sum(models.LabOrder.cost))
            .filter(
                models.LabOrder.laboratory_id == lab_id,
                models.LabOrder.tenant_id == self.tenant_id,
            )
            .scalar()
            or 0.0
        )
        total_revenue = (
            self.db.query(func.sum(models.LabOrder.price_to_patient))
            .filter(
                models.LabOrder.laboratory_id == lab_id,
                models.LabOrder.tenant_id == self.tenant_id,
            )
            .scalar()
            or 0.0
        )
        total_paid = (
            self.db.query(func.sum(models.LabPayment.amount))
            .filter(
                models.LabPayment.laboratory_id == lab_id,
                models.LabPayment.tenant_id == self.tenant_id,
            )
            .scalar()
            or 0.0
        )

        return {
            "lab_id": lab_id,
            "lab_name": lab.name,
            "total_orders": total_orders,
            "pending_orders": pending,
            "completed_orders": completed,
            "total_cost": float(total_cost),
            "total_revenue": float(total_revenue),
            "total_paid": float(total_paid),
            "balance": float(total_cost - total_paid),
        }

    # --- Payments ---

    def create_lab_payment(
        self, lab_id: int, data: schemas.LabPaymentCreate
    ) -> models.LabPayment:
        lab = self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        payment = models.LabPayment(
            **data.model_dump(),
            tenant_id=self.tenant_id,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_lab_payments(self, lab_id: int) -> List[models.LabPayment]:
        return (
            self.db.query(models.LabPayment)
            .filter(
                models.LabPayment.laboratory_id == lab_id,
                models.LabPayment.tenant_id == self.tenant_id,
            )
            .order_by(models.LabPayment.date.desc())
            .all()
        )


def get_lab_service(db: Session, tenant_id: int) -> LabService:
    return LabService(db, tenant_id)
