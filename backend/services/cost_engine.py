import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.core.money import as_decimal, quantize_money
from backend.models.clinical import Procedure, Treatment
from backend.models.inventory import (
    Batch,
    Material,
    ProcedureMaterialWeight,
    StockItem,
    TreatmentMaterialUsage,
)

logger = logging.getLogger(__name__)


class CostEngine:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_material_cost_basis(self, material_id: int) -> tuple[Decimal, str]:
        """Return tenant material unit cost plus provenance.

        A zero cost is treated as unavailable evidence, not as a free material.
        """
        stmt = (
            select(StockItem.quantity, Batch.cost_per_unit)
            .select_from(StockItem)
            .join(Batch, StockItem.batch_id == Batch.id)
            .where(
                StockItem.tenant_id == self.tenant_id,
                Batch.material_id == material_id,
                StockItem.quantity > 0,
            )
        )
        stock_query = (await self.db.execute(stmt)).all()

        total_base_qty = sum(
            (as_decimal(item.quantity) for item in stock_query), Decimal("0")
        )
        total_value = Decimal("0")
        for qty, batch_cost_per_unit in stock_query:
            total_value += as_decimal(qty) * as_decimal(batch_cost_per_unit)

        if total_base_qty > 0 and total_value > 0:
            return total_value / total_base_qty, "active_stock"

        stmt_fallback = (
            select(Batch)
            .where(
                Batch.tenant_id == self.tenant_id,
                Batch.material_id == material_id,
                Batch.cost_per_unit > 0,
            )
            .order_by(Batch.created_at.desc())
            .limit(1)
        )
        last_batch = (await self.db.execute(stmt_fallback)).scalars().first()
        if last_batch:
            return as_decimal(last_batch.cost_per_unit), "latest_batch"

        return Decimal("0"), "missing"

    async def get_material_average_cost(self, material_id: int) -> Decimal:
        """Compatibility helper returning only the unit cost."""
        cost, _ = await self.get_material_cost_basis(material_id)
        return cost

    async def _procedure_usage_average(
        self,
        *,
        procedure_name: str,
        material_id: int,
    ) -> tuple[Decimal, int]:
        """Return actual usage evidence scoped to this procedure and material."""
        stmt = (
            select(
                func.avg(TreatmentMaterialUsage.quantity_used),
                func.count(TreatmentMaterialUsage.id),
            )
            .join(Treatment, TreatmentMaterialUsage.treatment_id == Treatment.id)
            .where(
                TreatmentMaterialUsage.material_id == material_id,
                TreatmentMaterialUsage.tenant_id == self.tenant_id,
                TreatmentMaterialUsage.quantity_used.isnot(None),
                Treatment.procedure == procedure_name,
                Treatment.is_deleted == False,  # noqa: E712
            )
        )
        average, sample_count = (await self.db.execute(stmt)).one()
        return as_decimal(average), int(sample_count or 0)

    @staticmethod
    def _confidence_for_sample(sample_size: int, complete: bool) -> str:
        if not complete:
            return "unavailable"
        if sample_size >= 10:
            return "high"
        if sample_size >= 3:
            return "medium"
        return "low"

    async def calculate_procedure_cost(self, procedure_id: int) -> Dict[str, Any]:
        """Calculate estimated material margin with explicit evidence metadata.

        This is not full clinical profitability.  Margin values are withheld when
        the BOM, usage, or material cost evidence is incomplete so the API never
        turns missing cost into an artificial 100% margin.
        """
        stmt_proc = select(Procedure).where(
            Procedure.id == procedure_id,
            or_(
                Procedure.tenant_id == self.tenant_id,
                Procedure.tenant_id.is_(None),
            ),
        )
        proc = (await self.db.execute(stmt_proc)).scalars().first()
        if not proc:
            return {"error": "Procedure not found"}

        stmt_w = (
            select(ProcedureMaterialWeight)
            .options(joinedload(ProcedureMaterialWeight.material))
            .where(
                ProcedureMaterialWeight.procedure_id == procedure_id,
                or_(
                    ProcedureMaterialWeight.tenant_id == self.tenant_id,
                    ProcedureMaterialWeight.tenant_id.is_(None),
                ),
            )
        )
        weights = (await self.db.execute(stmt_w)).scalars().all()

        total_cost = Decimal("0")
        details: list[Dict[str, Any]] = []
        complete_items = 0
        missing_cost_items = 0
        missing_usage_items = 0
        unresolved_items = 0
        confidence_scores: list[int] = []
        score_map = {"unavailable": 0, "low": 1, "medium": 2, "high": 3}

        for w in weights:
            if not w.material:
                unresolved_items += 1
                details.append(
                    {
                        "material_id": w.material_id,
                        "material_name": None,
                        "base_unit": None,
                        "weight_score": w.weight,
                        "weight_used": w.weight,
                        "unit_cost": None,
                        "estimated_cost": None,
                        "actual_usage": None,
                        "actual_cost": None,
                        "sample_size": int(w.sample_size or 0),
                        "source": "unresolved",
                        "cost_source": "missing",
                        "confidence": "unavailable",
                        "complete": False,
                        "pack_size": None,
                        "cost_per_pack": None,
                        "coverage_per_pack": None,
                    }
                )
                confidence_scores.append(0)
                continue

            unit_cost, cost_source = await self.get_material_cost_basis(w.material_id)

            learned_average = as_decimal(getattr(w, "current_average_usage", 0.0))
            if learned_average > 0:
                actual_usage = learned_average
                usage_sample_size = int(w.sample_size or 0)
                usage_source = "learning"
            else:
                actual_usage, usage_sample_size = await self._procedure_usage_average(
                    procedure_name=proc.name,
                    material_id=w.material_id,
                )
                usage_source = "actual_usage" if actual_usage > 0 else "missing"

            has_cost = unit_cost > 0
            has_usage = actual_usage > 0
            complete = has_cost and has_usage
            if not has_cost:
                missing_cost_items += 1
            if not has_usage:
                missing_usage_items += 1
            if complete:
                complete_items += 1

            material_cost = actual_usage * unit_cost if complete else Decimal("0")
            total_cost += material_cost

            pkg_ratio_val = getattr(w.material, "packaging_ratio", 1.0)
            pkg_ratio = (
                as_decimal(pkg_ratio_val)
                if pkg_ratio_val and pkg_ratio_val > 0
                else Decimal("1")
            )
            coverage_per_pack = (
                pkg_ratio / actual_usage if actual_usage > 0 else None
            )
            cost_per_pack = unit_cost * pkg_ratio if unit_cost > 0 else None
            confidence = self._confidence_for_sample(usage_sample_size, complete)
            confidence_scores.append(score_map[confidence])

            details.append(
                {
                    "material_id": w.material_id,
                    "material_name": w.material.name,
                    "base_unit": w.material.base_unit,
                    "weight_score": w.weight,
                    "weight_used": w.weight,
                    "unit_cost": (
                        float(quantize_money(unit_cost)) if unit_cost > 0 else None
                    ),
                    "estimated_cost": (
                        float(quantize_money(material_cost)) if complete else None
                    ),
                    "actual_usage": round(float(actual_usage), 4) if has_usage else None,
                    "actual_cost": (
                        float(quantize_money(material_cost)) if complete else None
                    ),
                    "sample_size": usage_sample_size,
                    "source": usage_source,
                    "cost_source": cost_source,
                    "confidence": confidence,
                    "complete": complete,
                    "pack_size": float(pkg_ratio),
                    "cost_per_pack": (
                        float(quantize_money(cost_per_pack))
                        if cost_per_pack is not None
                        else None
                    ),
                    "coverage_per_pack": (
                        round(float(coverage_per_pack), 1)
                        if coverage_per_pack is not None
                        else None
                    ),
                }
            )

        expected_items = len(weights)
        coverage_percent = (
            round((complete_items / expected_items) * 100, 1)
            if expected_items > 0
            else 0.0
        )
        is_complete = expected_items > 0 and complete_items == expected_items
        if is_complete:
            min_score = min(confidence_scores) if confidence_scores else 0
            confidence = {3: "high", 2: "medium", 1: "low"}.get(min_score, "low")
            data_status = "complete"
        elif complete_items > 0:
            confidence = "low"
            data_status = "partial"
        else:
            confidence = "unavailable"
            data_status = "unavailable"

        current_price = as_decimal(proc.price)
        if is_complete:
            margin = current_price - total_cost
            margin_percent = (
                (margin / current_price * 100) if current_price > 0 else Decimal("0")
            )
            margin_value: Optional[float] = float(quantize_money(margin))
            margin_percent_value: Optional[float] = round(float(margin_percent), 1)
            material_cost_value: Optional[float] = float(quantize_money(total_cost))
        else:
            margin_value = None
            margin_percent_value = None
            material_cost_value = None

        return {
            "definition_version": "estimated-material-margin-v2",
            "metric_name": "estimated_material_margin",
            "metric_scope": "materials_only",
            "procedure_id": procedure_id,
            "procedure_name": proc.name,
            "current_price": float(quantize_money(current_price)),
            "total_estimated_cost": material_cost_value,
            "total_actual_cost": material_cost_value,
            "profit_margin": margin_value,
            "margin_percentage": margin_percent_value,
            "actual_profit_margin": margin_value,
            "actual_margin_percentage": margin_percent_value,
            "coverage": {
                "status": data_status,
                "is_complete": is_complete,
                "coverage_percent": coverage_percent,
                "expected_materials": expected_items,
                "complete_materials": complete_items,
                "missing_cost_materials": missing_cost_items,
                "missing_usage_materials": missing_usage_items,
                "unresolved_materials": unresolved_items,
                "confidence": confidence,
            },
            "breakdown": details,
        }

    async def calculate_all_procedures_costs(self) -> List[Dict[str, Any]]:
        """Compatibility bulk response, now with explicit reliability metadata."""
        stmt_p = select(Procedure).where(
            or_(
                Procedure.tenant_id == self.tenant_id,
                Procedure.tenant_id.is_(None),
            )
        )
        procedures = (await self.db.execute(stmt_p)).scalars().all()
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
                            "coverage": analysis["coverage"],
                            "definition_version": analysis["definition_version"],
                        }
                    )
            except Exception as exc:
                logger.error(
                    "[COST_ENGINE] Procedure %s: %s", proc.id, exc, exc_info=True
                )
                results.append(
                    {
                        "id": proc.id,
                        "name": proc.name,
                        "price": float(quantize_money(as_decimal(proc.price))),
                        "cost": None,
                        "margin": None,
                        "margin_percent": None,
                        "materials_count": 0,
                        "coverage": {
                            "status": "error",
                            "is_complete": False,
                            "coverage_percent": 0.0,
                            "confidence": "unavailable",
                        },
                        "definition_version": "estimated-material-margin-v2",
                        "error": "analysis_failed",
                    }
                )

        results.sort(
            key=lambda item: (
                item.get("margin_percent") is None,
                item.get("margin_percent") if item.get("margin_percent") is not None else 0,
                item.get("name") or "",
            )
        )
        return results

    async def calculate_material_margin_report(
        self,
        *,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
        sort: str = "name_asc",
    ) -> Dict[str, Any]:
        """Paginated server report; never downloads the whole catalog to React."""
        filters = [
            or_(
                Procedure.tenant_id == self.tenant_id,
                Procedure.tenant_id.is_(None),
            )
        ]
        if search:
            filters.append(Procedure.name.ilike(f"%{search}%"))

        count_stmt = select(func.count(Procedure.id)).where(*filters)
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        order_map = {
            "name_asc": Procedure.name.asc(),
            "name_desc": Procedure.name.desc(),
            "price_asc": Procedure.price.asc(),
            "price_desc": Procedure.price.desc(),
        }
        order_by = order_map.get(sort, Procedure.name.asc())
        stmt = (
            select(Procedure)
            .where(*filters)
            .order_by(order_by, Procedure.id.asc())
            .offset(skip)
            .limit(limit)
        )
        procedures = (await self.db.execute(stmt)).scalars().all()

        items = []
        error_count = 0
        for proc in procedures:
            try:
                analysis = await self.calculate_procedure_cost(proc.id)
            except Exception as exc:
                logger.error(
                    "[COST_ENGINE] Report procedure %s: %s", proc.id, exc, exc_info=True
                )
                error_count += 1
                items.append(
                    {
                        "procedure_id": proc.id,
                        "procedure_name": proc.name,
                        "current_price": float(quantize_money(as_decimal(proc.price))),
                        "material_cost": None,
                        "material_margin": None,
                        "margin_percent": None,
                        "coverage_percent": 0.0,
                        "confidence": "unavailable",
                        "status": "error",
                    }
                )
                continue

            coverage = analysis.get("coverage", {})
            items.append(
                {
                    "procedure_id": proc.id,
                    "procedure_name": proc.name,
                    "current_price": analysis.get("current_price"),
                    "material_cost": analysis.get("total_actual_cost"),
                    "material_margin": analysis.get("actual_profit_margin"),
                    "margin_percent": analysis.get("actual_margin_percentage"),
                    "coverage_percent": coverage.get("coverage_percent", 0.0),
                    "confidence": coverage.get("confidence", "unavailable"),
                    "status": coverage.get("status", "unavailable"),
                    "expected_materials": coverage.get("expected_materials", 0),
                    "complete_materials": coverage.get("complete_materials", 0),
                    "missing_cost_materials": coverage.get("missing_cost_materials", 0),
                    "missing_usage_materials": coverage.get("missing_usage_materials", 0),
                    "unresolved_materials": coverage.get("unresolved_materials", 0),
                }
            )

        complete_count = sum(1 for item in items if item["status"] == "complete")
        partial_count = sum(1 for item in items if item["status"] == "partial")
        unavailable_count = sum(
            1 for item in items if item["status"] in {"unavailable", "error"}
        )
        page_count = len(items)
        page_coverage_percent = (
            round((complete_count / page_count) * 100, 1) if page_count else 0.0
        )

        return {
            "definition_version": "estimated-material-margin-v2",
            "metric_name": "estimated_material_margin",
            "metric_scope": "materials_only",
            "warning": (
                "Incomplete procedures have null margin values; missing cost is never treated as zero."
                if partial_count or unavailable_count or error_count
                else None
            ),
            "items": items,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "returned": page_count,
            },
            "completeness": {
                "scope": "current_page",
                "complete": complete_count,
                "partial": partial_count,
                "unavailable": unavailable_count,
                "errors": error_count,
                "coverage_percent": page_coverage_percent,
            },
        }
