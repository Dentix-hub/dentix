from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List

from backend.models.inventory import ProcedureMaterialWeight, Batch, StockItem, Material
from backend.models.clinical import Procedure


class CostEngine:
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def get_material_average_cost(self, material_id: int) -> float:
        """
        Calculates the weighted average cost of a MATERIAL UNIT (e.g. per gram).
        Considers packaging_ratio to convert Batch Cost (Per Box) to Base Unit Cost.
        """
        # 1. Active Stock
        stock_query = (
            self.db.query(
                StockItem.quantity, Batch.cost_per_unit, Material.packaging_ratio
            )
            .select_from(StockItem)
            .join(Batch, StockItem.batch_id == Batch.id)
            .join(Material, Batch.material_id == Material.id)
            .filter(
                StockItem.tenant_id == self.tenant_id,
                Batch.material_id == material_id,
                StockItem.quantity > 0,
            )
            .all()
        )

        total_base_qty = sum(item.quantity for item in stock_query)
        total_value = 0.0

        for qty, box_cost, ratio in stock_query:
            # box_cost is per PACKAGE (e.g. 2000 for 4g)
            # ratio is package size (e.g. 4.0)
            # base_unit_cost = box_cost / ratio
            effective_ratio = ratio if ratio and ratio > 0 else 1.0
            unit_cost = box_cost / effective_ratio
            total_value += qty * unit_cost

        if total_base_qty > 0:
            return total_value / total_base_qty

        # 2. Fallback: Latest Batch
        last_batch = (
            self.db.query(Batch, Material)
            .select_from(Batch)
            .join(Material, Batch.material_id == Material.id)
            .filter(
                Batch.tenant_id == self.tenant_id,
                Batch.material_id == material_id,
                Batch.cost_per_unit > 0,
            )
            .order_by(Batch.created_at.desc())
            .first()
        )

        if last_batch:
            batch, mat = last_batch
            effective_ratio = (
                mat.packaging_ratio
                if mat.packaging_ratio and mat.packaging_ratio > 0
                else 1.0
            )
            return batch.cost_per_unit / effective_ratio

        return 0.0

    def calculate_procedure_cost(self, procedure_id: int) -> Dict[str, Any]:
        """
        Calculates the theoretical cost of a procedure based on its BOM.
        Includes Coverage Analysis (how many procedures per pack).
        """
        # 1. Get Procedure Info
        proc = self.db.query(Procedure).filter(Procedure.id == procedure_id).first()
        if not proc:
            return {"error": "Procedure not found"}

        # 2. Get BOM (Weights)
        weights = (
            self.db.query(ProcedureMaterialWeight)
            .options(joinedload(ProcedureMaterialWeight.material))
            .filter(
                ProcedureMaterialWeight.procedure_id == procedure_id,
                ProcedureMaterialWeight.tenant_id == self.tenant_id,
            )
            .all()
        )

        total_cost = 0.0
        total_actual_cost = 0.0
        details = []

        for w in weights:
            if not w.material:
                continue

            unit_cost = self.get_material_average_cost(w.material_id)
            material_cost = w.weight * unit_cost

            # AI / Actual Usage Logic
            # current_average_usage holds the learned "Actual Grams"
            # Defensive access for potentially missing column
            current_avg = getattr(w, "current_average_usage", 0.0)
            actual_usage = current_avg if current_avg and current_avg > 0 else 0.0
            actual_material_cost = actual_usage * unit_cost

            # Theoretical Cost logic:
            # Since 'weight' is a Relative Score (not grams), we cannot calculate standard cost directly from it
            # without a "Grams per Score" factor.
            # For now, we assume the AI-Learned cost IS the best estimate.
            # So estimated_cost converges to actual_cost.
            estimated_cost = actual_material_cost

            # Coverage Analysis
            # Pack Size = packaging_ratio
            pkg_ratio_val = getattr(w.material, "packaging_ratio", 1.0)
            pkg_ratio = pkg_ratio_val if pkg_ratio_val and pkg_ratio_val > 0 else 1.0

            # Coverage: How many services per Pack using ACTUAL usage?
            # If actual usage is 0, we can't estimate coverage yet.
            coverage_per_pack = pkg_ratio / actual_usage if actual_usage > 0 else 0

            cost_per_pack = unit_cost * pkg_ratio

            total_cost += estimated_cost
            total_actual_cost += actual_material_cost

            details.append(
                {
                    "material_id": w.material_id,
                    "material_name": w.material.name,
                    "base_unit": w.material.base_unit,
                    "weight_score": w.weight,  # Renamed key to emphasize it is a Score
                    "weight_used": w.weight,  # Keep backward compat for UI just in case, but value is Score
                    "unit_cost": round(unit_cost, 2),
                    "estimated_cost": round(estimated_cost, 2),
                    # AI Data
                    "actual_usage": round(actual_usage, 4),
                    "actual_cost": round(actual_material_cost, 2),
                    "sample_size": w.sample_size or 0,
                    # Coverage Info
                    "pack_size": pkg_ratio,
                    "cost_per_pack": round(cost_per_pack, 2),
                    "coverage_per_pack": round(coverage_per_pack, 1),
                }
            )

        current_price = proc.price or 0.0

        # Theoretical Margin
        margin = current_price - total_cost
        margin_percent = (margin / current_price * 100) if current_price > 0 else 0.0

        # Actual Margin (AI)
        # If total_actual_cost is 0 (no data), we might show 0 or null?
        # Let's calculate it purely.
        actual_margin = current_price - total_actual_cost
        actual_margin_percent = (
            (actual_margin / current_price * 100) if current_price > 0 else 0.0
        )

        return {
            "procedure_id": procedure_id,
            "procedure_name": proc.name,
            "total_estimated_cost": round(total_cost, 2),
            "total_actual_cost": round(total_actual_cost, 2),
            "current_price": current_price,
            "profit_margin": round(margin, 2),
            "margin_percentage": round(margin_percent, 1),
            "actual_profit_margin": round(actual_margin, 2),
            "actual_margin_percentage": round(actual_margin_percent, 1),
            "breakdown": details,
        }

    def calculate_all_procedures_costs(self) -> List[Dict[str, Any]]:
        """
        Calculates cost analysis for ALL procedures.
        Optimized to avoid N+1 where possible, but reuses core logic for consistency.
        """
        procedures = (
            self.db.query(Procedure).filter(Procedure.tenant_id == self.tenant_id).all()
        )
        results = []

        for proc in procedures:
            # We reuse the single calculation to ensure logic consistency (DRY)
            # Performance note: If this becomes slow, we should bulk-fetch material costs first.
            try:
                analysis = self.calculate_procedure_cost(proc.id)
                if "error" not in analysis:
                    results.append(
                        {
                            "id": proc.id,
                            "name": proc.name,
                            "price": analysis["current_price"],
                            "cost": analysis[
                                "total_actual_cost"
                            ],  # Using AI/Actual cost as the source of truth
                            "margin": analysis["actual_profit_margin"],
                            "margin_percent": analysis["actual_margin_percentage"],
                            "materials_count": len(analysis["breakdown"]),
                        }
                    )
            except Exception as e:
                print(f"[COST_ENGINE ERROR] Procedure {proc.id}: {e}")
                import traceback

                traceback.print_exc()
                continue

        # Sort by lowest margin percent by default to highlight issues
        results.sort(key=lambda x: x["margin_percent"])
        return results
