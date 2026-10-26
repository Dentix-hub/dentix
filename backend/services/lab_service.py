"""
Lab Service

Central service for laboratory and lab order operations:
- Laboratory CRUD
- Lab order lifecycle (create → send → receive → complete)
- Lab order ↔ treatment synchronization for billing
- Lab payments and balance tracking
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from backend import models, schemas
from backend.core.money import as_decimal, quantize_money
from backend.utils.tenant_time import utc_now_naive

logger = logging.getLogger(__name__)

TREATMENT_LINK_PREFIX = "Link:LabOrder:"


async def get_order_payment_map(
    db: AsyncSession, tenant_id: int, order_ids: Sequence[int]
) -> dict[int, Decimal]:
    """Single grouped query summing payments per lab_order_id. Prevents N+1."""
    if not order_ids:
        return {}
    stmt = (
        select(
            models.LabPayment.lab_order_id,
            func.coalesce(func.sum(models.LabPayment.amount), 0),
        )
        .where(
            models.LabPayment.tenant_id == tenant_id,
            models.LabPayment.lab_order_id.in_(order_ids),
        )
        .group_by(models.LabPayment.lab_order_id)
    )
    rows = (await db.execute(stmt)).all()
    return {
        order_id: quantize_money(as_decimal(total_paid))
        for order_id, total_paid in rows
        if order_id is not None
    }


def compute_order_payment_fields(
    cost: Any,
    paid_amount: Any,
    status: Optional[str],
) -> tuple[Decimal, Decimal, str]:
    """Derive paid_amount, remaining_amount, payment_status according to accounting rules."""
    cost_d = quantize_money(as_decimal(cost))
    paid_d = quantize_money(as_decimal(paid_amount))
    is_cancelled = (status or "").lower() == "cancelled"

    if is_cancelled:
        payment_status = "cancelled"
        remaining_d = Decimal("0.00")
    elif cost_d <= Decimal("0.00"):
        payment_status = "no_cost"
        remaining_d = Decimal("0.00")
    elif paid_d >= cost_d:
        payment_status = "paid"
        remaining_d = Decimal("0.00")
    elif paid_d > Decimal("0.00"):
        payment_status = "partial"
        remaining_d = quantize_money(cost_d - paid_d)
    else:
        payment_status = "unpaid"
        remaining_d = quantize_money(cost_d)

    return paid_d, remaining_d, payment_status


def format_lab_order_dict(
    order: models.LabOrder,
    paid_amount: Decimal | None = None,
    patient_name: str | None = None,
    laboratory_name: str | None = None,
    is_existing: bool | None = None,
) -> dict:
    """Serialize a LabOrder ORM instance to a dict matching schemas.LabOrder with derived fields."""
    order_dict = schemas.LabOrder.model_validate(order).model_dump()
    paid_d, remaining_d, payment_status = compute_order_payment_fields(
        order.cost, paid_amount, order.status
    )
    order_dict["paid_amount"] = float(paid_d)
    order_dict["remaining_amount"] = float(remaining_d)
    order_dict["payment_status"] = payment_status
    if patient_name is not None:
        order_dict["patient_name"] = patient_name
    elif order.patient:
        order_dict["patient_name"] = order.patient.name
    if laboratory_name is not None:
        order_dict["laboratory_name"] = laboratory_name
    elif order.laboratory:
        order_dict["laboratory_name"] = order.laboratory.name
    if is_existing is not None:
        order_dict["is_existing"] = is_existing
    return order_dict


async def get_unpaid_orders_count(
    db: AsyncSession, tenant_id: int, laboratory_id: int | None = None
) -> int:
    """Count non-cancelled orders with cost > 0 where total payments < cost."""
    pay_sub = (
        select(
            models.LabPayment.lab_order_id.label("order_id"),
            func.sum(models.LabPayment.amount).label("paid_total"),
        )
        .where(
            models.LabPayment.tenant_id == tenant_id,
            models.LabPayment.lab_order_id.isnot(None),
        )
        .group_by(models.LabPayment.lab_order_id)
        .subquery()
    )

    stmt = (
        select(func.count(models.LabOrder.id))
        .outerjoin(pay_sub, models.LabOrder.id == pay_sub.c.order_id)
        .where(
            models.LabOrder.tenant_id == tenant_id,
            models.LabOrder.status != "cancelled",
            models.LabOrder.cost > 0,
            func.coalesce(pay_sub.c.paid_total, 0) < models.LabOrder.cost,
        )
    )
    if laboratory_id is not None:
        stmt = stmt.where(models.LabOrder.laboratory_id == laboratory_id)

    res = await db.execute(stmt)
    return res.scalar() or 0


async def get_unallocated_payments_stats(
    db: AsyncSession, tenant_id: int, laboratory_id: int | None = None
) -> tuple[Decimal, int]:
    """Return (unallocated_payments_total, unallocated_payments_count) where lab_order_id IS NULL."""
    stmt = select(
        func.coalesce(func.sum(models.LabPayment.amount), 0),
        func.count(models.LabPayment.id),
    ).where(
        models.LabPayment.tenant_id == tenant_id,
        models.LabPayment.lab_order_id.is_(None),
    )
    if laboratory_id is not None:
        stmt = stmt.where(models.LabPayment.laboratory_id == laboratory_id)
    row = (await db.execute(stmt)).one()
    return quantize_money(as_decimal(row[0])), int(row[1] or 0)


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
        """Create a lab order and its billable treatment atomically."""
        stmt_patient = select(models.Patient).where(
            models.Patient.id == data.patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
        patient = (await self.db.execute(stmt_patient)).scalars().first()
        if not patient:
            raise ValueError("Patient not found")

        stmt_lab = select(models.Laboratory).where(
            models.Laboratory.id == data.laboratory_id,
            models.Laboratory.tenant_id == self.tenant_id,
        )
        lab = (await self.db.execute(stmt_lab)).scalars().first()
        if not lab:
            raise ValueError("Laboratory not found")

        # G12-M16: Handoff idempotency - return existing active lab order if one exists
        if data.work_item_id is not None:
            stmt_existing = (
                select(models.LabOrder)
                .where(
                    models.LabOrder.tenant_id == self.tenant_id,
                    models.LabOrder.work_item_id == data.work_item_id,
                    models.LabOrder.status != "cancelled",
                )
                .order_by(models.LabOrder.id.desc())
            )
            existing_order = (await self.db.execute(stmt_existing)).scalars().first()
            if existing_order:
                return existing_order

        if data.treatment_id is not None:
            stmt_treatment = select(models.Treatment).where(
                models.Treatment.id == data.treatment_id,
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.patient_id == data.patient_id,
                models.Treatment.is_deleted == False,  # noqa: E712
            )
            treatment = (await self.db.execute(stmt_treatment)).scalars().first()
            if not treatment:
                raise ValueError("Treatment not found")

            # D3 / Step 2: Idempotency - return existing active non-cancelled lab order if present
            stmt_existing = (
                select(models.LabOrder)
                .where(
                    models.LabOrder.tenant_id == self.tenant_id,
                    models.LabOrder.treatment_id == data.treatment_id,
                    models.LabOrder.status != "cancelled",
                )
                .order_by(models.LabOrder.id.desc())
            )
            existing_order = (await self.db.execute(stmt_existing)).scalars().first()
            if existing_order:
                return existing_order

        paid_now_d = quantize_money(as_decimal(getattr(data, "paid_now", 0)))
        cost_d = quantize_money(as_decimal(data.cost))
        if paid_now_d > 0 and paid_now_d > cost_d:
            raise ValueError("المبلغ المدفوع لا يمكن أن يتجاوز تكلفة الطلب")

        db_order = models.LabOrder(
            **data.model_dump(exclude={"paid_now"}),
            tenant_id=self.tenant_id,
            doctor_id=doctor_id,
        )
        self.db.add(db_order)
        # Generate the order ID without persisting a half-complete financial pair.
        await self.db.flush()

        if paid_now_d > 0:
            payment = models.LabPayment(
                laboratory_id=data.laboratory_id,
                lab_order_id=db_order.id,
                amount=paid_now_d,
                method="Cash",
                notes=f"دفعة طلب معمل #{db_order.id}",
                tenant_id=self.tenant_id,
            )
            self.db.add(payment)
            await self.db.flush()

        # G12-M08 & G12-M09 / R06 / D3: Decouple lab price from synthetic treatment creation.
        # When linked to a clinical work item or existing treatment, create 0 synthetic treatments!
        if data.work_item_id is None and data.treatment_id is None and db_order.price_to_patient and db_order.price_to_patient > 0:
            await self._create_linked_treatment(db_order, lab)

        await self.db.commit()
        await self.db.refresh(db_order)
        return db_order

    async def update_lab_order(
        self, order_id: int, data: schemas.LabOrderUpdate
    ) -> models.LabOrder:
        """Update lab order and sync linked treatment."""
        order = await self.get_lab_order(order_id)
        if not order:
            raise ValueError("Lab order not found")

        update_data = data.model_dump(exclude_unset=True)
        if "treatment_id" in update_data and update_data["treatment_id"] is not None:
            if order.work_item_id is not None or update_data.get("work_item_id") is not None:
                raise ValueError("Cannot link treatment to a work item lab order")

            stmt_treat = select(models.Treatment).where(
                models.Treatment.id == update_data["treatment_id"],
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.patient_id == order.patient_id,
                models.Treatment.is_deleted == False,  # noqa: E712
            )
            treatment = (await self.db.execute(stmt_treat)).scalars().first()
            if not treatment:
                raise ValueError("Treatment not found")

            if update_data["treatment_id"] != order.treatment_id:
                stmt_conflict = select(models.LabOrder).where(
                    models.LabOrder.tenant_id == self.tenant_id,
                    models.LabOrder.treatment_id == update_data["treatment_id"],
                    models.LabOrder.status != "cancelled",
                    models.LabOrder.id != order.id,
                )
                conflict = (await self.db.execute(stmt_conflict)).scalars().first()
                if conflict:
                    raise ValueError("An active lab order already exists for this treatment")

        if update_data.get("status") == "completed" and order.status != "completed":
            update_data["received_date"] = utc_now_naive()

        if "cost" in update_data and update_data["cost"] is not None:
            total_paid = await self.db.scalar(
                select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
                    models.LabPayment.tenant_id == self.tenant_id,
                    models.LabPayment.lab_order_id == order.id,
                )
            )
            total_paid_d = quantize_money(as_decimal(total_paid))
            new_cost_d = quantize_money(as_decimal(update_data["cost"]))
            if new_cost_d < total_paid_d:
                raise ValueError(
                    f"لا يمكن تقليل تكلفة الطلب ({new_cost_d}) إلى أقل من المبلغ المدفوع بالفعل ({total_paid_d})"
                )

        for key, value in update_data.items():
            setattr(order, key, value)

        # G12-M13: Sync shade/material updates to active care session observations
        if order.work_item_id and ("shade" in update_data or "material" in update_data):
            from backend.clinical.shade_material_sync import sync_lab_order_to_active_care_session_observations
            await sync_lab_order_to_active_care_session_observations(
                self.db, self.tenant_id, order
            )

        await self._sync_linked_treatment(order, commit=False)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def delete_lab_order(self, order_id: int) -> bool:
        """Delete one lab order and only its exact linked treatment."""
        order = await self.get_lab_order(order_id)
        if not order:
            raise ValueError("Lab order not found")

        has_payments = await self.db.scalar(
            select(func.count(models.LabPayment.id)).where(
                models.LabPayment.tenant_id == self.tenant_id,
                models.LabPayment.lab_order_id == order_id,
            )
        )
        if has_payments and has_payments > 0:
            raise ValueError("الطلب عليه دفعات، الغِ الطلب بدل حذفه")

        link_note = f"{TREATMENT_LINK_PREFIX}{order_id}"
        stmt_treatment = select(models.Treatment).where(
            models.Treatment.tenant_id == self.tenant_id,
            models.Treatment.notes == link_note,
        )
        linked_treatment = (await self.db.execute(stmt_treatment)).scalars().first()
        if linked_treatment:
            await self.db.delete(linked_treatment)

        await self.db.delete(order)
        await self.db.commit()
        return True

    async def get_patient_lab_orders(self, patient_id: int) -> List[models.LabOrder]:
        stmt = (
            select(models.LabOrder)
            .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
            .where(
                models.LabOrder.patient_id == patient_id,
                models.LabOrder.tenant_id == self.tenant_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .order_by(models.LabOrder.order_date.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # --- Linked Treatment Sync ---

    async def _create_linked_treatment(
        self,
        order: models.LabOrder,
        lab: models.Laboratory,
    ) -> None:
        """Stage the exact tenant-owned treatment linked to a lab order."""
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
            tenant_id=self.tenant_id,
        )
        self.db.add(linked_treatment)

    async def _sync_linked_treatment(
        self,
        order: models.LabOrder,
        *,
        commit: bool = True,
    ) -> None:
        """Update or create the exact tenant-owned linked treatment."""
        link_note = f"{TREATMENT_LINK_PREFIX}{order.id}"
        stmt_treatment = select(models.Treatment).where(
            models.Treatment.tenant_id == self.tenant_id,
            models.Treatment.notes == link_note,
        )
        linked_treatment = (await self.db.execute(stmt_treatment)).scalars().first()

        if linked_treatment:
            linked_treatment.cost = order.price_to_patient or 0
            linked_treatment.procedure = _get_lab_procedure_name(
                order.work_type, order.material
            )
            linked_treatment.doctor_id = order.doctor_id
            if order.laboratory:
                linked_treatment.diagnosis = f"تركيبة معملية - {order.laboratory.name}"
        elif order.work_item_id is None and order.treatment_id is None and order.price_to_patient and order.price_to_patient > 0:
            tooth_num = None
            if order.tooth_number:
                try:
                    tooth_num = int(order.tooth_number.split(",")[0].strip())
                except (ValueError, AttributeError):
                    pass

            lab_name = "معمل"
            if order.laboratory_id:
                stmt_lab = select(models.Laboratory).where(
                    models.Laboratory.id == order.laboratory_id,
                    models.Laboratory.tenant_id == self.tenant_id,
                )
                lab = (await self.db.execute(stmt_lab)).scalars().first()
                if lab:
                    lab_name = lab.name

            self.db.add(
                models.Treatment(
                    patient_id=order.patient_id,
                    tooth_number=tooth_num,
                    diagnosis=f"تركيبة معملية - {lab_name}",
                    procedure=_get_lab_procedure_name(order.work_type, order.material),
                    doctor_id=order.doctor_id,
                    cost=order.price_to_patient,
                    discount=0.0,
                    date=order.order_date,
                    notes=link_note,
                    tenant_id=self.tenant_id,
                )
            )

        if commit:
            await self.db.commit()

    # --- Statistics ---

    async def get_stats_summary(self) -> Dict[str, Any]:
        stmt_total = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id
        )
        total_orders = (await self.db.execute(stmt_total)).scalar() or 0

        stmt_pending = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "pending",
        )
        pending_orders = (await self.db.execute(stmt_pending)).scalar() or 0

        stmt_ip = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "in_progress",
        )
        in_progress = (await self.db.execute(stmt_ip)).scalar() or 0

        stmt_comp = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "completed",
        )
        completed = (await self.db.execute(stmt_comp)).scalar() or 0

        stmt_cost = select(func.coalesce(func.sum(models.LabOrder.cost), 0)).where(
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status != "cancelled",
        )
        total_cost = (await self.db.execute(stmt_cost)).scalar() or 0

        stmt_rev = select(func.coalesce(func.sum(models.LabOrder.price_to_patient), 0)).where(
            models.LabOrder.tenant_id == self.tenant_id
        )
        total_revenue = (await self.db.execute(stmt_rev)).scalar() or 0

        stmt_labs = select(func.count()).select_from(models.Laboratory).where(
            models.Laboratory.tenant_id == self.tenant_id,
            models.Laboratory.is_active == True,  # noqa: E712
        )
        total_labs = (await self.db.execute(stmt_labs)).scalar() or 0

        unpaid_orders_count = await get_unpaid_orders_count(self.db, self.tenant_id)

        return {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "in_progress_orders": in_progress,
            "completed_orders": completed,
            "total_cost": float(total_cost),
            "total_revenue": float(total_revenue),
            "profit": float(total_revenue - total_cost),
            "total_labs": total_labs,
            "unpaid_orders_count": unpaid_orders_count,
        }

    async def get_lab_stats(self, lab_id: int) -> Dict[str, Any]:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        stmt_total = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )
        total_orders = (await self.db.execute(stmt_total)).scalar() or 0

        stmt_pending = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "pending",
        )
        pending = (await self.db.execute(stmt_pending)).scalar() or 0

        stmt_completed = select(func.count()).select_from(models.LabOrder).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status == "completed",
        )
        completed = (await self.db.execute(stmt_completed)).scalar() or 0

        stmt_cost = select(func.coalesce(func.sum(models.LabOrder.cost), 0)).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
            models.LabOrder.status != "cancelled",
        )
        total_cost = (await self.db.execute(stmt_cost)).scalar() or 0.0

        stmt_rev = select(func.coalesce(func.sum(models.LabOrder.price_to_patient), 0)).where(
            models.LabOrder.laboratory_id == lab_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )
        total_revenue = (await self.db.execute(stmt_rev)).scalar() or 0.0

        stmt_paid = select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == self.tenant_id,
        )
        total_paid = (await self.db.execute(stmt_paid)).scalar() or 0.0

        unpaid_orders_count = await get_unpaid_orders_count(self.db, self.tenant_id, lab_id)
        unallocated_total, unallocated_count = await get_unallocated_payments_stats(
            self.db, self.tenant_id, lab_id
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
            "unpaid_orders_count": unpaid_orders_count,
            "unallocated_payments_total": float(unallocated_total),
            "unallocated_payments_count": unallocated_count,
        }

    # --- Payments ---

    async def create_lab_payment(
        self, lab_id: int, data: schemas.LabPaymentCreate
    ) -> models.LabPayment:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        if data.lab_order_id is not None:
            stmt = select(models.LabOrder).where(
                models.LabOrder.id == data.lab_order_id,
                models.LabOrder.tenant_id == self.tenant_id,
            )
            bind = self.db.bind or self.db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update()

            order = (await self.db.execute(stmt)).scalars().first()
            if not order:
                raise ValueError("طلب المعمل غير موجود")
            if order.laboratory_id != lab_id:
                raise ValueError("الطلب لا يتبع هذا المعمل")
            if (order.status or "").lower() == "cancelled":
                raise ValueError("لا يمكن تسجيل دفعة لطلب معمل ملغي")

            existing_paid = await self.db.scalar(
                select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
                    models.LabPayment.tenant_id == self.tenant_id,
                    models.LabPayment.lab_order_id == order.id,
                )
            )
            existing_paid_d = quantize_money(as_decimal(existing_paid))
            order_cost_d = quantize_money(as_decimal(order.cost))
            remaining_d = max(Decimal("0.00"), order_cost_d - existing_paid_d)

            payment_amount_d = quantize_money(as_decimal(data.amount))
            if payment_amount_d > remaining_d:
                raise ValueError(
                    f"المبلغ المدفوع ({payment_amount_d}) يتجاوز المبلغ المتبقي للطلب ({remaining_d})"
                )

        payment = models.LabPayment(
            **data.model_dump(),
            tenant_id=self.tenant_id,
        )
        payment.laboratory_id = lab_id
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

    async def allocate_payment(
        self, lab_id: int, payment_id: int, lab_order_id: int
    ) -> models.LabPayment:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        stmt_payment = select(models.LabPayment).where(
            models.LabPayment.id == payment_id,
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == self.tenant_id,
        )
        bind = self.db.bind or self.db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            stmt_payment = stmt_payment.with_for_update()

        payment = (await self.db.execute(stmt_payment)).scalars().first()
        if not payment:
            raise ValueError("الدفعة غير موجودة")
        if payment.lab_order_id is not None:
            raise ValueError("الدفعة مرتبطة بطلب بالفعل")

        stmt_order = select(models.LabOrder).where(
            models.LabOrder.id == lab_order_id,
            models.LabOrder.tenant_id == self.tenant_id,
        )
        if bind and bind.dialect.name == "postgresql":
            stmt_order = stmt_order.with_for_update()

        order = (await self.db.execute(stmt_order)).scalars().first()
        if not order:
            raise ValueError("طلب المعمل غير موجود")
        if order.laboratory_id != lab_id:
            raise ValueError("الطلب لا يتبع هذا المعمل")
        if (order.status or "").lower() == "cancelled":
            raise ValueError("لا يمكن ربط دفعة بطلب معمل ملغي")

        existing_paid = await self.db.scalar(
            select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
                models.LabPayment.tenant_id == self.tenant_id,
                models.LabPayment.lab_order_id == order.id,
            )
        )
        existing_paid_d = quantize_money(as_decimal(existing_paid))
        order_cost_d = quantize_money(as_decimal(order.cost))
        remaining_d = max(Decimal("0.00"), order_cost_d - existing_paid_d)

        payment_amount_d = quantize_money(as_decimal(payment.amount))
        if payment_amount_d > remaining_d:
            raise ValueError(
                f"مبلغ الدفعة ({payment_amount_d}) يتجاوز المبلغ المتبقي للطلب ({remaining_d})"
            )

        payment.lab_order_id = lab_order_id
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def deallocate_payment(
        self, lab_id: int, payment_id: int
    ) -> models.LabPayment:
        lab = await self.get_laboratory(lab_id)
        if not lab:
            raise ValueError("Laboratory not found")

        stmt_payment = select(models.LabPayment).where(
            models.LabPayment.id == payment_id,
            models.LabPayment.laboratory_id == lab_id,
            models.LabPayment.tenant_id == self.tenant_id,
        )
        bind = self.db.bind or self.db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            stmt_payment = stmt_payment.with_for_update()

        payment = (await self.db.execute(stmt_payment)).scalars().first()
        if not payment:
            raise ValueError("الدفعة غير موجودة")
        if payment.lab_order_id is None:
            raise ValueError("الدفعة غير مرتبطة بأي طلب")

        payment.lab_order_id = None
        await self.db.commit()
        await self.db.refresh(payment)
        return payment


async def get_lab_service(db: AsyncSession, tenant_id: int) -> LabService:
    return LabService(db, tenant_id)
