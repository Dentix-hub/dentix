"""
Lab Service

Central service for laboratory and lab order operations:
- Laboratory CRUD
- Lab order lifecycle (create → send → receive → complete)
- Lab order ↔ treatment synchronization for billing
- Lab payments and balance tracking
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

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

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # --- Laboratory CRUD ---

    async def get_laboratories(self) -> List[models.Laboratory]:
        stmt = (
            select(models.Laboratory)
            .where(models.Laboratory.tenant_id == self.tenant_id)
            .order_by(models.Laboratory.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_laboratory(self, lab_id: int) -> Optional[models.Laboratory]:
        stmt = select(models.Laboratory).where(
            models.Laboratory.id == lab_id,
            models.Laboratory.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_laboratory(self, data: schemas.LaboratoryCreate) -> models.Laboratory:
        lab = models.Laboratory(**data.model_dump(), tenant_id=self.tenant_id)
        self.db.add(lab)
        await self.db.commit()
        await self.db.refresh(lab)
        return lab

    async def update_laboratory(
        self, lab_id: int, data: schemas.LaboratoryUpdate
    ) -> models.Laboratory:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(lab, key, value)

        await self.db.commit()
        await self.db.refresh(lab)
        return lab

    async def delete_laboratory(self, lab_id: int) -> bool:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")
        await self.db.delete(lab)
        await self.db.commit()
        return True

    # --- Lab Orders ---

    async def get_lab_orders(
        self, laboratory_id: int = None, status: str = None
    ) -> List[models.LabOrder]:
        stmt = select(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id
        )
        if laboratory_id:
            stmt = stmt.where(models.LabOrder.laboratory_id == laboratory_id)
        if status:
            stmt = stmt.where(models.LabOrder.status == status)
        stmt = stmt.order_by(models.LabOrder.order_date.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_lab_order(self, order_id: int) -> Optional[models.LabOrder]:
        stmt = select(models.LabOrder).where(
            models.LabOrder.id == order_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_lab_order(
        self, data: schemas.LabOrderCreate, doctor_id: int
    ) -> models.LabOrder:
        """Create lab order with automatic linked treatment for billing."""
        # Verify patient
        stmt_patient = select(models.Patient).where(
            models.Patient.id == data.patient_id,
            models.Patient.tenant_id == self.tenant_id,
        )
        res_patient = await self.db.execute(stmt_patient)
        patient = res_patient.scalars().first()
        if not patient:
            raise ValueError("Patient not found")

        # Verify laboratory
        stmt_lab = select(models.Laboratory).where(
            models.Laboratory.id == data.laboratory_id,
            models.Laboratory.tenant_id == self.tenant_id,
        )
        res_lab = await self.db.execute(stmt_lab)
        lab = res_lab.scalars().first()
        if not lab:
            raise ValueError("Laboratory not found")

        db_order = models.LabOrder(
            **data.model_dump(),
            tenant_id=self.tenant_id,
            doctor_id=doctor_id,
        )
        self.db.add(db_order)
        await self.db.commit()
        await self.db.refresh(db_order)

        # Auto-create linked treatment
        if db_order.price_to_patient and db_order.price_to_patient > 0:
            await self._create_linked_treatment(db_order, lab)

        return db_order

    async def update_lab_order(
        self, order_id: int, data: schemas.LabOrderUpdate
    ) -> models.LabOrder:
        """Update lab order and sync linked treatment."""
        order = await self.get_lab_order(order_id)
        if not order:
            raise ValueError("Lab order not found")

        update_data = data.model_dump(exclude_unset=True)

        # If status changes to completed, set received_date
        if update_data.get("status") == "completed" and order.status != "completed":
            update_data["received_date"] = datetime.now(timezone.utc)

        for key, value in update_data.items():
            setattr(order, key, value)

        if not order.doctor_id:
            order.doctor_id = order.doctor_id

        await self.db.commit()
        await self.db.refresh(order)

        # Sync linked treatment
        await self._sync_linked_treatment(order)

        return order

    async def delete_lab_order(self, order_id: int) -> bool:
        """Delete lab order and its linked treatment."""
        order = await self.get_lab_order(order_id)
        if not order:
            raise ValueError("Lab order not found")

        # Delete linked treatment
        link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
        stmt_treatment = select(models.Treatment).where(
            models.Treatment.notes.contains(link_note)
        )
        res_treatment = await self.db.execute(stmt_treatment)
        linked_treatment = res_treatment.scalars().first()
        if linked_treatment:
            await self.db.delete(linked_treatment)

        await self.db.delete(order)
        await self.db.commit()
        return True

    async def get_patient_lab_orders(self, patient_id: int) -> List[models.LabOrder]:
        stmt = (
            select(models.LabOrder)
            .where(models.LabOrder.patient_id == patient_id)
            .order_by(models.LabOrder.order_date.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # --- Linked Treatment Sync ---

    async def _create_linked_treatment(self, order: models.LabOrder, lab: models.Laboratory):
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
        await self.db.commit()

    async def _sync_linked_treatment(self, order: models.LabOrder):
        """Update or create linked treatment for lab order."""
        link_note = f"{TREATMENT_LINK_PREFIX}{order.id}"
        stmt_treatment = select(models.Treatment).where(
            models.Treatment.notes.contains(link_note)
        )
        res_treatment = await self.db.execute(stmt_treatment)
        linked_treatment = res_treatment.scalars().first()

        if linked_treatment:
            linked_treatment.cost = order.price_to_patient or 0
            linked_treatment.procedure = _get_lab_procedure_name(
                order.work_type, order.material
            )
            linked_treatment.doctor_id = order.doctor_id
            if order.laboratory:
                linked_treatment.diagnosis = f"تركيبة معملية - {order.laboratory.name}"
            await self.db.commit()
        elif order.price_to_patient and order.price_to_patient > 0:
            tooth_num = None
            if order.tooth_number:
                try:
                    tooth_num = int(order.tooth_number.split(",")[0].strip())
                except (ValueError, AttributeError):
                    pass

            # Make sure lab is loaded
            lab_name = "معمل"
            if order.laboratory_id:
                stmt_lab = select(models.Laboratory).where(
                    models.Laboratory.id == order.laboratory_id
                )
                res_lab = await self.db.execute(stmt_lab)
                lab = res_lab.scalars().first()
                if lab:
                    lab_name = lab.name

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
            await self.db.commit()

    # --- Statistics ---

    async def get_stats_summary(self) -> Dict[str, Any]:
        # Total orders count
        stmt_total = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id
        )
        res_total = await self.db.execute(stmt_total)
        total_orders = res_total.scalar() or 0

        # Pending count
        stmt_pending = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "pending"
        )
        res_pending = await self.db.execute(stmt_pending)
        pending_orders = res_pending.scalar() or 0

        # In progress count
        stmt_ip = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "in_progress"
        )
        res_ip = await self.db.execute(stmt_ip)
        in_progress = res_ip.scalar() or 0

        # Completed count
        stmt_comp = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "completed"
        )
        res_comp = await self.db.execute(stmt_comp)
        completed = res_comp.scalar() or 0

        # Total cost
        stmt_cost = select(func.sum(models.LabOrder.cost)).where(
            models.LabOrder.tenant_id == self.tenant_id
        )
        res_cost = await self.db.execute(stmt_cost)
        total_cost = res_cost.scalar() or 0

        # Total revenue
        stmt_rev = select(func.sum(models.LabOrder.price_to_patient)).where(
            models.LabOrder.tenant_id == self.tenant_id
        )
        res_rev = await self.db.execute(stmt_rev)
        total_revenue = res_rev.scalar() or 0

        # Total active labs
        stmt_labs = select(func.count()).select_from(models.Laboratory).where(
            models.Laboratory.tenant_id == self.tenant_id,
            models.Laboratory.is_active == True
        )
        res_labs = await self.db.execute(stmt_labs)
        total_labs = res_labs.scalar() or 0

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

    async def get_lab_stats(self, lab_id: int) -> Dict[str, Any]:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        # Total orders
        stmt_total = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id
        )
        res_total = await self.db.execute(stmt_total)
        total_orders = res_total.scalar() or 0

        # Pending orders
        stmt_pending = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "pending"
        )
        res_pending = await self.db.execute(stmt_pending)
        pending = res_pending.scalar() or 0

        # Completed orders
        stmt_completed = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "completed"
        )
        res_completed = await self.db.execute(stmt_completed)
        completed = res_completed.scalar() or 0

        # Total cost
        stmt_cost = select(func.sum(models.LabOrder.cost)).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )
        res_cost = await self.db.execute(stmt_cost)
        total_cost = res_cost.scalar() or 0.0

        # Total revenue
        stmt_rev = select(func.sum(models.LabOrder.price_to_patient)).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )
        res_rev = await self.db.execute(stmt_rev)
        total_revenue = res_rev.scalar() or 0.0

        # Total paid
        stmt_paid = select(func.sum(models.LabPayment.amount)).where(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == self.tenant_id,
        )
        res_paid = await self.db.execute(stmt_paid)
        total_paid = res_paid.scalar() or 0.0

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

    async def create_lab_payment(
        self, lab_id: int, data: schemas.LabPaymentCreate
    ) -> models.LabPayment:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        payment = models.LabPayment(
            **data.model_dump(),
            tenant_id=self.tenant_id,
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_lab_payments(self, lab_id: int) -> List[models.LabPayment]:
        stmt = (
            select(models.LabPayment)
            .where(
                models.LabPayment.laboratory_id == lab_id,
                models.LabPayment.tenant_id == self.tenant_id,
            )
            .order_by(models.LabPayment.date.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


async def get_lab_service(db: AsyncSession, tenant_id: int) -> LabService:
    return LabService(db, tenant_id)
