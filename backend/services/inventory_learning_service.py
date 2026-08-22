import logging
import json
from datetime import datetime, timezone
from typing import List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select, func, or_
from ..models import inventory as inv_models
from ..models import clinical as clinical_models
from ..core.money import as_decimal

logger = logging.getLogger(__name__)


class InventoryLearningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def close_session(self, session_id: int, total_consumed: float, user_id: int):
        """
        Closes a material session and triggers the smart learning algorithm
        to distribute consumption based on procedure weights.
        """

        try:
            stmt = (
                select(inv_models.MaterialSession)
                .options(
                    joinedload(inv_models.MaterialSession.stock_item).joinedload(
                        inv_models.StockItem.batch
                    )
                )
                .where(inv_models.MaterialSession.id == session_id)
            )
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                raise ValueError(f"Session {session_id} not found")

            if not session.stock_item:
                raise ValueError("CRITICAL: Session has no linked StockItem")

            if not session.stock_item.batch:
                raise ValueError(
                    "CRITICAL: StockItem has no linked Batch (Data Corruption)"
                )
        except Exception as e:
            raise e

        if session.status == "CLOSED":
            return {
                "success": True,
                "message": "Session already closed (Idempotent)",
                "already_closed": True,
            }

        # 1. Update Session Status
        session.status = "CLOSED"
        session.closed_at = datetime.now(timezone.utc)
        session.total_amount_consumed = total_consumed

        # 2. Find Relevant Treatments (Since session open until now)
        stmt_t = select(clinical_models.Treatment).where(
            clinical_models.Treatment.date >= session.opened_at,
            clinical_models.Treatment.date <= session.closed_at,
            clinical_models.Treatment.tenant_id == session.stock_item.tenant_id,
        )

        # If session belongs to a doctor, filter by that doctor
        if session.doctor_id:
            stmt_t = stmt_t.where(
                clinical_models.Treatment.doctor_id == session.doctor_id
            )

        res_t = await self.db.execute(stmt_t)
        treatments = res_t.scalars().all()

        if not treatments:
            await self._log_learning(
                session, total_consumed, {"error": "No treatments found in window"}
            )
            session.remaining_est = 0
            await self.db.commit()
            return

        # 3. Calculate Distribution
        # Get unique procedure names from treatments
        proc_names = list(set([t.procedure for t in treatments if t.procedure]))

        stmt_p = (
            select(clinical_models.Procedure)
            .where(
                clinical_models.Procedure.name.in_(proc_names),
                or_(
                    clinical_models.Procedure.tenant_id == session.stock_item.tenant_id,
                    clinical_models.Procedure.tenant_id.is_(None),  # Global procedures
                ),
            )
        )
        res_p = await self.db.execute(stmt_p)
        procs = res_p.scalars().all()

        proc_map = {p.name: p.id for p in procs}

        # Get Material ID
        material_id = session.stock_item.batch.material_id

        # Get Weights
        stmt_w = (
            select(inv_models.ProcedureMaterialWeight)
            .where(
                inv_models.ProcedureMaterialWeight.material_id == material_id,
                inv_models.ProcedureMaterialWeight.procedure_id.in_(proc_map.values()),
            )
        )
        res_w = await self.db.execute(stmt_w)
        weights = res_w.scalars().all()

        weight_map = {w.procedure_id: w for w in weights}  # Map ProcID -> WeightObj

        # ALGORITHM
        total_weight_score = 0
        distribution_log = []

        # Build treatment-based weight map from TreatmentMaterialUsage records
        stmt_u = (
            select(inv_models.TreatmentMaterialUsage)
            .where(
                inv_models.TreatmentMaterialUsage.session_id == session_id,
                inv_models.TreatmentMaterialUsage.material_id == material_id,
            )
        )
        res_u = await self.db.execute(stmt_u)
        treatment_usages = res_u.scalars().all()

        # Map: treatment_id -> TreatmentMaterialUsage
        usage_map = {u.treatment_id: u for u in treatment_usages}

        for t in treatments:
            if not t.procedure:
                continue

            pid = proc_map.get(t.procedure)
            if not pid:
                continue

            # Get weight from TreatmentMaterialUsage if exists, else from ProcedureMaterialWeight
            usage_rec = usage_map.get(t.id)
            if usage_rec and usage_rec.weight_score:
                weight_val = usage_rec.weight_score
            else:
                w_obj = weight_map.get(pid)
                weight_val = w_obj.weight if w_obj else 1.0

            total_weight_score += weight_val
            distribution_log.append(
                {"treatment_id": t.id, "procedure": t.procedure, "weight": weight_val}
            )

        if total_weight_score == 0:
            await self._log_learning(
                session, total_consumed, {"error": "Total weight score is zero"}
            )
            await self.db.commit()
            return

        # Calculate "Unit Weight Value"
        unit_weight_value = total_consumed / total_weight_score

        learning_updates = {}
        usage_updates = []

        # Get unit cost from batch for cost calculation
        unit_cost = as_decimal(session.stock_item.batch.cost_per_unit)

        for t in treatments:
            if not t.procedure:
                continue
            pid = proc_map.get(t.procedure)
            if not pid:
                continue

            # Get the TreatmentMaterialUsage record
            usage_rec = usage_map.get(t.id)
            if not usage_rec:
                continue

            # Calculate actual quantity used based on weight proportion
            weight_val = usage_rec.weight_score or 1.0
            actual_quantity = weight_val * unit_weight_value

            # Update usage record
            usage_rec.quantity_used = actual_quantity
            usage_rec.cost_calculated = as_decimal(actual_quantity) * unit_cost
            usage_updates.append({
                "treatment_id": t.id,
                "quantity": actual_quantity,
                "cost": usage_rec.cost_calculated
            })

        # 5. Update ProcedureMaterialWeight learning (by category for global defaults)
        stmt_cw = (
            select(inv_models.ProcedureMaterialWeight)
            .join(inv_models.Material, inv_models.ProcedureMaterialWeight.category_id == inv_models.Material.category_id)
            .where(
                inv_models.Material.id == material_id,
                inv_models.ProcedureMaterialWeight.procedure_id.in_(proc_map.values()),
            )
        )
        res_cw = await self.db.execute(stmt_cw)
        category_weights = res_cw.scalars().all()

        for w_obj in category_weights:
            observed_usage = w_obj.weight * unit_weight_value

            # Weighted Moving Average
            old_avg = w_obj.current_average_usage or 0.0
            if old_avg == 0:
                new_avg = observed_usage
            else:
                new_avg = (old_avg * 0.7) + (observed_usage * 0.3)

            w_obj.current_average_usage = new_avg
            w_obj.sample_size += 1

            learning_updates[w_obj.procedure_id] = {
                "old": old_avg,
                "observed": observed_usage,
                "new": new_avg,
            }

        # 6. Log EVERYTHING
        log_data = {
            "treatments_count": len(treatments),
            "total_weight_score": total_weight_score,
            "unit_weight_value": unit_weight_value,
            "dist_log": distribution_log,
            "usage_updates": usage_updates,
            "learning_updates": learning_updates,
        }

        await self._log_learning(session, total_consumed, log_data)

        # 6. Adjust Stock (Ensure remaining is 0)
        if session.stock_item.quantity > 0:
            session.stock_item.quantity = 0

        try:
            await self.db.commit()
        except Exception as e:
            logger.exception("An exception occurred", exc_info=True)
            await self.db.rollback()
            raise ValueError(f"Transaction failed: {str(e)}")

    async def _log_learning(self, session, total_consumed, log_data):
        """
        Helper to create a MaterialLearningLog entry.
        """
        log_entry = inv_models.MaterialLearningLog(
            material_id=session.stock_item.batch.material_id,
            tenant_id=session.stock_item.tenant_id,
            session_id=session.id,
            total_consumed=total_consumed,
            calculation_data=json.dumps(log_data),
        )
        self.db.add(log_entry)

    async def get_suggested_materials(
        self, procedure_id: int, tenant_id: int, doctor_id: int = None
    ) -> List[Dict]:
        """
        Get suggested materials for a procedure.
        """
        stmt_w = (
            select(inv_models.ProcedureMaterialWeight)
            .where(
                inv_models.ProcedureMaterialWeight.procedure_id == procedure_id,
                or_(
                    inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
                    inv_models.ProcedureMaterialWeight.tenant_id.is_(None)
                )
            )
        )
        res_w = await self.db.execute(stmt_w)
        weights = res_w.scalars().all()

        suggestions = []

        for w in weights:
            resolved_materials = []

            # CASE A: Specific Material
            if w.material_id:
                stmt_m = select(inv_models.Material).where(
                    inv_models.Material.id == w.material_id,
                    inv_models.Material.tenant_id == tenant_id,
                    inv_models.Material.is_deleted == False,  # noqa: E712
                )
                mat = (await self.db.execute(stmt_m)).scalars().first()
                if mat:
                    resolved_materials.append(mat)

            # CASE B: Category
            elif w.category_id:
                stmt_mats = (
                    select(inv_models.Material)
                    .where(
                        inv_models.Material.category_id == w.category_id,
                        inv_models.Material.tenant_id == tenant_id,
                        inv_models.Material.is_deleted == False,  # noqa: E712
                    )
                )
                res_mats = await self.db.execute(stmt_mats)
                resolved_materials.extend(res_mats.scalars().all())

            if not resolved_materials:
                suggestions.append({
                    "material_id": None,
                    "category_id": w.category_id,
                    "material": None,
                    "suggested_quantity": round(w.weight, 2),
                    "default_quantity": round(w.weight, 2),
                    "confidence": 0.3,
                    "reason": "لا توجد مواد في هذه الفئة بالعيادة",
                })
                continue

            for mat in resolved_materials:
                quantity = w.weight
                confidence = 0.8
                reason = "Standard Protocol"

                if w.current_average_usage and w.sample_size and w.sample_size > 5:
                    quantity = w.current_average_usage
                    confidence = 0.95
                    reason = f"Based on {w.sample_size} previous cases"

                suggestions.append(
                    {
                        "material_id": mat.id,
                        "material": {
                            "id": mat.id,
                            "name": mat.name,
                            "brand": mat.brand,
                            "base_unit": mat.base_unit,
                            "type": mat.type,
                            "category_id": mat.category_id,
                        },
                        "suggested_quantity": round(quantity, 2),
                        "default_quantity": round(w.weight, 2),
                        "confidence": confidence,
                        "reason": reason,
                    }
                )

        return suggestions
