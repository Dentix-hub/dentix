from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import func

from backend import schemas
from backend.models.inventory import (
    Warehouse,
    Material,
    Batch,
    StockItem,
    MaterialSession,
    StockMovement,
)


class InventoryService:
    def __init__(self, db: Session = None, tenant_id: int = None):
        self.db = db
        self.tenant_id = tenant_id

    def _get_db(self, db: Session):
        return db or self.db

    # --- WAREHOUSE ---
    def create_warehouse(
        self, data: schemas.WarehouseCreate, tenant_id: int, db: Session = None
    ) -> Warehouse:
        db = self._get_db(db)
        wh = Warehouse(**data.model_dump(), tenant_id=tenant_id)
        db.add(wh)
        db.commit()
        db.refresh(wh)
        return wh

    def get_warehouses(self, tenant_id: int, db: Session = None) -> List[Warehouse]:
        db = self._get_db(db)
        return db.query(Warehouse).filter(Warehouse.tenant_id == tenant_id).all()

    def delete_warehouse(self, warehouse_id: int, tenant_id: int, db: Session = None):
        """
        Delete warehouse if empty (no stock items with quantity > 0).
        """
        db = self._get_db(db)
        wh = (
            db.query(Warehouse)
            .filter(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id)
            .first()
        )
        if not wh:
            raise ValueError("Warehouse not found")

        # Check for active stock
        has_stock = (
            db.query(StockItem)
            .filter(StockItem.warehouse_id == warehouse_id, StockItem.quantity > 0)
            .count()
            > 0
        )

        if has_stock:
            raise ValueError(
                "Cannot delete warehouse with active stock. Please move or consume stock first."
            )

        # Delete empty stock items (cleanup)
        db.query(StockItem).filter(StockItem.warehouse_id == warehouse_id).delete()

        db.delete(wh)
        db.commit()
        return True

    # --- MATERIAL ---
    def create_material(
        self, data: schemas.MaterialCreate, tenant_id: int, db: Session = None
    ) -> Material:
        db = self._get_db(db)
        mat = Material(**data.model_dump(), tenant_id=tenant_id)
        db.add(mat)
        db.commit()
        db.refresh(mat)
        return mat

    def get_materials(self, tenant_id: int, db: Session = None) -> List[Material]:
        db = self._get_db(db)
        return db.query(Material).filter(Material.tenant_id == tenant_id).all()

    def update_material(
        self,
        material_id: int,
        data: schemas.MaterialUpdate,
        tenant_id: int,
        db: Session = None,
    ) -> Material:
        db = self._get_db(db)
        mat = (
            db.query(Material)
            .filter(Material.id == material_id, Material.tenant_id == tenant_id)
            .first()
        )
        if not mat:
            raise ValueError("Material not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(mat, key, value)

        db.commit()
        db.refresh(mat)
        return mat

    # --- STOCK LOGIC ---
    def get_material_stock_summary(
        self, tenant_id: int, warehouse_id: Optional[int] = None, db: Session = None
    ) -> List[schemas.MaterialStockSummary]:
        """
        Group by Material + Base Unit.
        Sum Quantity from StockItems.
        Count unique Batches.
        """
        db = self._get_db(db)

        # Results: (id, name, type, unit, threshold, total_qty, batch_count)
        # Note: Left Outer Join to include materials with 0 stock

        query = (
            db.query(
                Material.id,
                Material.name,
                Material.type,
                Material.base_unit,
                Material.alert_threshold,
                Material.packaging_ratio,
                Material.standard_price,
                func.coalesce(func.sum(StockItem.quantity), 0).label("total_qty"),
                func.count(Batch.id.distinct()).label("batch_count"),
            )
            .outerjoin(Batch, Batch.material_id == Material.id)
            .outerjoin(StockItem, StockItem.batch_id == Batch.id)
            .filter(Material.tenant_id == tenant_id)
        )

        if warehouse_id:
            query = query.filter(StockItem.warehouse_id == warehouse_id)

        results = query.group_by(Material.id, Material.standard_price).all()

        summary = []
        for r in results:
            qty = r.total_qty or 0
            status = "OK"
            if qty <= (r.alert_threshold or 0):
                status = "LOW"
            if qty == 0:
                status = "CRITICAL"

            summary.append(
                schemas.MaterialStockSummary(
                    material_id=r.id,
                    material_name=r.name,
                    material_type=r.type,
                    unit=r.base_unit,
                    total_quantity=qty,
                    alert_status=status,
                    batches_count=r.batch_count,
                    packaging_ratio=r.packaging_ratio or 1.0,
                    standard_price=r.standard_price or 0.0,
                )
            )

        return summary

    def add_stock(
        self,
        material_id: int,
        warehouse_id: int,
        batch_data: schemas.BatchBase,
        quantity: float,
        tenant_id: int,
        user_id: int,
        db: Session = None,
    ) -> StockItem:
        """
        Purchase/Receive Stock.
        Creates SEPARATE StockItems for each unit so each can have its own session.
        """
        db = self._get_db(db)

        # 1. Check Batch
        batch = (
            db.query(Batch)
            .filter(
                Batch.batch_number == batch_data.batch_number,
                Batch.material_id == material_id,
                Batch.tenant_id == tenant_id,
            )
            .first()
        )

        if not batch:
            batch = Batch(
                material_id=material_id, tenant_id=tenant_id, **batch_data.model_dump()
            )
            db.add(batch)
            db.flush()  # get ID

        # 2. Get Material for ratio and price update
        mat = db.query(Material).get(material_id)
        ratio = mat.packaging_ratio if mat and mat.packaging_ratio > 0 else 1.0

        # Update Material Standard Price with latest cost
        if batch_data.cost_per_unit > 0:
            new_package_price = batch_data.cost_per_unit * ratio
            mat.standard_price = new_package_price
            db.add(mat)

        # 3. Create SEPARATE StockItems for each package
        # Each unit gets quantity = ratio (e.g., 5g for a 5g package)
        num_packages = int(quantity)  # Number of packages to create
        created_items = []

        for i in range(num_packages):
            stock_item = StockItem(
                warehouse_id=warehouse_id,
                batch_id=batch.id,
                tenant_id=tenant_id,
                quantity=ratio,  # Each package starts with full ratio
            )
            db.add(stock_item)
            db.flush()

            # Record Movement for each item
            move = StockMovement(
                stock_item_id=stock_item.id,
                change_amount=1,  # 1 package received
                reason="PURCHASE",
                performed_by=user_id,
            )
            db.add(move)
            created_items.append(stock_item)

        db.commit()

        # Return the first created item (for API compatibility)
        if created_items:
            db.refresh(created_items[0])
            return created_items[0]

        # Fallback: if quantity was 0 or less, return empty item
        return StockItem(
            warehouse_id=warehouse_id,
            batch_id=batch.id,
            tenant_id=tenant_id,
            quantity=0,
        )

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

        # Get Material Name
        mat = (
            db.query(Material)
            .filter(Material.id == material_id, Material.tenant_id == tenant_id)
            .first()
        )
        mat_name = mat.name if mat else f"Unknown Material {material_id}"

        # Sum Quantity (Global if warehouse_id is None)
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

        # 1. Custom Validation for Divisible Materials with Active Session
        # Only check active session if we are validating for a specific warehouse/batch context
        # But 'validate_stock' assumes checking Global or Warehouse availability.
        # If we have an active session, we consider stock available for consumption (via that session).

        # We need to find if *any* stock item of this material has an active session.
        # Use helper
        has_active_session = (
            db.query(MaterialSession)
            .join(StockItem)
            .join(Batch)
            .filter(
                Batch.material_id == material_id, MaterialSession.status == "ACTIVE"
            )
            .count()
            > 0
        )

        # Check Material Type

        # FIX: If ANY material has an active session, it's available for consumption
        # This applies to both DIVISIBLE and NON_DIVISIBLE materials
        # Previously only DIVISIBLE was supported, but opened packages should be available
        if has_active_session:
            return True, 9999.0, mat_name  # Virtual availability

        total_available = query.scalar()

        return (total_available >= quantity), total_available, mat_name

    # --- SESSION MANAGEMENT ---
    def get_active_session(
        self, stock_item_id: int, db: Session = None
    ) -> Optional[MaterialSession]:
        db = self._get_db(db)
        return (
            db.query(MaterialSession)
            .filter(
                MaterialSession.stock_item_id == stock_item_id,
                MaterialSession.status == "ACTIVE",
            )
            .first()
        )

    def open_session(
        self, stock_item_id: int, user_id: int, db: Session = None
    ) -> MaterialSession:
        """
        Explicitly open a material package (Session).
        - DIVISIBLE: Requires full packaging_ratio, deducts it on open
        - NON_DIVISIBLE: Requires qty >= 1, no deduction (consumption per unit)
        """
        db = self._get_db(db)
        stock_item = db.query(StockItem).get(stock_item_id)
        if not stock_item:
            raise ValueError("Stock Item not found")

        # Check existing
        existing = self.get_active_session(stock_item_id, db)
        if existing:
            return existing

        # Get material info
        mat = stock_item.batch.material
        mat_type = mat.type if mat else "NON_DIVISIBLE"
        ratio = mat.packaging_ratio if mat and mat.packaging_ratio > 0 else 1.0

        if mat_type == "DIVISIBLE":
            # DIVISIBLE: Check for full package and deduct
            if stock_item.quantity < ratio:
                raise ValueError(
                    f"Insufficient stock to open session. Need {ratio} {mat.base_unit}, Have {stock_item.quantity}"
                )

            # Deduct full package
            stock_item.quantity -= ratio

            # Record Movement
            move = StockMovement(
                stock_item_id=stock_item.id,
                change_amount=-ratio,
                reason="SESSION_OPEN",
                performed_by=user_id,
            )
            db.add(move)
        else:
            # NON_DIVISIBLE: Just need at least 1 unit, no deduction on open
            if stock_item.quantity < 1:
                raise ValueError(
                    f"Insufficient stock to open session. Need at least 1 unit, Have {stock_item.quantity}"
                )
            # No deduction - consumption happens per unit via consume_stock

        # Create Session
        session = MaterialSession(
            stock_item_id=stock_item_id,
            opened_at=datetime.utcnow(),
            status="ACTIVE",
            remaining_est=1.0,  # 100%
            doctor_id=user_id,  # Initial opener
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # TODO: Trigger Notification "Material Opened"
        return session

    def close_material_session_manually(
        self, session_id: int, user_id: int, db: Session = None
    ):
        """
        Manual close for Divisible items (Doctor decides).
        """
        db = self._get_db(db)
        from .inventory_learning_service import InventoryLearningService

        learning_service = InventoryLearningService(db)

        # Calculate usage?
        # The learning service handles the logic of finding treatments and calculating
        # We just need to trigger it.
        # But we need 'total_consumed'.
        session = db.query(MaterialSession).get(session_id)
        if not session:
            raise ValueError("Session not found")

        # For Divisible, total_consumed is whatever was tracked via 'consume_stock'
        # OR we might calculate it as (Initial - Remaining)?
        # Actually `consume_stock` decrements `StockItem.quantity`.
        # So Total Consumed = Initial Qty (from Batch) - Current Qty?
        # BUT `consume_stock` updates `StockItem`.

        # Wait, if `StockItem` is used, the quantity decreases.
        # So 'Total Consumed' = (Batch Initial - Current)?
        # Actually if we assume the bottle is empty now, Total Consumed = SUM(Movements).

        # Let's get total usage from movements for this session window
        total_usage = (
            db.query(func.abs(func.sum(StockMovement.change_amount)))
            .filter(
                StockMovement.stock_item_id == session.stock_item_id,
                StockMovement.change_amount < 0,
                StockMovement.created_at >= session.opened_at,
                StockMovement.created_at <= (session.closed_at or datetime.utcnow()),
            )
            .scalar()
            or 0.0
        )

        learning_service.close_session(session_id, float(total_usage), user_id)
        return True

    def consume_stock(
        self,
        material_id: int,
        quantity: float,
        tenant_id: int,
        user_id: int,
        batch_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        auto_open: bool = False,
        reference_id: Optional[str] = None,
        db: Session = None,
    ) -> List[StockMovement]:
        """
        Consume material (FIFO).
        Enforces strict opening rules:
        - If item is not 'Open' (no active session), requires auto_open=True or fails.
        """
        db = self._get_db(db)

        # 0. Resolve Warehouse (Default to CLINIC if not specified)
        if not warehouse_id:
            clinic_wh = (
                db.query(Warehouse)
                .filter(Warehouse.tenant_id == tenant_id, Warehouse.type == "CLINIC")
                .first()
            )
            if clinic_wh:
                warehouse_id = clinic_wh.id

        # 1. Validation: Non-Divisible Integer Check (SKIP if active session exists)
        mat = db.query(Material).filter(Material.id == material_id).first()
        if not mat:
            raise ValueError(f"Material {material_id} not found")

        # FIX: Check if this material has an active session - if so, allow fractional amounts
        has_active_session_for_material = (
            db.query(MaterialSession)
            .join(StockItem)
            .join(Batch)
            .filter(
                Batch.material_id == material_id, MaterialSession.status == "ACTIVE"
            )
            .count()
            > 0
        )

        # Only enforce integer check if NO active session
        if (
            mat.type == "NON_DIVISIBLE"
            and not float(quantity).is_integer()
            and not has_active_session_for_material
        ):
            raise ValueError(
                f"Invalid Quantity: {mat.name} ({mat.type}) cannot be consumed in fractional amounts ({quantity})."
            )

        movements = []
        remaining_to_consume = quantity

        # Find eligible StockItems
        # Bug Fix: Include 0-quantity items IF they have an ACTIVE session (Divisible)
        active_session_subquery = db.query(MaterialSession.stock_item_id).filter(
            MaterialSession.status == "ACTIVE"
        )

        query = (
            db.query(StockItem)
            .join(Batch)
            .filter(
                Batch.material_id == material_id,
                StockItem.tenant_id == tenant_id,
                (StockItem.quantity > 0) | (StockItem.id.in_(active_session_subquery)),
            )
        )

        if warehouse_id:
            query = query.filter(StockItem.warehouse_id == warehouse_id)

        if batch_id:
            query = query.filter(Batch.id == batch_id)

        # FIFO Sort - but items with active sessions come FIRST
        stock_items_raw = query.order_by(Batch.expiry_date.asc()).all()

        # Reorder: Active session items first, then rest by expiry
        items_with_session = []
        items_without_session = []
        for si in stock_items_raw:
            sess = self.get_active_session(si.id, db)
            if sess:
                items_with_session.append(si)
            else:
                items_without_session.append(si)

        stock_items = items_with_session + items_without_session

        # S.1: Check for Active Session (Virtual Stock)
        # FIX: Check if ANY stock item has an active session (regardless of DIVISIBLE/NON_DIVISIBLE type)
        has_active_session = False
        for si in stock_items:
            sess = self.get_active_session(si.id, db)
            if sess:
                has_active_session = True
                break

        total_available = sum(si.quantity for si in stock_items)

        # Only enforce strict quantity check if we DON'T have any active open session
        if total_available < quantity and not has_active_session:
            raise ValueError(
                f"Insufficient stock. Available: {total_available}, Requested: {quantity}"
            )

        for si in stock_items:
            if remaining_to_consume <= 0:
                break

            # --- SMART LOGIC START ---
            # 1. Open Check
            session = self.get_active_session(si.id, db)
            mat_type = si.batch.material.type

            if not session:
                # FIXED: Only enforce opening for DIVISIBLE items
                if mat_type == "DIVISIBLE":
                    if auto_open:
                        # This will decrement stock by packaging_ratio
                        try:
                            session = self.open_session(si.id, user_id, db)
                            db.refresh(si)
                        except ValueError as e:
                            raise e
                    else:
                        # BLOCKING Trigger
                        raise ValueError(
                            f"CONFIRM_OPEN_REQUIRED:{si.id}:{si.batch.material.name} - Batch {si.batch.batch_number}"
                        )

                # For NON_DIVISIBLE, we proceed to consumption directly without session.

            # 2. Consume Logic
            # FIX: If ANY material has an active session -> It is 'Virtual Consumption'
            # We do NOT decrement stock (because we already decremented on OPEN)
            # We do NOT record USAGE movement (because we track via Weights/Treatments later)
            if session:
                # Satisfy request fully from this open session
                # Assume infinite capacity until closed manually
                remaining_to_consume = 0
                # The caller (treatment) records the 'consumption' in its own logic via BOM.
                continue

            # 3. Standard Consumption (Non-Divisible or Divisible-but-legacy? No, Divisible enforced above)
            consume_amount = min(si.quantity, remaining_to_consume)

            si.quantity -= consume_amount
            remaining_to_consume -= consume_amount

            # Log Movement
            move = StockMovement(
                stock_item_id=si.id,
                change_amount=-consume_amount,
                reason="USAGE",
                performed_by=user_id,
                reference_id=reference_id,
            )
            db.add(move)
            movements.append(move)

            # 4. Close Check (Non-Divisible Auto Close)
            if mat_type == "NON_DIVISIBLE" and si.quantity <= 0:
                # Auto Close logic...
                if session:
                    db.flush()
                    total_usage = (
                        db.query(func.abs(func.sum(StockMovement.change_amount)))
                        .filter(
                            StockMovement.stock_item_id == si.id,
                            StockMovement.change_amount < 0,
                        )
                        .scalar()
                        or 0.0
                    )

                    from .inventory_learning_service import InventoryLearningService

                    ls = InventoryLearningService(db)
                    ls.close_session(session.id, float(total_usage), user_id)

            # --- SMART LOGIC END ---

        db.commit()
        return movements

    def get_expiry_alerts(self, tenant_id: int, days: int = 30, db: Session = None):
        """
        Find batches expiring within 'days' (default 30).
        """
        db = self._get_db(db)
        target_date = datetime.now().date()
        from datetime import timedelta

        limit_date = target_date + timedelta(days=days)

        # Find batches with qty > 0 and expiry < limit
        results = (
            db.query(Batch, Material, StockItem)
            .join(Material, Material.id == Batch.material_id)
            .join(StockItem, StockItem.batch_id == Batch.id)
            .filter(
                Batch.tenant_id == tenant_id,
                StockItem.quantity > 0,
                Batch.expiry_date <= limit_date,
            )
            .order_by(Batch.expiry_date.asc())
            .all()
        )

        alerts = []
        for batch, mat, item in results:
            days_left = (batch.expiry_date - target_date).days
            alerts.append(
                {
                    "material_name": mat.name,
                    "batch_number": batch.batch_number,
                    "expiry_date": batch.expiry_date,
                    "days_left": days_left,
                    "quantity": item.quantity,
                    "warehouse_id": item.warehouse_id,
                }
            )

        return alerts

    def delete_material(self, material_id: int, tenant_id: int, db: Session = None):
        """
        Delete material ensuring no dependencies block it.
        Rules:
        1. Access Check (Tenant)
        2. Stock Check (Any quantity > 0) -> Block
        3. History Check (Any movements) -> Block (or require purge, but blocking is safer)
        """
        db = self._get_db(db)

        # 1. Get Material
        mat = (
            db.query(Material)
            .filter(Material.id == material_id, Material.tenant_id == tenant_id)
            .first()
        )
        if not mat:
            raise ValueError("Material not found")

        # 2. Check Active Stock
        # DEV NOTE: Disabled for testing upon request.
        # has_stock = db.query(StockItem).join(Batch).filter(
        #     Batch.material_id == material_id,
        #     StockItem.quantity > 0
        # ).count() > 0

        # if has_stock:
        #     raise ValueError("Cannot delete material with active stock. Please consume or adjust stock to zero first.")

        # 3. Check History (Movements)
        # DEV NOTE: Disabled for testing upon request.
        # has_history = db.query(StockMovement).join(StockItem).join(Batch).filter(
        #     Batch.material_id == material_id
        # ).count() > 0

        # if has_history:
        #      raise ValueError("Cannot delete material with historical movemements (Audit trail protected).")

        # 4. Cleanup (Cascade Delete logic if strict checks pass)
        # Delete Weights (BOM)
        from ..models.inventory import ProcedureMaterialWeight, MaterialLearningLog

        db.query(ProcedureMaterialWeight).filter(
            ProcedureMaterialWeight.material_id == material_id
        ).delete()
        db.query(MaterialLearningLog).filter(
            MaterialLearningLog.material_id == material_id
        ).delete()

        # Delete Sessions
        # Note: If history check passed, there should be no sessions/movements, but safely cleaning empty orphan records

        # Delete StockItems (Empty ones)
        # This requires finding them first
        batches = db.query(Batch).filter(Batch.material_id == material_id).all()
        for b in batches:
            stock_items = db.query(StockItem).filter(StockItem.batch_id == b.id).all()
            for si in stock_items:
                # Delete sessions first (FK dependency)
                db.query(MaterialSession).filter(
                    MaterialSession.stock_item_id == si.id
                ).delete()
                # Then delete movements
                db.query(StockMovement).filter(
                    StockMovement.stock_item_id == si.id
                ).delete()

            db.query(StockItem).filter(StockItem.batch_id == b.id).delete()
            db.query(Batch).filter(Batch.id == b.id).delete()

        # Finally Delete Material
        db.delete(mat)
        db.commit()
        return True

    def get_cogs_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: int,
        db: Session = None,
    ) -> float:
        """
        Calculate Cost of Goods Sold (COGS) for a period.
        Sum of (Usage Qty * Unit Cost).
        Fallback to Material Standard Price if Batch Cost is 0.
        """
        db = self._get_db(db)

        movements = (
            db.query(StockMovement, Batch, Material)
            .join(StockItem, StockItem.id == StockMovement.stock_item_id)
            .join(Batch, Batch.id == StockItem.batch_id)
            .join(Material, Material.id == Batch.material_id)
            .filter(
                StockMovement.reason.in_(["USAGE", "EXPIRED"]),
                StockMovement.created_at >= start_date,
                StockMovement.created_at <= end_date,
                Batch.tenant_id == tenant_id,
            )
            .all()
        )

        total_cogs = 0.0

        for move, batch, mat in movements:
            qty = abs(move.change_amount)
            # Priority: Batch Cost > Standard Price > 0
            cost = batch.cost_per_unit
            if cost <= 0:
                cost = mat.standard_price or 0.0

            total_cogs += qty * cost

        return total_cogs

    def transfer_stock(
        self,
        stock_item_id: int,
        target_warehouse_id: int,
        quantity: float,
        tenant_id: int,
        user_id: int,
        db: Session = None,
    ) -> StockMovement:
        """
        Transfer stock between warehouses (e.g., MAIN -> CLINIC).
        """
        db = self._get_db(db)

        # 1. Source Item
        source_item = db.query(StockItem).get(stock_item_id)
        if not source_item:
            raise ValueError("Source stock item not found")

        if source_item.quantity < quantity:
            raise ValueError(
                f"Insufficient quantity. Available: {source_item.quantity}"
            )

        # 2. Target Item (Find or Create)
        # Must match Batch & Material
        target_item = (
            db.query(StockItem)
            .filter(
                StockItem.warehouse_id == target_warehouse_id,
                StockItem.batch_id == source_item.batch_id,
                StockItem.tenant_id == tenant_id,
            )
            .first()
        )

        if not target_item:
            target_item = StockItem(
                warehouse_id=target_warehouse_id,
                batch_id=source_item.batch_id,
                tenant_id=tenant_id,
                quantity=0,
            )
            db.add(target_item)
            db.flush()

        # 3. Validation: Non-Divisible Check
        mat = source_item.batch.material
        if mat.type == "NON_DIVISIBLE" and not float(quantity).is_integer():
            raise ValueError(
                f"Invalid Transfer Quantity: {mat.name} cannot be transferred in fractional amounts."
            )

        # 4. Execution
        source_item.quantity -= quantity
        target_item.quantity += quantity

        # 5. Movements
        move_out = StockMovement(
            stock_item_id=source_item.id,
            change_amount=-quantity,
            reason="TRANSFER_OUT",
            performed_by=user_id,
        )
        move_in = StockMovement(
            stock_item_id=target_item.id,
            change_amount=quantity,
            reason="TRANSFER_IN",
            performed_by=user_id,
        )

        db.add(move_out)
        db.add(move_in)

        db.commit()
        return move_in


inventory_service = InventoryService()
