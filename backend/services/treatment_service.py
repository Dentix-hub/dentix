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
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, select, delete

from fastapi import HTTPException
from backend import models, schemas
from backend.services.pricing_service import get_pricing_service
from backend.services.inventory_service import inventory_service
from backend.utils.audit_logger import log_admin_action
from backend.core.money import as_decimal, money_json_default

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
                "unit_price": as_decimal(unit_price),
                "date": date.today().isoformat(),
            }
            # Numeric columns return Decimal under PostgreSQL; plain json.dumps
            # would raise TypeError (HIGH-01 regression guard).
            price_snapshot = json.dumps(snapshot, default=money_json_default)

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

    async def _sync_clinical_work_item(
        self,
        treatment: models.Treatment,
        surfaces: Optional[List[str]] = None,
    ) -> Optional[models.ClinicalWorkItem]:
        """
        Synchronize created/updated treatment to ClinicalWorkItem and ClinicalEvent.
        Provides zero-overhead integration with Odontogram renderer workspace projection.
        """
        if not treatment.tooth_number:
            return None

        tooth_key = str(treatment.tooth_number)
        from backend.models.clinical_core import FDI_TOOTH_KEYS, SURFACE_CODES
        if tooth_key not in FDI_TOOTH_KEYS:
            return None

        from backend.clinical.catalog import CANONICAL_PROCEDURE_CODES
        from backend.clinical.legacy_mapping import LEGACY_PROCEDURE_ALLOWLIST

        canonical_code = treatment.procedure
        if canonical_code not in CANONICAL_PROCEDURE_CODES:
            canonical_code = LEGACY_PROCEDURE_ALLOWLIST.get(treatment.procedure, treatment.procedure)

        status_raw = (treatment.status or "Done").lower()
        if status_raw in ("done", "completed"):
            status = "completed"
        elif status_raw in ("pending", "planned"):
            status = "planned"
        else:
            status = "active"

        work_item = models.ClinicalWorkItem(
            tenant_id=self.tenant_id,
            patient_id=treatment.patient_id,
            kind="procedure",
            code=canonical_code,
            status=status,
            notes=treatment.notes,
            created_by_user_id=treatment.doctor_id or self.current_user.id,
        )
        self.db.add(work_item)
        await self.db.flush()

        surfs = surfaces or treatment.surfaces or []
        valid_surfs = [s for s in surfs if s in SURFACE_CODES]
        if valid_surfs:
            for s in valid_surfs:
                self.db.add(
                    models.ClinicalWorkItemTarget(
                        tenant_id=self.tenant_id,
                        work_item_id=work_item.id,
                        target_kind="surface",
                        tooth_key=tooth_key,
                        surface_code=s,
                    )
                )
        else:
            self.db.add(
                models.ClinicalWorkItemTarget(
                    tenant_id=self.tenant_id,
                    work_item_id=work_item.id,
                    target_kind="tooth",
                    tooth_key=tooth_key,
                )
            )

        # Append ClinicalEvent
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=treatment.patient_id,
            work_item_id=work_item.id,
            event_type="procedure_recorded",
            occurred_at=treatment.date or datetime.now(timezone.utc).replace(tzinfo=None),
            actor_user_id=treatment.doctor_id or self.current_user.id,
            payload={
                "kind": "procedure",
                "canonical_code": canonical_code,
                "treatment_id": treatment.id,
                "surfaces": valid_surfs,
            },
            notes=treatment.notes,
        )
        self.db.add(event)
        await self.db.flush()

        if valid_surfs:
            for s in valid_surfs:
                self.db.add(
                    models.clinical_core.ClinicalEventTarget(
                        tenant_id=self.tenant_id,
                        event_id=event.id,
                        target_kind="surface",
                        tooth_key=tooth_key,
                        surface_code=s,
                    )
                )
        else:
            self.db.add(
                models.clinical_core.ClinicalEventTarget(
                    tenant_id=self.tenant_id,
                    event_id=event.id,
                    target_kind="tooth",
                    tooth_key=tooth_key,
                )
            )

        return work_item

    async def create_treatment(
        self,
        treatment_data: schemas.TreatmentCreate,
        commit: bool = True,
    ) -> models.Treatment:
        """
        Create treatment with pricing, stock validation, and consumption.
        Supports single or multi-surface procedure targeting.
        """
        from fastapi import HTTPException
        from backend import crud

        if treatment_data.cost < 0 or treatment_data.discount < 0:
            raise HTTPException(status_code=422, detail="Treatment values cannot be negative")
        if treatment_data.discount > treatment_data.cost:
            raise HTTPException(status_code=422, detail="Discount cannot exceed treatment cost")

        # 1. Verify patient exists
        patient = await crud.patient.get_patient(self.db, treatment_data.patient_id, self.tenant_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # 1.5. Embed surfaces in notes if provided
        surfaces = getattr(treatment_data, "surfaces", None)
        surface = getattr(treatment_data, "surface", None)
        if surfaces:
            surf_tag = f"[Surfaces: {', '.join(surfaces)}]"
            if not treatment_data.notes:
                treatment_data.notes = surf_tag
            elif "[Surface" not in treatment_data.notes:
                treatment_data.notes = f"{treatment_data.notes} {surf_tag}"
        elif surface:
            surf_tag = f"[Surface: {surface}]"
            if not treatment_data.notes:
                treatment_data.notes = surf_tag
            elif "[Surface" not in treatment_data.notes:
                treatment_data.notes = f"{treatment_data.notes} {surf_tag}"

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

        # 5.5. Synchronize ClinicalWorkItem / ClinicalEvent for odontogram projection
        await self._sync_clinical_work_item(created_treatment, surfaces=surfaces)

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
        if commit:
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
        else:
            await self.db.flush()

        created_treatment.consumedMaterials = treatment_data.consumedMaterials or []
        if surface:
            created_treatment.surface = surface
        if surfaces:
            created_treatment.surfaces = surfaces

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

    async def create_multi_procedure_treatment(
        self,
        multi_data: schemas.ToothMultiProcedureCreate,
    ) -> schemas.ToothClinicalRecordResponse:
        """
        Record multiple procedures on a single tooth in an atomic tenant-scoped transaction.
        Calculates pricing snapshots, validates stock, consumes inventory, creates treatments,
        and links ClinicalWorkItems/ClinicalEvents for Odontogram projection.
        """
        from fastapi import HTTPException
        from backend import crud

        patient = await crud.patient.get_patient(self.db, multi_data.patient_id, self.tenant_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # 1. Aggregate and validate all stock up-front
        all_materials: List[schemas.clinical.ConsumedMaterialItem] = []
        for proc in multi_data.procedures:
            if not proc.skip_stock_check and proc.consumedMaterials:
                all_materials.extend(proc.consumedMaterials)

        if all_materials:
            await self.validate_treatment_stock(all_materials)

        created_treatments: List[models.Treatment] = []

        # 2. Process each procedure
        for proc in multi_data.procedures:
            treatment_data = schemas.TreatmentCreate(
                patient_id=multi_data.patient_id,
                tooth_number=multi_data.tooth_number,
                tooth_key=multi_data.tooth_key,
                procedure=proc.procedure,
                cost=proc.cost,
                discount=proc.discount,
                diagnosis=proc.diagnosis,
                surface=proc.surface,
                surfaces=proc.surfaces,
                canal_count=proc.canal_count,
                canal_lengths=proc.canal_lengths,
                sessions=proc.sessions,
                complications=proc.complications,
                notes=proc.notes or multi_data.notes,
                status=proc.status,
                doctor_id=multi_data.doctor_id or self.current_user.id,
                consumedMaterials=proc.consumedMaterials,
                skip_stock_check=True,  # already validated
                price_list_id=proc.price_list_id,
            )

            created = await self.create_treatment(treatment_data, commit=False)
            created_treatments.append(created)

        # 3. Commit all atomically
        await self.db.commit()

        # Refresh all created treatments
        for t in created_treatments:
            await self.db.refresh(t)

        tooth_key = multi_data.tooth_key or str(multi_data.tooth_number)
        return schemas.ToothClinicalRecordResponse(
            patient_id=multi_data.patient_id,
            tooth_number=multi_data.tooth_number,
            tooth_key=tooth_key,
            treatments=[schemas.Treatment.model_validate(t) for t in created_treatments],
            message="Multi-procedure treatments recorded successfully",
        )

    async def update_treatment(
        self,
        treatment_id: int,
        treatment_data: schemas.TreatmentCreate,
    ) -> models.Treatment:
        """
        Update treatment with stock validation and consumption.
        """
        from backend import crud

        if treatment_data.cost < 0 or treatment_data.discount < 0:
            raise HTTPException(status_code=422, detail="Treatment values cannot be negative")
        if treatment_data.discount > treatment_data.cost:
            raise HTTPException(status_code=422, detail="Discount cannot exceed treatment cost")

        # Embed surfaces in notes if present
        surfaces = getattr(treatment_data, "surfaces", None)
        surface = getattr(treatment_data, "surface", None)
        if surfaces:
            surf_tag = f"[Surfaces: {', '.join(surfaces)}]"
            if not treatment_data.notes:
                treatment_data.notes = surf_tag
            elif "[Surface" not in treatment_data.notes:
                treatment_data.notes = f"{treatment_data.notes} {surf_tag}"
        elif surface:
            surf_tag = f"[Surface: {surface}]"
            if not treatment_data.notes:
                treatment_data.notes = surf_tag
            elif "[Surface" not in treatment_data.notes:
                treatment_data.notes = f"{treatment_data.notes} {surf_tag}"

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
        if surfaces:
            updated_treatment.surfaces = surfaces
        if surface:
            updated_treatment.surface = surface

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
            inv_models.Material.is_deleted == False,  # noqa: E712
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
                    total_cost = Decimal("0")
                    for move in movements:
                        # move.change_amount is negative for consumption
                        cost_per_unit = as_decimal(move.stock_item.batch.cost_per_unit)
                        total_cost += as_decimal(abs(move.change_amount)) * cost_per_unit
                    cost_calculated = total_cost
                else:
                    # Fallback to standard price
                    standard_price = as_decimal(mat.standard_price)
                    cost_calculated = as_decimal(quantity_used) * standard_price
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
