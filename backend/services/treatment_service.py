"""
Treatment Service (Refactored to Async)

Central service for all treatment-related operations:
- Create/update treatments with pricing and stock logic
- Stock validation and consumption
- Price snapshot creation

This removes business logic from the treatments router.
"""

import json
import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, select, delete

from backend import models, schemas
from backend.services.pricing_service import get_pricing_service
from backend.services.inventory_service import inventory_service
from backend.utils.audit_logger import log_admin_action

logger = logging.getLogger(__name__)


class TreatmentService:
    """Central treatment logic - SINGLE SOURCE OF TRUTH."""

    def __init__(self, db: AsyncSession, tenant_id: int, current_user: models.User):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.pricing = get_pricing_service(db, tenant_id)

    # --- Pricing & Snapshot ---

    async def _calculate_price_and_snapshot(
        self,
        treatment_data: schemas.TreatmentCreate,
        price_list_id: Optional[int],
    ) -> tuple[float, Optional[str]]:
        """
        Calculate unit price and create price snapshot.

        Returns:
            (unit_price, price_snapshot_json)
        """
        # Get patient's default price list if not provided
        if not price_list_id:
            stmt_patient = select(models.Patient).where(
                models.Patient.id == treatment_data.patient_id,
                models.Patient.tenant_id == self.tenant_id,
            )
            patient = (await self.db.execute(stmt_patient)).scalars().first()
            price_list_id = patient.default_price_list_id if patient else None

        # Find procedure
        stmt_proc = select(models.Procedure).where(
            models.Procedure.name == treatment_data.procedure,
            or_(
                models.Procedure.tenant_id == self.tenant_id,
                models.Procedure.tenant_id.is_(None),
            ),
        )
        procedure = (await self.db.execute(stmt_proc)).scalars().first()

        unit_price = 0.0
        price_snapshot = None

        if procedure:
            unit_price = await self.pricing.get_procedure_price(procedure.id, price_list_id)

            # Create price snapshot
            price_list = await self.pricing.get_price_list(price_list_id)
            snapshot = {
                "list_id": price_list_id,
                "list_name": price_list.name if price_list else "Standard",
                "unit_price": unit_price,
                "date": date.today().isoformat(),
            }
            price_snapshot = json.dumps(snapshot)

        return unit_price, price_snapshot

    # --- Stock Operations ---

    async def validate_treatment_stock(
        self, consumed_materials: List[schemas.clinical.ConsumedMaterialItem]
    ) -> None:
        """
        Validate stock availability for all materials.

        Raises HTTPException with detailed message if insufficient stock.
        """
        from fastapi import HTTPException

        if not consumed_materials:
            return

        errors = []
        for item in consumed_materials:
            try:
                is_valid, available, mat_name = await inventory_service.validate_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=self.tenant_id,
                    db=self.db,
                )
                if not is_valid:
                    errors.append(
                        f"{mat_name} (Need: {item.quantity}, Available: {available})"
                    )
            except Exception as e:
                logger.error(f"Stock Validation Error for material {item.material_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500, detail=f"Stock Validation Error: {str(e)}"
                )

        if errors:
            raise HTTPException(
                status_code=400,
                detail="فشل حفظ العلاج بسبب نقص المخزون: " + " | ".join(errors),
            )

    async def consume_treatment_stock(
        self,
        treatment_id: int,
        consumed_materials: List[schemas.clinical.ConsumedMaterialItem],
        patient_id: Optional[int] = None,
    ) -> None:
        """
        Consume stock for treatment materials.

        Raises HTTPException (409 for CONFIRM_OPEN_REQUIRED, 500 for other errors).
        """
        from fastapi import HTTPException

        logger.info(f"[STOCK_DEBUG] consume_treatment_stock called for treatment {treatment_id} with {len(consumed_materials or [])} materials")

        if not consumed_materials:
            logger.info("[STOCK_DEBUG] No consumed materials provided, skipping stock consumption")
            return

        for item in consumed_materials:
            logger.info(f"[STOCK_DEBUG] Processing material_id={item.material_id}, quantity={item.quantity}")
            try:
                await inventory_service.consume_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=self.tenant_id,
                    user_id=self.current_user.id,
                    reference_id=f"TREATMENT:{treatment_id}",
                    patient_id=patient_id,
                    db=self.db,
                    commit=False,
                )
            except Exception as e:
                logger.error(f"Stock Consumption Error: {e}", exc_info=True)
                error_msg = str(e)

                if error_msg.startswith("CONFIRM_OPEN_REQUIRED:"):
                    parts = error_msg.split(":", 2)
                    stock_item_id = int(parts[1]) if len(parts) > 1 else None
                    material_info = parts[2] if len(parts) > 2 else "Unknown"
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "CONFIRM_OPEN_REQUIRED",
                            "stock_item_id": stock_item_id,
                            "material_info": material_info,
                            "message": f"يجب فتح عبوة جديدة قبل الاستخدام: {material_info}",
                        },
                    )

                if isinstance(e, ValueError):
                    raise HTTPException(status_code=400, detail=error_msg)

                raise HTTPException(status_code=500, detail=f"Stock Error: {error_msg}")

    # --- Treatment CRUD ---

    async def create_treatment(
        self,
        treatment_data: schemas.TreatmentCreate,
    ) -> models.Treatment:
        """
        Create treatment with pricing, stock validation, and consumption.
        """
        from fastapi import HTTPException
        from backend import crud

        # 1. Verify patient exists
        patient = await crud.patient.get_patient(self.db, treatment_data.patient_id, self.tenant_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # 2. Validate stock (pre-check) — skip if requested
        skip_stock = getattr(treatment_data, 'skip_stock_check', False)
        if not skip_stock:
            await self.validate_treatment_stock(treatment_data.consumedMaterials or [])
        else:
            logger.info("[TREATMENT] Skipping stock validation (skip_stock_check=True)")

        # 3. Calculate price and snapshot
        price_list_id = getattr(treatment_data, "price_list_id", None)
        unit_price, price_snapshot = await self._calculate_price_and_snapshot(
            treatment_data, price_list_id
        )

        # 4. Auto-assign doctor if not provided
        doctor_id = treatment_data.doctor_id if treatment_data.doctor_id else self.current_user.id

        # 5. Create treatment (deferred commit)
        created_treatment = await crud.billing.create_treatment(
            db=self.db,
            treatment=treatment_data,
            tenant_id=self.tenant_id,
            doctor_id=doctor_id,
            price_list_id=price_list_id,
            unit_price=unit_price,
            price_snapshot=price_snapshot,
            commit=False,
        )

        # 6. Consume stock (post-creation) — skip if requested
        if not skip_stock:
            await self.consume_treatment_stock(
                created_treatment.id,
                treatment_data.consumedMaterials or [],
                patient_id=treatment_data.patient_id
            )
        else:
            logger.info("[TREATMENT] Skipping stock consumption (skip_stock_check=True)")

        # 6.5. Persist material usage records (for reports/learning)
        await self.persist_treatment_material_usages(
            created_treatment.id,
            treatment_data.consumedMaterials or [],
            doctor_id=doctor_id
        )

        # 7. Commit transaction
        await self.db.commit()
        await self.db.refresh(created_treatment)
        from sqlalchemy.orm import selectinload
        stmt = (
            select(models.Treatment)
            .where(models.Treatment.id == created_treatment.id)
            .options(selectinload(models.Treatment.treatment_sessions))
        )
        result = await self.db.execute(stmt)
        refreshed_treatment = result.scalars().first()
        if refreshed_treatment is not None:
            created_treatment = refreshed_treatment
        created_treatment.consumedMaterials = treatment_data.consumedMaterials or []

        # 8. Log admin action
        log_admin_action(
            db=self.db,
            admin_user=self.current_user,
            action="create",
            entity_type="treatment",
            entity_id=created_treatment.id,
            details=f"Treatment '{treatment_data.procedure}' for patient {treatment_data.patient_id}",
        )

        return created_treatment

    async def update_treatment(
        self,
        treatment_id: int,
        treatment_data: schemas.TreatmentCreate,
    ) -> models.Treatment:
        """
        Update treatment with stock validation and consumption.
        """
        from backend import crud

        # 1. Reverse old stock movements for this treatment
        await inventory_service.reverse_stock_by_reference(
            reference_id=f"TREATMENT:{treatment_id}",
            user_id=self.current_user.id,
            db=self.db,
        )

        # 2. Validate new stock (pre-check) — skip if requested
        skip_stock = getattr(treatment_data, 'skip_stock_check', False)
        if not skip_stock:
            await self.validate_treatment_stock(treatment_data.consumedMaterials or [])
        else:
            logger.info("[TREATMENT] Skipping stock validation on update (skip_stock_check=True)")

        # 3. Update treatment (deferred commit)
        updated_treatment = await crud.billing.update_treatment(
            self.db, treatment_id, treatment_data, self.tenant_id, commit=False
        )

        # 4. Consume new stock (post-update) — skip if requested
        if not skip_stock:
            await self.consume_treatment_stock(
                treatment_id,
                treatment_data.consumedMaterials or [],
                patient_id=treatment_data.patient_id
            )
        else:
            logger.info("[TREATMENT] Skipping stock consumption on update (skip_stock_check=True)")

        # 4.5. Persist material usage records (for reports/learning)
        await self.persist_treatment_material_usages(
            treatment_id,
            treatment_data.consumedMaterials or [],
            doctor_id=updated_treatment.doctor_id or self.current_user.id
        )

        # 5. Commit transaction
        await self.db.commit()
        await self.db.refresh(updated_treatment)
        from sqlalchemy.orm import selectinload
        stmt = (
            select(models.Treatment)
            .where(models.Treatment.id == updated_treatment.id)
            .options(selectinload(models.Treatment.treatment_sessions))
        )
        result = await self.db.execute(stmt)
        refreshed_treatment = result.scalars().first()
        if refreshed_treatment is not None:
            updated_treatment = refreshed_treatment
        updated_treatment.consumedMaterials = treatment_data.consumedMaterials or []

        return updated_treatment

    async def delete_treatment(self, treatment_id: int) -> dict:
        """Delete a treatment record and reverse its stock movements."""
        from backend import crud
        from backend.models import inventory as inv_models

        # 1. Reverse stock movements for this treatment
        await inventory_service.reverse_stock_by_reference(
            reference_id=f"TREATMENT:{treatment_id}",
            user_id=self.current_user.id,
            db=self.db,
        )

        # 1.5. Clear associated usage records
        stmt_del = delete(inv_models.TreatmentMaterialUsage).where(
            inv_models.TreatmentMaterialUsage.treatment_id == treatment_id,
            inv_models.TreatmentMaterialUsage.tenant_id == self.tenant_id,
        )
        await self.db.execute(stmt_del)

        # 2. Log the action
        log_admin_action(
            db=self.db,
            admin_user=self.current_user,
            action="delete",
            entity_type="treatment",
            entity_id=treatment_id,
            details=f"Deleted treatment #{treatment_id} (stock reversed)",
        )

        # 3. Delete treatment
        return await crud.billing.delete_treatment(self.db, treatment_id, self.tenant_id)

    async def persist_treatment_material_usages(
        self,
        treatment_id: int,
        consumed_materials: List[schemas.clinical.ConsumedMaterialItem],
        doctor_id: Optional[int] = None,
    ) -> None:
        """
        Create and persist TreatmentMaterialUsage records for a treatment.
        """
        from backend.models import inventory as inv_models

        # Clear existing usage records for this treatment
        stmt_del = delete(inv_models.TreatmentMaterialUsage).where(
            inv_models.TreatmentMaterialUsage.treatment_id == treatment_id,
            inv_models.TreatmentMaterialUsage.tenant_id == self.tenant_id,
        )
        await self.db.execute(stmt_del)

        if not consumed_materials:
            return

        # Fetch materials to determine type (DIVISIBLE / NON_DIVISIBLE)
        material_ids = [m.material_id for m in consumed_materials]
        stmt_mat = select(inv_models.Material).where(
            inv_models.Material.id.in_(material_ids),
            inv_models.Material.tenant_id == self.tenant_id,
        )
        materials = (await self.db.execute(stmt_mat)).scalars().all()
        material_map = {m.id: m for m in materials}

        for item in consumed_materials:
            mat = material_map.get(item.material_id)
            if not mat:
                continue

            mat_type = getattr(item, 'material_type', None) or mat.type
            session_id = getattr(item, 'session_id', None)

            # Auto-resolve session_id for divisible/reusable materials if not provided
            if mat_type in ("DIVISIBLE", "REUSABLE") and not session_id:
                # Look for active session in the database
                active_session_query = (
                    select(inv_models.MaterialSession)
                    .join(inv_models.StockItem)
                    .join(inv_models.Batch)
                    .where(
                        inv_models.MaterialSession.status == "ACTIVE",
                        inv_models.StockItem.tenant_id == self.tenant_id,
                        inv_models.Batch.material_id == item.material_id,
                    )
                )
                if doctor_id:
                    # Try to match the doctor first
                    doc_session = (await self.db.execute(
                        active_session_query.where(
                            inv_models.MaterialSession.doctor_id == doctor_id
                        )
                    )).scalars().first()

                    if doc_session:
                        session_id = doc_session.id
                    else:
                        fallback_sess = (await self.db.execute(active_session_query)).scalars().first()
                        session_id = fallback_sess.id if fallback_sess else None
                else:
                    fallback_sess = (await self.db.execute(active_session_query)).scalars().first()
                    session_id = fallback_sess.id if fallback_sess else None

            # Calculate quantities and costs
            quantity_used = None
            cost_calculated = None

            if mat_type == "NON_DIVISIBLE":
                # For non-divisible, quantity is used immediately
                quantity_used = item.quantity

                # Fetch stock movements created for this treatment to find batch costs
                stmt_moves = (
                    select(inv_models.StockMovement)
                    .join(inv_models.StockItem)
                    .join(inv_models.Batch)
                    .options(
                        joinedload(inv_models.StockMovement.stock_item)
                        .joinedload(inv_models.StockItem.batch)
                    )
                    .where(
                        inv_models.StockMovement.reference_id == f"TREATMENT:{treatment_id}",
                        inv_models.Batch.material_id == item.material_id,
                    )
                )
                movements = (await self.db.execute(stmt_moves)).scalars().all()

                if movements:
                    total_cost = 0.0
                    for move in movements:
                        # move.change_amount is negative for consumption
                        cost_per_unit = move.stock_item.batch.cost_per_unit or 0.0
                        total_cost += abs(move.change_amount) * cost_per_unit
                    cost_calculated = total_cost
                else:
                    # Fallback to standard price
                    standard_price = mat.standard_price or 0.0
                    cost_calculated = quantity_used * standard_price
            else:
                # For divisible/reusable, quantity_used & cost_calculated will be set upon session close
                quantity_used = None
                cost_calculated = None

            usage = inv_models.TreatmentMaterialUsage(
                treatment_id=treatment_id,
                material_id=item.material_id,
                session_id=session_id,
                weight_score=getattr(item, 'weight_score', None) or 1.0,
                quantity_used=quantity_used,
                cost_calculated=cost_calculated,
                is_manual_override=getattr(item, 'is_manual_override', None) or False,
                tenant_id=self.tenant_id,
            )
            self.db.add(usage)

    async def add_session(self, session_data: schemas.clinical.TreatmentSessionCreate) -> models.TreatmentSession:
        """Add a treatment session."""
        from fastapi import HTTPException

        # Verify treatment exists and belongs to tenant
        stmt_t = select(models.Treatment).where(
            models.Treatment.id == session_data.treatment_id,
            models.Treatment.tenant_id == self.tenant_id,
        )
        treatment = (await self.db.execute(stmt_t)).scalars().first()
        if not treatment:
            raise HTTPException(status_code=404, detail="Treatment not found")

        session = models.TreatmentSession(
            treatment_id=session_data.treatment_id,
            notes=session_data.notes,
            session_date=session_data.session_date or datetime.now(timezone.utc),
            tenant_id=self.tenant_id
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session


# Factory function
def get_treatment_service(db: AsyncSession, tenant_id: int, current_user: models.User) -> TreatmentService:
    """Factory function for treatment service."""
    return TreatmentService(db, tenant_id, current_user)
