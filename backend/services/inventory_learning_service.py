import logging
import json
from datetime import datetime
from typing import List, Dict

from sqlalchemy.orm import Session, joinedload
from ..models import inventory as inv_models
from ..models import clinical as clinical_models

logger = logging.getLogger(__name__)


class InventoryLearningService:
    def __init__(self, db: Session):
        self.db = db

    def close_session(self, session_id: int, total_consumed: float, user_id: int):
        """
        Closes a material session and triggers the smart learning algorithm
        to distribute consumption based on procedure weights.
        """

        try:
            session = (
                self.db.query(inv_models.MaterialSession)
                .options(
                    joinedload(inv_models.MaterialSession.stock_item).joinedload(
                        inv_models.StockItem.batch
                    )
                )
                .filter(inv_models.MaterialSession.id == session_id)
                .first()
            )

            if not session:
                raise ValueError(f"Session {session_id} not found")

            if not session.stock_item:
                raise ValueError("CRITICAL: Session has no linked StockItem")

            if not session.stock_item.batch:
                # Attempt simpler reload if joinedload failed?
                # OR just fail gracefully
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
        session.closed_at = datetime.utcnow()
        session.total_amount_consumed = total_consumed

        # 2. Find Relevant Treatments (Since session open until now)
        # Filter by: Tenant, Doctor (if assigned to doctor), Room (if assigned to warehouse)
        # Ideally, we link treatments to the room/warehouse, but Doctor is a good proxy for personal stock.

        query = self.db.query(clinical_models.Treatment).filter(
            clinical_models.Treatment.date >= session.opened_at,
            clinical_models.Treatment.date <= session.closed_at,
            clinical_models.Treatment.tenant_id == session.stock_item.tenant_id,
        )

        # If session belongs to a doctor, filter by that doctor
        if session.doctor_id:
            query = query.filter(
                clinical_models.Treatment.doctor_id == session.doctor_id
            )

        treatments = query.all()

        if not treatments:
            # No treatments found found to distribute usage?
            # Log it but don't crash. Maybe it was spilled or used for untracked items.
            self._log_learning(
                session, total_consumed, {"error": "No treatments found in window"}
            )
            session.remaining_est = 0
            self.db.commit()
            return

        # 3. Calculate Distribution
        # Find WEIGHTS for these procedures
        # We need to match Treatment.procedure (String name) to Procedure (Table) -> ProcedureMaterialWeight

        # Get unique procedure names from treatments
        proc_names = list(set([t.procedure for t in treatments if t.procedure]))

        # Resolve names to IDs
        # FIX: Include global procedures (tenant_id is NULL) as well as tenant-specific ones
        from sqlalchemy import or_

        procs = (
            self.db.query(clinical_models.Procedure)
            .filter(
                clinical_models.Procedure.name.in_(proc_names),
                or_(
                    clinical_models.Procedure.tenant_id == session.stock_item.tenant_id,
                    clinical_models.Procedure.tenant_id.is_(None),  # Global procedures
                ),
            )
            .all()
        )

        proc_map = {p.name: p.id for p in procs}

        # Get Material ID
        material_id = session.stock_item.batch.material_id

        # Get Weights
        weights = (
            self.db.query(inv_models.ProcedureMaterialWeight)
            .filter(
                inv_models.ProcedureMaterialWeight.material_id == material_id,
                inv_models.ProcedureMaterialWeight.procedure_id.in_(proc_map.values()),
            )
            .all()
        )

        weight_map = {w.procedure_id: w for w in weights}  # Map ProcID -> WeightObj

        # ALGORITHM
        total_weight_score = 0
        distribution_log = []

        # Build treatment-based weight map from TreatmentMaterialUsage records
        # These were saved when the treatment was created
        treatment_usages = (
            self.db.query(inv_models.TreatmentMaterialUsage)
            .filter(
                inv_models.TreatmentMaterialUsage.session_id == session_id,
                inv_models.TreatmentMaterialUsage.material_id == material_id,
            )
            .all()
        )

        # Map: treatment_id -> TreatmentMaterialUsage
        usage_map = {u.treatment_id: u for u in treatment_usages}

        for t in treatments:
            if not t.procedure:
                continue

            pid = proc_map.get(t.procedure)
            if not pid:
                continue  # Procedure not configured in DB?

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
            self._log_learning(
                session, total_consumed, {"error": "Total weight score is zero"}
            )
            self.db.commit()
            return

        # Calculate "Unit Weight Value" (How much material per 1.0 weight)
        unit_weight_value = total_consumed / total_weight_score

        # 4. Update TreatmentMaterialUsage records with actual quantity and cost
        # Also update ProcedureMaterialWeight learning
        learning_updates = {}
        usage_updates = []

        # Get unit cost from batch for cost calculation
        unit_cost = session.stock_item.batch.cost_per_unit or 0.0

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
            usage_rec.cost_calculated = actual_quantity * unit_cost
            usage_updates.append({
                "treatment_id": t.id,
                "quantity": actual_quantity,
                "cost": usage_rec.cost_calculated
            })

        # 5. Update ProcedureMaterialWeight learning (by category for global defaults)
        # Find weights by category for this material
        category_weights = (
            self.db.query(inv_models.ProcedureMaterialWeight)
            .join(inv_models.Material, inv_models.ProcedureMaterialWeight.category_id == inv_models.Material.category_id)
            .filter(
                inv_models.Material.id == material_id,
                inv_models.ProcedureMaterialWeight.procedure_id.in_(proc_map.values()),
            )
            .all()
        )

        for w_obj in category_weights:
            # Observed Usage for this procedure type = Weight * Unit Weight Value
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

        self._log_learning(session, total_consumed, log_data)

        # 6. Adjust Stock (Ensure remaining is 0)
        # Usage logic handled separately?
        # usually closing a session implies it is empty.
        if session.stock_item.quantity > 0:
            # Deduct remaining
            session.stock_item.quantity = 0

        try:
            self.db.commit()
        except Exception as e:
            logger.exception("An exception occurred", exc_info=True)
            self.db.rollback()
            raise ValueError(f"Transaction failed: {str(e)}")

    def _log_learning(self, session, total_consumed, log_data):
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
        # Note: We do not commit here to keep it within the transaction of close_session

    def get_suggested_materials(
        self, procedure_id: int, tenant_id: int, doctor_id: int = None
    ) -> List[Dict]:
        """
        Get suggested materials for a procedure based on:
        1. Defined Weights (ProcedureMaterialWeight) - Primary Source (Specific Material or Category)
        2. Clinic Inventory (Tenant's Materials matching the Category)
        3. Learning History (Adaptive Adjustment)
        """
        # 1. Get Base Weights for this procedure (Global or Tenant-specific)
        from sqlalchemy import or_
        weights = (
            self.db.query(inv_models.ProcedureMaterialWeight)
            .filter(
                inv_models.ProcedureMaterialWeight.procedure_id == procedure_id,
                or_(
                    inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
                    inv_models.ProcedureMaterialWeight.tenant_id.is_(None)
                )
            )
            .all()
        )

        suggestions = []

        for w in weights:
            resolved_materials = []
            
            # CASE A: Specific Material assigned to this weight
            if w.material_id:
                mat = self.db.query(inv_models.Material).filter(inv_models.Material.id == w.material_id).first()
                if mat:
                    resolved_materials.append(mat)
            
            # CASE B: Category assigned - Find materials in this category for this tenant
            elif w.category_id:
                mats = (
                    self.db.query(inv_models.Material)
                    .filter(
                        inv_models.Material.category_id == w.category_id,
                        inv_models.Material.tenant_id == tenant_id
                    )
                    .all()
                )
                resolved_materials.extend(mats)

            # If no materials found for this weight/category in this tenant, return category placeholder
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
                # Base quantity from weight
                quantity = w.weight
                confidence = 0.8
                reason = "Standard Protocol"

                # Adjust based on history (Smart Learning)
                if w.current_average_usage and w.sample_size and w.sample_size > 5:
                    # If we have enough data, lean towards the average usage
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
