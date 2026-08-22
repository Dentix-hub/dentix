import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from typing import Dict, Any, List

from sqlalchemy import func, or_, select
from backend.models.inventory import ProcedureMaterialWeight, Batch, StockItem, Material, TreatmentMaterialUsage
from backend.models.clinical import Procedure
from backend.core.money import as_decimal, quantize_money

logger = logging.getLogger(__name__)


class CostEngine:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_material_average_cost(self, material_id: int) -> Decimal:
        """
        Calculates the weighted average cost of a MATERIAL BASE UNIT (e.g. per gram).
        Batch.cost_per_unit already stores per-base-unit cost (frontend divides package_price / ratio).
        """
        # 1. Active Stock
        stmt = (
            select(
                StockItem.quantity, Batch.cost_per_unit, Material.packaging_ratio
            )
            .select_from(StockItem)
            .join(Batch, StockItem.batch_id == Batch.id)
            .join(Material, Batch.material_id == Material.id)
            .where(
                StockItem.tenant_id == self.tenant_id,
                Batch.material_id == material_id,
                StockItem.quantity > 0,
            )
        )
        result = await self.db.execute(stmt)
        stock_query = result.all()

        total_base_qty = sum((as_decimal(item.quantity) for item in stock_query), Decimal("0"))
        total_value = Decimal("0")

        for qty, batch_cost_per_unit, ratio in stock_query:
            unit_cost = as_decimal(batch_cost_per_unit)
            total_value += as_decimal(qty) * unit_cost

        if total_base_qty > 0:
            return total_value / total_base_qty

        # 2. Fallback: Latest Batch
        stmt_fallback = (
            select(Batch, Material)
            .select_from(Batch)
            .join(Material, Batch.material_id == Material.id)
            .where(
                Batch.tenant_id == self.tenant_id,
                Batch.material_id == material_id,
                Batch.cost_per_unit > 0,
            )
            .order_by(Batch.created_at.desc())
            .limit(1)
        )
        res_fallback = await self.db.execute(stmt_fallback)
        last_batch = res_fallback.first()

        if last_batch:
            batch, mat = last_batch
            return batch.cost_per_unit

        return Decimal("0")

    async def calculate_procedure_cost(self, procedure_id: int) -> Dict[str, Any]:
        """
        Calculates the theoretical cost of a procedure based on its BOM.
        Includes Coverage Analysis (how many procedures per pack).
        """
        # 1. Get Procedure Info
        stmt_proc = select(Procedure).where(Procedure.id == procedure_id)
        proc = (await self.db.execute(stmt_proc)).scalars().first()
        if not proc:
            return {"error": "Procedure not found"}

        # 2. Get BOM (Weights)
        stmt_w = (
            select(ProcedureMaterialWeight)
            .options(joinedload(ProcedureMaterialWeight.material))
            .where(
                ProcedureMaterialWeight.procedure_id == procedure_id,
                ProcedureMaterialWeight.tenant_id == self.tenant_id,
            )
        )
        result_w = await self.db.execute(stmt_w)
        weights = result_w.scalars().all()

        total_cost = Decimal("0")
        total_actual_cost = Decimal("0")
        details = []

        for w in weights:
            if not w.material:
                continue

            unit_cost = await self.get_material_average_cost(w.material_id)

            # AI / Actual Usage Logic
            # 1. Try learned average from ProcedureMaterialWeight
            current_avg = getattr(w, "current_average_usage", 0.0)

            # 2. Fallback: Calculate from actual TreatmentMaterialUsage records if no learning data
            if not current_avg or current_avg == 0:
                stmt_avg = (
                    select(func.avg(TreatmentMaterialUsage.quantity_used))
                    .where(
                        TreatmentMaterialUsage.material_id == w.material_id,
                        TreatmentMaterialUsage.tenant_id == self.tenant_id,
                        TreatmentMaterialUsage.quantity_used.isnot(None),
                    )
                )
                actual_usage_stats = await self.db.scalar(stmt_avg)
                if actual_usage_stats:
                    current_avg = float(actual_usage_stats)

            actual_usage = as_decimal(current_avg) if current_avg and current_avg > 0 else Decimal("0")
            actual_material_cost = actual_usage * unit_cost

            estimated_cost = actual_material_cost

            # Coverage Analysis
            pkg_ratio_val = getattr(w.material, "packaging_ratio", 1.0)
            pkg_ratio = as_decimal(pkg_ratio_val) if pkg_ratio_val and pkg_ratio_val > 0 else Decimal("1")

            coverage_per_pack = pkg_ratio / actual_usage if actual_usage > 0 else Decimal("0")

            cost_per_pack = unit_cost * pkg_ratio

            total_cost += estimated_cost
            total_actual_cost += actual_material_cost

            details.append(
                {
                    "material_id": w.material_id,
                    "material_name": w.material.name,
                    "base_unit": w.material.base_unit,
                    "weight_score": w.weight,
                    "weight_used": w.weight,
                    "unit_cost": float(quantize_money(unit_cost)),
                    "estimated_cost": float(quantize_money(estimated_cost)),
                    "actual_usage": round(float(actual_usage), 4),
                    "actual_cost": float(quantize_money(actual_material_cost)),
                    "sample_size": w.sample_size or 0,
                    "source": "learning" if (w.current_average_usage or 0) > 0 else ("actual_usage" if actual_usage > 0 else "estimated"),
                    "pack_size": float(pkg_ratio),
                    "cost_per_pack": float(quantize_money(cost_per_pack)),
                    "coverage_per_pack": round(float(coverage_per_pack), 1),
                }
            )

        current_price = as_decimal(proc.price)

        # Theoretical Margin
        margin = current_price - total_cost
        margin_percent = (margin / current_price * 100) if current_price > 0 else 0.0

        # Actual Margin (AI)
        actual_margin = current_price - total_actual_cost
        actual_margin_percent = (
            (actual_margin / current_price * 100) if current_price > 0 else 0.0
        )

        return {
            "procedure_id": procedure_id,
            "procedure_name": proc.name,
            "total_estimated_cost": float(quantize_money(total_cost)),
            "total_actual_cost": float(quantize_money(total_actual_cost)),
            "current_price": float(quantize_money(current_price)),
            "profit_margin": float(quantize_money(margin)),
            "margin_percentage": round(float(margin_percent), 1),
            "actual_profit_margin": float(quantize_money(actual_margin)),
            "actual_margin_percentage": round(float(actual_margin_percent), 1),
            "breakdown": details,
        }

    async def calculate_all_procedures_costs(self) -> List[Dict[str, Any]]:
        """
        Calculates cost analysis for ALL procedures.
        """
        stmt_p = (
            select(Procedure)
            .where(
                or_(
                    Procedure.tenant_id == self.tenant_id,
                    Procedure.tenant_id.is_(None),
                )
            )
        )
        res_p = await self.db.execute(stmt_p)
        procedures = res_p.scalars().all()
        results = []

        for proc in procedures:
            try:
                analysis = await self.calculate_procedure_cost(proc.id)
                if "error" not in analysis:
                    results.append(
                        {
                            "id": proc.id,
                            "name": proc.name,
                            "price": analysis["current_price"],
                            "cost": analysis["total_actual_cost"],
                            "margin": analysis["actual_profit_margin"],
                            "margin_percent": analysis["actual_margin_percentage"],
                            "materials_count": len(analysis["breakdown"]),
                        }
                    )
            except Exception as e:
                logger.error("[COST_ENGINE] Procedure %s: %s", proc.id, e, exc_info=True)
                continue

        results.sort(key=lambda x: x["margin_percent"])
        return results
