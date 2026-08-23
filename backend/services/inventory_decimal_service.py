"""Exact-money inventory adapter used by financial reporting.

The legacy inventory service serializes COGS to ``float`` before returning it.
That became unsafe once persisted money columns moved to PostgreSQL NUMERIC and
therefore arrive as ``Decimal``.  This adapter keeps the calculation exact and
only lets HTTP response layers serialize the final value.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.money import as_decimal, quantize_money
from backend.models.inventory import Batch, Material, StockItem, StockMovement
from backend.services.inventory_service import InventoryService


class DecimalInventoryService(InventoryService):
    async def get_cogs_summary(
        self,
        start_date,
        end_date,
        tenant_id: int,
        db: AsyncSession = None,
    ) -> Decimal:
        db = self._get_db(db)
        stmt = (
            select(StockMovement, Batch, Material)
            .join(StockItem, StockItem.id == StockMovement.stock_item_id)
            .join(Batch, Batch.id == StockItem.batch_id)
            .join(Material, Material.id == Batch.material_id)
            .where(
                StockMovement.reason.in_(["USAGE", "EXPIRED"]),
                StockMovement.created_at >= start_date,
                StockMovement.created_at <= end_date,
                Batch.tenant_id == tenant_id,
            )
        )
        movements = (await db.execute(stmt)).all()

        total_cogs = Decimal("0")
        for move, batch, material in movements:
            quantity = as_decimal(abs(move.change_amount or 0))
            unit_cost = as_decimal(batch.cost_per_unit)
            if unit_cost <= 0:
                unit_cost = as_decimal(material.standard_price)
            total_cogs += quantity * unit_cost

        return quantize_money(total_cogs)


inventory_service_decimal = DecimalInventoryService()
