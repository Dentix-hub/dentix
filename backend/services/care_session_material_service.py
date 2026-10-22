"""
Care Session Material Service (Slice S30).
Point-of-care material suggestion, deduct-at-use consumption, and work-item
material cost aggregation (G13-M04, G13-M05, G13-M06, G13-M07, G13-M08, G13-M09).

Invariants:
- Suggestions are strictly read-only: zero stock movements / usage rows (G13-M05).
  Plan creation / acceptance and proposed|planned work items never reach this
  service's write path, so they deduct zero inventory.
- Stock is deducted ONLY when `record_material_usage` is called for an
  in_progress/paused CareSession (G13-M06), through the existing
  `InventoryService.consume_stock` (FIFO, divisible/reusable session logic and
  CONFIRM_OPEN_REQUIRED rules are reused unchanged - G13-M08).
- Each call is one transaction: any stock failure rolls back every deduction
  made by that call (no partial deduction).
- Different materials per session of the same work item are supported by
  recording usages per care session (G13-M07).
- Fail-closed gate: clinical_vnext_native_writes (404 when disabled).
- Legacy `Treatment` rows, payments and invoices are never touched (R01/R06).
"""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.clinical.legacy_mapping import map_legacy_procedure
from backend.core.money import as_decimal, quantize_money
from backend.models import inventory as inv_models
from backend.services.care_session_service import CareSessionService
from backend.services.inventory_learning_service import InventoryLearningService
from backend.services.inventory_service import inventory_service
from backend.utils.audit_logger import log_admin_action

NON_USABLE_WORK_ITEM_STATUSES = {"cancelled", "superseded", "entered_in_error"}


class CareSessionMaterialService(CareSessionService):
    # -----------------------------------------------------------------------
    # G13-M04: Material suggestion (read-only)
    # -----------------------------------------------------------------------

    async def suggest_materials(
        self,
        patient_id: int,
        work_item_id: int,
        step_code: Optional[str] = None,
    ) -> schemas.MaterialSuggestionResponse:
        """
        Suggest materials for a work item by canonical procedure code.
        Resolves clinic/global Procedure rows whose legacy name maps to the work
        item's canonical code, then reuses InventoryLearningService suggestions
        (ProcedureMaterialWeight). `step_code` is echoed back; the weight table has
        no per-step dimension, so suggestions are procedure-level.
        Performs zero writes.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        work_item = await self._verify_work_item(patient_id, work_item_id)

        stmt = select(models.Procedure).where(
            (models.Procedure.tenant_id == self.tenant_id)
            | (models.Procedure.tenant_id.is_(None))
        )
        procedures = (await self.db.execute(stmt)).scalars().all()
        matched = [
            p for p in procedures if map_legacy_procedure(p.name)[0] == work_item.code
        ]
        # Clinic-owned procedures take precedence over global templates.
        matched.sort(key=lambda p: (p.tenant_id is None, p.id))

        learning = InventoryLearningService(self.db)
        user = await self._get_active_current_user()
        seen_materials = set()
        suggestions: List[dict] = []
        for proc in matched:
            for suggestion in await learning.get_suggested_materials(
                proc.id, self.tenant_id, getattr(user, "id", None)
            ):
                key = suggestion.get("material_id")
                if key is not None:
                    if key in seen_materials:
                        continue
                    seen_materials.add(key)
                suggestions.append(suggestion)

        return schemas.MaterialSuggestionResponse(
            work_item_id=work_item.id,
            procedure_code=work_item.code,
            step_code=step_code,
            procedure_ids=[p.id for p in matched],
            suggestions=suggestions,
        )

    # -----------------------------------------------------------------------
    # G13-M06 / G13-M07 / G13-M08: Deduct at point of use
    # -----------------------------------------------------------------------

    async def _resolve_open_package_session_id(
        self, material_id: int, doctor_id: Optional[int]
    ) -> Optional[int]:
        """Find the ACTIVE MaterialSession for a divisible/reusable material (legacy rule)."""
        query = (
            select(inv_models.MaterialSession)
            .join(inv_models.StockItem)
            .join(inv_models.Batch)
            .where(
                inv_models.MaterialSession.status == "ACTIVE",
                inv_models.StockItem.tenant_id == self.tenant_id,
                inv_models.Batch.material_id == material_id,
            )
        )
        if doctor_id:
            own = (
                await self.db.execute(
                    query.where(inv_models.MaterialSession.doctor_id == doctor_id)
                )
            ).scalars().first()
            if own:
                return own.id
        fallback = (await self.db.execute(query)).scalars().first()
        return fallback.id if fallback else None

    async def _movement_cost(self, movements: list) -> Optional[Decimal]:
        """Sum |change| * batch.cost_per_unit for freshly created stock movements."""
        if not movements:
            return None
        stock_item_ids = {m.stock_item_id for m in movements}
        rows = await self.db.execute(
            select(inv_models.StockItem.id, inv_models.Batch.cost_per_unit)
            .join(inv_models.Batch, inv_models.Batch.id == inv_models.StockItem.batch_id)
            .where(inv_models.StockItem.id.in_(stock_item_ids))
        )
        unit_cost = {sid: as_decimal(cost) for sid, cost in rows.all()}
        total = Decimal("0")
        for move in movements:
            total += as_decimal(abs(move.change_amount)) * unit_cost.get(
                move.stock_item_id, Decimal("0")
            )
        return total

    async def record_material_usage(
        self,
        patient_id: int,
        session_id: int,
        data: schemas.CareSessionMaterialUsageCreate,
    ) -> List[models.TreatmentMaterialUsage]:
        """
        Record actual material consumption for an active care session, deducting
        stock at the point of use and persisting TreatmentMaterialUsage rows linked
        by care_session_id / work_item_id (treatment_id stays NULL, PD07).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status not in ("in_progress", "paused"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot record materials on care session with status '{session.status}'",
            )

        work_item = None
        if data.work_item_id is not None:
            work_item = await self._verify_work_item(patient_id, data.work_item_id)
            if work_item.status in NON_USABLE_WORK_ITEM_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot record materials against work item with status '{work_item.status}'",
                )

        await self._acquire_advisory_lock(f"care_session_material:{session_id}")

        user = await self._get_active_current_user()
        user_id = getattr(user, "id", None) or self.current_user_id

        # Tenant-scoped material lookup (type drives divisible handling).
        material_ids = {item.material_id for item in data.items}
        mat_rows = (
            await self.db.execute(
                select(inv_models.Material).where(
                    inv_models.Material.id.in_(material_ids),
                    inv_models.Material.tenant_id == self.tenant_id,
                    inv_models.Material.is_deleted == False,  # noqa: E712
                )
            )
        ).scalars().all()
        material_map = {m.id: m for m in mat_rows}
        missing = sorted(material_ids - set(material_map))
        if missing:
            raise HTTPException(
                status_code=404, detail=f"Material(s) not found: {missing}"
            )

        # 1. Validate aggregate stock per material up-front (no partial deduction).
        totals: Dict[int, float] = defaultdict(float)
        for item in data.items:
            totals[item.material_id] += item.quantity
        errors = []
        for material_id, qty in totals.items():
            ok, available, name = await inventory_service.validate_stock(
                material_id=material_id,
                quantity=qty,
                tenant_id=self.tenant_id,
                db=self.db,
            )
            if not ok:
                errors.append(f"{name} (Need: {qty}, Available: {available})")
        if errors:
            raise HTTPException(
                status_code=400,
                detail="فشل تسجيل المواد بسبب نقص المخزون: " + " | ".join(errors),
            )

        # 2. Consume + persist, all in one transaction.
        reference_id = f"CARE_SESSION:{session_id}"
        usages: List[models.TreatmentMaterialUsage] = []
        try:
            for item in data.items:
                mat = material_map[item.material_id]
                try:
                    movements = await inventory_service.consume_stock(
                        material_id=item.material_id,
                        quantity=item.quantity,
                        tenant_id=self.tenant_id,
                        user_id=user_id,
                        reference_id=reference_id,
                        patient_id=patient_id,
                        db=self.db,
                        commit=False,
                    )
                except Exception as exc:
                    await self.db.rollback()
                    await self._get_active_current_user()
                    msg = str(exc)
                    if msg.startswith("CONFIRM_OPEN_REQUIRED:"):
                        parts = msg.split(":", 2)
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
                        ) from exc
                    if isinstance(exc, ValueError):
                        raise HTTPException(status_code=400, detail=msg) from exc
                    raise HTTPException(
                        status_code=500, detail=f"Stock Error: {msg}"
                    ) from exc

                quantity_used = None
                cost_calculated = None
                package_session_id = None
                if mat.type == "NON_DIVISIBLE":
                    quantity_used = item.quantity
                    cost = await self._movement_cost(movements)
                    if cost is None:
                        cost = as_decimal(item.quantity) * as_decimal(mat.standard_price)
                    cost_calculated = quantize_money(cost)
                else:
                    # DIVISIBLE / REUSABLE: costed when the open package closes (legacy rule).
                    package_session_id = await self._resolve_open_package_session_id(
                        item.material_id, user_id
                    )

                usage = models.TreatmentMaterialUsage(
                    treatment_id=None,
                    care_session_id=session_id,
                    work_item_id=data.work_item_id,
                    material_id=item.material_id,
                    session_id=package_session_id,
                    weight_score=item.weight_score or 1.0,
                    quantity_used=quantity_used,
                    cost_calculated=cost_calculated,
                    is_manual_override=False,
                    tenant_id=self.tenant_id,
                )
                self.db.add(usage)
                usages.append(usage)

            await self.db.flush()
        except HTTPException:
            raise
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict while recording care session materials",
            ) from exc

        now = datetime.now(timezone.utc)
        self.db.add(
            models.ClinicalEvent(
                tenant_id=self.tenant_id,
                patient_id=patient_id,
                care_session_id=session_id,
                work_item_id=data.work_item_id,
                event_type="care_session_materials_recorded",
                occurred_at=now,
                actor_user_id=user_id,
                payload={
                    "session_id": session_id,
                    "work_item_id": data.work_item_id,
                    "usage_ids": [u.id for u in usages],
                    "items": [
                        {"material_id": i.material_id, "quantity": i.quantity}
                        for i in data.items
                    ],
                },
            )
        )
        log_admin_action(
            db=self.db,
            admin_user=user,
            action="RECORD_CARE_SESSION_MATERIALS",
            entity_type="care_session",
            entity_id=session_id,
            details=f"Recorded {len(usages)} material usage row(s) for care session {session_id}",
            new_value={"usage_ids": [u.id for u in usages]},
            tenant_id=self.tenant_id,
        )

        try:
            await self.db.commit()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict while committing care session materials",
            ) from exc

        return await self._load_usages([u.id for u in usages])

    async def _load_usages(self, usage_ids: List[int]) -> List[models.TreatmentMaterialUsage]:
        stmt = (
            select(models.TreatmentMaterialUsage)
            .where(
                models.TreatmentMaterialUsage.id.in_(usage_ids),
                models.TreatmentMaterialUsage.tenant_id == self.tenant_id,
            )
            .order_by(models.TreatmentMaterialUsage.id.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # -----------------------------------------------------------------------
    # G13-M09: Aggregate work-item material cost across sessions
    # -----------------------------------------------------------------------

    async def _to_read(
        self, usages: List[models.TreatmentMaterialUsage]
    ) -> List[schemas.CareSessionMaterialUsageRead]:
        ids = {u.material_id for u in usages}
        names: Dict[int, tuple] = {}
        if ids:
            rows = await self.db.execute(
                select(
                    inv_models.Material.id,
                    inv_models.Material.name,
                    inv_models.Material.type,
                ).where(
                    inv_models.Material.id.in_(ids),
                    inv_models.Material.tenant_id == self.tenant_id,
                )
            )
            names = {mid: (name, mtype) for mid, name, mtype in rows.all()}
        return [
            schemas.CareSessionMaterialUsageRead(
                id=u.id,
                care_session_id=u.care_session_id,
                work_item_id=u.work_item_id,
                material_id=u.material_id,
                material_name=names.get(u.material_id, (None, None))[0],
                material_type=names.get(u.material_id, (None, None))[1],
                session_id=u.session_id,
                weight_score=u.weight_score,
                quantity_used=u.quantity_used,
                cost_calculated=(
                    float(u.cost_calculated) if u.cost_calculated is not None else None
                ),
                created_at=u.created_at,
            )
            for u in usages
        ]

    async def to_usage_reads(
        self, usages: List[models.TreatmentMaterialUsage]
    ) -> List[schemas.CareSessionMaterialUsageRead]:
        return await self._to_read(usages)

    async def get_work_item_material_cost(
        self, patient_id: int, work_item_id: int
    ) -> schemas.WorkItemMaterialCostRead:
        """
        Aggregate material usage and cost across every care session of a work item.
        Usages whose cost is not yet resolved (open divisible packages) are counted in
        `pending_cost_count` and contribute 0 until the package closes.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        await self._verify_work_item(patient_id, work_item_id)

        stmt = (
            select(models.TreatmentMaterialUsage)
            .where(
                models.TreatmentMaterialUsage.tenant_id == self.tenant_id,
                models.TreatmentMaterialUsage.work_item_id == work_item_id,
            )
            .order_by(
                models.TreatmentMaterialUsage.care_session_id.asc(),
                models.TreatmentMaterialUsage.id.asc(),
            )
        )
        usages = list((await self.db.execute(stmt)).scalars().all())
        reads = await self._to_read(usages)

        by_session: Dict[Optional[int], List[schemas.CareSessionMaterialUsageRead]] = defaultdict(list)
        for r in reads:
            by_session[r.care_session_id].append(r)

        sessions = []
        total = Decimal("0")
        total_pending = 0
        for cs_id, rows in by_session.items():
            cost = sum(
                (as_decimal(r.cost_calculated) for r in rows if r.cost_calculated is not None),
                Decimal("0"),
            )
            pending = sum(1 for r in rows if r.cost_calculated is None)
            total += cost
            total_pending += pending
            sessions.append(
                schemas.WorkItemSessionMaterialCost(
                    care_session_id=cs_id,
                    usage_count=len(rows),
                    pending_cost_count=pending,
                    cost=float(quantize_money(cost)),
                    usages=rows,
                )
            )

        return schemas.WorkItemMaterialCostRead(
            work_item_id=work_item_id,
            total_cost=float(quantize_money(total)),
            usage_count=len(reads),
            pending_cost_count=total_pending,
            sessions=sessions,
        )
