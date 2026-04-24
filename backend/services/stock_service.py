"""
Stock Service

Extracted from inventory_service.py.
Handles: stock consume, validate, movement recording.
"""

import logging
from datetime import datetime, timezone
from typing import Tuple, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.inventory import (
    Material,
    Batch,
    StockItem,
    StockMovement,
    MaterialSession,
)

logger = logging.getLogger(__name__)


class StockService:
    """Central stock operations logic."""

    def __init__(self, db: Session = None, tenant_id: int = None):
        self.db = db
        self.tenant_id = tenant_id

    def _get_db(self, db: Session = None):
        return db or self.db

    # --- Stock Validation ---

    def validate_stock(
        self,
        material_id: int,
        quantity: float,
        tenant_id: int,
        warehouse_id: Optional[int] = None,
        db: Session = None,
    ) -> Tuple[bool, float, str]:
        """
        Check if stock is sufficient without consuming.
        Returns: (is_sufficient, available_qty, material_name)
        """
        db = self._get_db(db)

        # Get material name
        mat = (
            db.query(Material)
            .filter(Material.id == material_id, Material.tenant_id == tenant_id)
            .first()
        )
        mat_name = mat.name if mat else f"Unknown Material {material_id}"

        # Sum quantity (global if warehouse_id is None)
        query = (
            db.query(func.coalesce(func.sum(StockItem.quantity), 0))
            .join(Batch)
            .filter(
                Batch.material_id == material_id,
                StockItem.quantity > 0,
                StockItem.tenant_id == tenant_id,
            )
        )

        if warehouse_id:
            query = query.filter(StockItem.warehouse_id == warehouse_id)

        # Check for active session (opened package = virtual availability)
        has_active_session = (
            db.query(MaterialSession)
            .join(StockItem)
            .join(Batch)
            .filter(
                Batch.material_id == material_id,
                MaterialSession.status == "ACTIVE",
            )
            .count()
            > 0
        )

        if has_active_session:
            return True, 9999.0, mat_name

        total_available = query.scalar()
        return (total_available >= quantity), total_available, mat_name

    # --- Stock Consumption ---

    def consume_stock(
        self,
        material_id: int,
        quantity: float,
        tenant_id: int,
        user_id: int,
        reference_id: str,
        db: Session = None,
    ) -> StockMovement:
        """
        Consume stock for a material.

        Flow:
        1. Find stock items with active sessions or available quantity
        2. Deduct quantity (FIFO)
        3. Handle CONFIRM_OPEN_REQUIRED for non-divisible materials
        4. Record movement
        """
        db = self._get_db(db)

        # Get stock items for this material
        stock_items = (
            db.query(StockItem)
            .join(Batch)
            .filter(
                Batch.material_id == material_id,
                StockItem.tenant_id == tenant_id,
                StockItem.quantity > 0,
            )
            .order_by(StockItem.id)
            .all()
        )

        if not stock_items:
            raise ValueError("No stock available for this material")

        # Check for active session first
        active_session = (
            db.query(MaterialSession)
            .join(StockItem)
            .join(Batch)
            .filter(
                Batch.material_id == material_id,
                MaterialSession.status == "ACTIVE",
            )
            .first()
        )

        remaining = quantity

        # If we have an active session, consume from it first
        if active_session:
            stock_item = active_session.stock_item
            material = stock_item.batch.material

            if material.type == "DIVISIBLE":
                # For divisible materials, consume from session remaining
                deduct = min(remaining, active_session.remaining_amount or 0)
                if deduct > 0:
                    active_session.remaining_amount = (
                        active_session.remaining_amount or stock_item.quantity
                    ) - deduct
                    stock_item.quantity -= deduct
                    remaining -= deduct

                    # Record movement
                    movement = self._record_movement(
                        db, stock_item.id, user_id, "CONSUME", deduct, reference_id
                    )
                    db.add(movement)

                    if remaining <= 0:
                        db.commit()
                        return movement

            elif material.type == "NON_DIVISIBLE":
                # For non-divisible, consume 1 unit from active session
                if remaining >= 1 and active_session.remaining_amount >= 1:
                    active_session.remaining_amount -= 1
                    stock_item.quantity -= 1
                    remaining -= 1

                    movement = self._record_movement(
                        db, stock_item.id, user_id, "CONSUME", 1, reference_id
                    )
                    db.add(movement)

                    if remaining <= 0:
                        db.commit()
                        return movement

        # If we still have remaining quantity, find new stock items
        if remaining > 0:
            for stock_item in stock_items:
                if stock_item.id == (active_session.stock_item_id if active_session else None):
                    continue  # Skip already processed

                material = stock_item.batch.material

                if material.type == "NON_DIVISIBLE":
                    if stock_item.quantity < 1:
                        raise ValueError(
                            f"CONFIRM_OPEN_REQUIRED:{stock_item.id}:{material.name} "
                            f"(Need to open new package)"
                        )

                    # Consume 1 unit
                    stock_item.quantity -= 1
                    remaining -= 1

                    # Open new session
                    session = MaterialSession(
                        stock_item_id=stock_item.id,
                        user_id=user_id,
                        opened_at=datetime.now(timezone.utc),
                        remaining_amount=stock_item.quantity,
                        status="ACTIVE",
                    )
                    db.add(session)

                    movement = self._record_movement(
                        db, stock_item.id, user_id, "CONSUME", 1, reference_id
                    )
                    db.add(movement)

                    if remaining <= 0:
                        db.commit()
                        return movement

                elif material.type == "DIVISIBLE":
                    deduct = min(remaining, stock_item.quantity)
                    stock_item.quantity -= deduct
                    remaining -= deduct

                    # Open session for remainder
                    session = MaterialSession(
                        stock_item_id=stock_item.id,
                        user_id=user_id,
                        opened_at=datetime.now(timezone.utc),
                        remaining_amount=stock_item.quantity,
                        status="ACTIVE",
                    )
                    db.add(session)

                    movement = self._record_movement(
                        db, stock_item.id, user_id, "CONSUME", deduct, reference_id
                    )
                    db.add(movement)

                    if remaining <= 0:
                        db.commit()
                        return movement

        if remaining > 0:
            raise ValueError(f"Insufficient stock. Still need {remaining} units")

        db.commit()

    def _record_movement(
        self,
        db: Session,
        stock_item_id: int,
        user_id: int,
        movement_type: str,
        quantity: float,
        reference_id: str,
    ) -> StockMovement:
        return StockMovement(
            stock_item_id=stock_item_id,
            user_id=user_id,
            movement_type=movement_type,
            quantity=quantity,
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc),
        )

    # --- Stock Summary ---

    def get_stock_summary(self, tenant_id: int, db: Session = None) -> List[dict]:
        """Get stock summary by material."""
        db = self._get_db(db)

        results = (
            db.query(
                Material.id,
                Material.name,
                Material.unit,
                func.coalesce(func.sum(StockItem.quantity), 0).label("total_quantity"),
            )
            .join(Batch)
            .join(StockItem)
            .filter(Material.tenant_id == tenant_id)
            .group_by(Material.id, Material.name, Material.unit)
            .all()
        )

        return [
            {
                "material_id": r.id,
                "name": r.name,
                "unit": r.unit,
                "total_quantity": float(r.total_quantity),
            }
            for r in results
        ]


def get_stock_service(db: Session, tenant_id: int) -> StockService:
    return StockService(db, tenant_id)


# Singleton instance for backward compatibility
stock_service = StockService()
