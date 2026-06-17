from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, select, or_
import logging

from backend import schemas

logger = logging.getLogger(__name__)
from backend.models.inventory import (
    Warehouse,
    Material,
    Batch,
    StockItem,
    MaterialCategory,
    MaterialSession,
    StockMovement,
)
from backend.models.financial import Expense


class InventoryService:
    def __init__(self, db: AsyncSession = None, tenant_id: int = None):
        self.db = db
        self.tenant_id = tenant_id

    def _get_db(self, db: AsyncSession):
        result = db or self.db
        if result is None:
            raise RuntimeError("No database session provided to InventoryService. Please pass db parameter to method calls.")
        return result

    # --- WAREHOUSE ---
    async def create_warehouse(
        self, data: schemas.WarehouseCreate, tenant_id: int, db: AsyncSession = None
    ) -> Warehouse:
        db = self._get_db(db)
        wh = Warehouse(**data.model_dump(), tenant_id=tenant_id)
        db.add(wh)
        await db.commit()
        await db.refresh(wh)
        return wh

    async def get_warehouses(self, tenant_id: int, db: AsyncSession = None) -> List[Warehouse]:
        db = self._get_db(db)
        stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_warehouse(self, warehouse_id: int, tenant_id: int, db: AsyncSession = None):
        """
        Delete warehouse if empty (no stock items with quantity > 0).
        """
        db = self._get_db(db)
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id)
        wh = (await db.execute(stmt)).scalars().first()
        if not wh:
            raise ValueError("Warehouse not found")

        # Check for active stock (with tenant isolation)
        stmt_stock = select(func.count(StockItem.id)).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.quantity > 0,
            StockItem.tenant_id == tenant_id
        )
        has_stock = (await db.scalar(stmt_stock) or 0) > 0

        if has_stock:
            raise ValueError(
                "Cannot delete warehouse with active stock. Please move or consume stock first."
            )

        # Delete empty stock items (cleanup)
        from sqlalchemy import delete
        stmt_del = delete(StockItem).where(StockItem.warehouse_id == warehouse_id)
        await db.execute(stmt_del)

        await db.delete(wh)
        await db.commit()
        return True

    # --- MATERIAL ---
    async def create_material(
        self, data: schemas.MaterialCreate, tenant_id: int, db: AsyncSession = None
    ) -> Material:
        db = self._get_db(db)
        mat = Material(**data.model_dump(), tenant_id=tenant_id)
        db.add(mat)
        await db.commit()
        await db.refresh(mat)
        return mat

    async def get_materials(self, tenant_id: int, db: AsyncSession = None) -> List[Material]:
        db = self._get_db(db)
        from sqlalchemy.orm import joinedload
        stmt = (
            select(Material)
            .options(joinedload(Material.category))
            .where(Material.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_material(
        self,
        material_id: int,
        data: schemas.MaterialUpdate,
        tenant_id: int,
        db: AsyncSession = None,
    ) -> Material:
        db = self._get_db(db)
        stmt = select(Material).where(Material.id == material_id, Material.tenant_id == tenant_id)
        mat = (await db.execute(stmt)).scalars().first()
        if not mat:
            raise ValueError("Material not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(mat, key, value)

        await db.commit()
        await db.refresh(mat)
        return mat

    # --- STOCK LOGIC ---
    async def get_material_stock_summary(
        self, tenant_id: int, warehouse_id: Optional[int] = None, db: AsyncSession = None
    ) -> List[schemas.MaterialStockSummary]:
        """
        Group by Material + Base Unit.
        Sum Quantity from StockItems.
        Count unique Batches.
        """
        db = self._get_db(db)

        # Results: (id, name, type, unit, threshold, total_qty, batch_count)
        # Note: Left Outer Join to include materials with 0 stock

        stmt = (
            select(
                Material.id,
                Material.name,
                Material.type,
                Material.brand,
                Material.base_unit,
                Material.alert_threshold,
                Material.packaging_ratio,
                Material.standard_price,
                MaterialCategory.name_ar.label("category_ar"),
                MaterialCategory.name_en.label("category_en"),
                func.coalesce(func.sum(StockItem.quantity), 0).label("total_qty"),
                func.count(Batch.id.distinct()).label("batch_count"),
            )
            .outerjoin(MaterialCategory, MaterialCategory.id == Material.category_id)
            .outerjoin(Batch, Batch.material_id == Material.id)
            .outerjoin(StockItem, StockItem.batch_id == Batch.id)
            .where(Material.tenant_id == tenant_id)
        )

        if warehouse_id:
            stmt = stmt.where(StockItem.warehouse_id == warehouse_id)

        stmt = stmt.group_by(
            Material.id,
            Material.brand,
            Material.standard_price,
            MaterialCategory.name_ar,
            MaterialCategory.name_en
        )

        result = await db.execute(stmt)
        results = result.all()

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
                    brand=r.brand,
                    unit=r.base_unit,
                    total_quantity=qty,
                    alert_status=status,
                    batches_count=r.batch_count,
                    packaging_ratio=r.packaging_ratio or 1.0,
                    standard_price=r.standard_price or 0.0,
                    category_name_ar=r.category_ar,
                    category_name_en=r.category_en,
                )
            )

        return summary

    async def add_stock(
        self,
        material_id: int,
        warehouse_id: int,
        batch_data: schemas.BatchBase,
        quantity: float,
        tenant_id: int,
        user_id: int,
        db: AsyncSession = None,
    ) -> StockItem:
        """
        Purchase/Receive Stock.
        Creates SEPARATE StockItems for each unit so each can have its own session.
        """
        db = self._get_db(db)

        # 1. Check Batch
        stmt_batch = select(Batch).where(
            Batch.batch_number == batch_data.batch_number,
            Batch.material_id == material_id,
            Batch.tenant_id == tenant_id,
        )
        batch = (await db.execute(stmt_batch)).scalars().first()

        if not batch:
            batch = Batch(
                material_id=material_id, tenant_id=tenant_id, **batch_data.model_dump()
            )
            db.add(batch)
            await db.flush()  # get ID

        # 2. Get Material for ratio and price update
        stmt_mat = select(Material).where(Material.id == material_id)
        mat = (await db.execute(stmt_mat)).scalars().first()
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
            await db.flush()

            # Record Movement for each item
            move = StockMovement(
                stock_item_id=stock_item.id,
                change_amount=1,  # 1 package received
                reason="PURCHASE",
                performed_by=user_id,
            )
            db.add(move)
            created_items.append(stock_item)

        # 4. Add to Expenses automatically
        if batch_data.cost_per_unit > 0:
            total_cost = batch_data.cost_per_unit * ratio * quantity
            expense = Expense(
                item_name=f"شراء: {mat.name}",
                cost=total_cost,
                category="مخزن",
                date=datetime.now(timezone.utc).date(),
                tenant_id=tenant_id,
                notes=f"استلام {quantity} عبوة - باتش: {batch_data.batch_number}"
            )
            db.add(expense)

        await db.commit()

        # Return the first created item (for API compatibility)
        if created_items:
            await db.refresh(created_items[0])
            return created_items[0]

        # Fallback: if quantity was 0 or less, return empty item
        return StockItem(
            warehouse_id=warehouse_id,
            batch_id=batch.id,
            tenant_id=tenant_id,
            quantity=0,
        )

    async def validate_stock(
        self,
        material_id: int,
        quantity: float,
        tenant_id: int,
        warehouse_id: Optional[int] = None,
        db: AsyncSession = None,
    ) -> Tuple[bool, float, str]:
        """
        Check if stock is sufficient without consuming.
        Returns: (is_sufficient, available_qty, material_name)
        """
        db = self._get_db(db)

        # Get Material Name
        stmt_mat = select(Material).where(Material.id == material_id, Material.tenant_id == tenant_id)
        mat = (await db.execute(stmt_mat)).scalars().first()
        mat_name = mat.name if mat else f"Unknown Material {material_id}"

        # Sum Quantity (Global if warehouse_id is None)
        stmt_sum = (
            select(func.coalesce(func.sum(StockItem.quantity), 0))
            .join(Batch)
            .where(
                Batch.material_id == material_id,
                StockItem.quantity > 0,
                StockItem.tenant_id == tenant_id,
            )
        )

        if warehouse_id:
            stmt_sum = stmt_sum.where(StockItem.warehouse_id == warehouse_id)

        # 1. Custom Validation for Divisible Materials with Active Session
        stmt_sess = (
            select(func.count(MaterialSession.id))
            .join(StockItem)
            .join(Batch)
            .where(
                Batch.material_id == material_id,
                MaterialSession.status == "ACTIVE"
            )
        )
        has_active_session = (await db.scalar(stmt_sess) or 0) > 0

        if has_active_session:
            if mat and mat.type in ("DIVISIBLE", "REUSABLE"):
                return True, float('inf'), mat_name  # Virtual availability for DIVISIBLE/REUSABLE

        total_available = await db.scalar(stmt_sum) or 0.0

        return (total_available >= quantity), total_available, mat_name

    # --- SESSION MANAGEMENT ---
    async def get_active_session(
        self, stock_item_id: int, db: AsyncSession = None
    ) -> Optional[MaterialSession]:
        db = self._get_db(db)
        stmt = select(MaterialSession).where(
            MaterialSession.stock_item_id == stock_item_id,
            MaterialSession.status == "ACTIVE",
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def open_session(
        self, stock_item_id: int, user_id: int, patient_id: Optional[int] = None, db: AsyncSession = None, commit: bool = True
    ) -> MaterialSession:
        """
        Explicitly open a material package (Session).
        - DIVISIBLE: Requires full packaging_ratio, deducts it on open
        - NON_DIVISIBLE: Requires qty >= 1, no deduction (consumption per unit)
        """
        db = self._get_db(db)

        # Load stock_item and its batch/material relations
        from sqlalchemy.orm import joinedload
        stmt_item = (
            select(StockItem)
            .options(joinedload(StockItem.batch).joinedload(Batch.material))
            .where(StockItem.id == stock_item_id)
        )
        stock_item = (await db.execute(stmt_item)).scalars().first()
        if not stock_item:
            raise ValueError("Stock Item not found")

        # Check existing
        existing = await self.get_active_session(stock_item_id, db)
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

        # Create Session
        session = MaterialSession(
            stock_item_id=stock_item_id,
            opened_at=datetime.now(timezone.utc),
            status="ACTIVE",
            remaining_est=1.0,  # 100%
            doctor_id=user_id,  # Initial opener
            patient_id=patient_id,
        )
        db.add(session)
        if commit:
            await db.commit()
            await db.refresh(session)

        return session

    async def close_material_session_manually(
        self, session_id: int, user_id: int, db: AsyncSession = None
    ):
        """
        Manual close for Divisible items (Doctor decides).
        """
        db = self._get_db(db)
        from .inventory_learning_service import InventoryLearningService

        learning_service = InventoryLearningService(db)

        stmt_sess = select(MaterialSession).where(MaterialSession.id == session_id)
        session = (await db.execute(stmt_sess)).scalars().first()
        if not session:
            raise ValueError("Session not found")

        # Let's get total usage from movements for this session window
        stmt_usage = (
            select(func.abs(func.sum(StockMovement.change_amount)))
            .where(
                StockMovement.stock_item_id == session.stock_item_id,
                StockMovement.change_amount < 0,
                StockMovement.created_at >= session.opened_at,
                StockMovement.created_at <= (session.closed_at or datetime.now(timezone.utc)),
            )
        )
        total_usage = await db.scalar(stmt_usage) or 0.0

        await learning_service.close_session(session_id, float(total_usage), user_id)
        return True

    async def consume_stock(
        self,
        material_id: int,
        quantity: float,
        tenant_id: int,
        user_id: int,
        batch_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        auto_open: bool = False,
        reference_id: Optional[str] = None,
        patient_id: Optional[int] = None,
        db: AsyncSession = None,
        commit: bool = True,
    ) -> List[StockMovement]:
        """
        Consume material (FIFO).
        Enforces strict opening rules:
        - If item is not 'Open' (no active session), requires auto_open=True or fails.
        """
        db = self._get_db(db)

        # 0. Resolve Warehouse (Default to CLINIC if not specified)
        if not warehouse_id:
            clinic_wh_stmt = select(Warehouse).where(
                Warehouse.tenant_id == tenant_id, Warehouse.type == "CLINIC"
            )
            clinic_wh = (await db.execute(clinic_wh_stmt)).scalars().first()
            if clinic_wh:
                warehouse_id = clinic_wh.id

        # 1. Validation: Non-Divisible Integer Check (SKIP if active session exists)
        stmt_mat = select(Material).where(Material.id == material_id)
        mat = (await db.execute(stmt_mat)).scalars().first()
        if not mat:
            raise ValueError(f"Material {material_id} not found")

        # Check if this material has an active session
        stmt_active_sess = (
            select(func.count(MaterialSession.id))
            .join(StockItem)
            .join(Batch)
            .where(
                Batch.material_id == material_id,
                MaterialSession.status == "ACTIVE"
            )
        )

        # If patient_id is provided, prioritize sessions for that patient
        if patient_id:
            stmt_active_sess = stmt_active_sess.where(
                MaterialSession.patient_id == patient_id
            )

        has_active_session_for_material = (await db.scalar(stmt_active_sess) or 0) > 0

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
        active_session_subquery = select(MaterialSession.stock_item_id).where(
            MaterialSession.status == "ACTIVE"
        )

        stmt_items = (
            select(StockItem)
            .join(Batch)
            .where(
                Batch.material_id == material_id,
                StockItem.tenant_id == tenant_id,
                or_(
                    StockItem.quantity > 0,
                    StockItem.id.in_(active_session_subquery)
                )
            )
        )

        if warehouse_id:
            stmt_items = stmt_items.where(StockItem.warehouse_id == warehouse_id)

        if batch_id:
            stmt_items = stmt_items.where(Batch.id == batch_id)

        # FIFO Sort
        stmt_items = stmt_items.order_by(Batch.expiry_date.asc())

        # Load relations eagerly
        from sqlalchemy.orm import joinedload
        stmt_items = stmt_items.options(joinedload(StockItem.batch).joinedload(Batch.material))

        result_items = await db.execute(stmt_items)
        stock_items_raw = result_items.scalars().all()

        # Reorder: Active session items first, then rest by expiry
        items_with_session = []
        items_without_session = []
        for si in stock_items_raw:
            sess = await self.get_active_session(si.id, db)
            if sess:
                items_with_session.append(si)
            else:
                items_without_session.append(si)

        stock_items = items_with_session + items_without_session

        # S.1: Check for Active Session (Virtual Stock)
        has_active_session = False
        for si in stock_items:
            sess = await self.get_active_session(si.id, db)
            if sess:
                if patient_id and sess.patient_id and sess.patient_id != patient_id:
                    continue
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

            session = await self.get_active_session(si.id, db)
            mat_type = si.batch.material.type
            mat_name = si.batch.material.name
            logger.info(f"[CONSUME_DEBUG] Processing stock_item={si.id}, material={mat_name}, type={mat_type}, qty={si.quantity}, session={session is not None}")

            if not session:
                if mat_type == "DIVISIBLE" or mat_type == "REUSABLE":
                    if auto_open:
                        try:
                            session = await self.open_session(si.id, user_id, db=db, commit=False)
                            await db.refresh(si)
                        except ValueError as e:
                            raise e
                    else:
                        raise ValueError(
                            f"CONFIRM_OPEN_REQUIRED:{si.id}:{si.batch.material.name} - Batch {si.batch.batch_number}"
                        )

            if session and mat_type in ("DIVISIBLE", "REUSABLE"):
                mat_obj = si.batch.material
                if mat_obj and (mat_obj.type == "REUSABLE" or mat_obj.max_uses > 1):
                    session.current_uses += 1

                remaining_to_consume = 0
                logger.info(f"[CONSUME_DEBUG] Virtual consumption for {mat_name} (type={mat_type}) via session")
                continue

            # Standard Consumption
            consume_amount = min(si.quantity, remaining_to_consume)
            logger.info(f"[CONSUME_DEBUG] Standard consumption: consume_amount={consume_amount}, stock_qty={si.quantity}, remaining={remaining_to_consume}")

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
            logger.info(f"[CONSUME_DEBUG] Stock deducted: material={mat_name}, amount={consume_amount}, new_qty={si.quantity}")

            # 4. Close Check (Non-Divisible Auto Close)
            if mat_type == "NON_DIVISIBLE" and si.quantity <= 0:
                if session:
                    await db.flush()
                    stmt_sum_move = (
                        select(func.abs(func.sum(StockMovement.change_amount)))
                        .where(
                            StockMovement.stock_item_id == si.id,
                            StockMovement.change_amount < 0,
                        )
                    )
                    total_usage = await db.scalar(stmt_sum_move) or 0.0

                    from .inventory_learning_service import InventoryLearningService
                    ls = InventoryLearningService(db)
                    await ls.close_session(session.id, float(total_usage), user_id)

        if commit:
            await db.commit()
        return movements

    async def reverse_stock_by_reference(
        self,
        reference_id: str,
        user_id: int,
        db: AsyncSession = None,
    ) -> List[StockMovement]:
        """
        Reverse all stock movements for a given reference_id.
        """
        db = self._get_db(db)

        stmt_move = select(StockMovement).where(StockMovement.reference_id == reference_id)
        movements = (await db.execute(stmt_move)).scalars().all()

        if not movements:
            return []

        reversals = []
        reverse_ref = f"REVERSE:{reference_id}"

        # Prevent double reversal
        stmt_double = select(func.count(StockMovement.id)).where(StockMovement.reference_id == reverse_ref)
        already_reversed = await db.scalar(stmt_double) or 0
        if already_reversed > 0:
            return []

        for move in movements:
            reverse_move = StockMovement(
                stock_item_id=move.stock_item_id,
                change_amount=-move.change_amount,
                reason="REVERSAL",
                performed_by=user_id,
                reference_id=reverse_ref,
            )
            db.add(reverse_move)

            # Restore stock item quantity
            stmt_si = select(StockItem).where(StockItem.id == move.stock_item_id)
            stock_item = (await db.execute(stmt_si)).scalars().first()
            if stock_item:
                stock_item.quantity -= move.change_amount

            reversals.append(reverse_move)

        return reversals

    async def get_expiry_alerts(self, tenant_id: int, days: int = 30, db: AsyncSession = None):
        """
        Find batches expiring within 'days' (default 30).
        """
        db = self._get_db(db)
        target_date = datetime.now().date()
        limit_date = target_date + timedelta(days=days)

        # Find batches with qty > 0 and expiry < limit
        stmt = (
            select(Batch, Material, StockItem)
            .join(Material, Material.id == Batch.material_id)
            .join(StockItem, StockItem.batch_id == Batch.id)
            .where(
                Batch.tenant_id == tenant_id,
                StockItem.quantity > 0,
                Batch.expiry_date <= limit_date,
            )
            .order_by(Batch.expiry_date.asc())
        )
        result = await db.execute(stmt)
        results = result.all()

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

    async def delete_material(self, material_id: int, tenant_id: int, db: AsyncSession = None):
        """
        Delete material ensuring no dependencies block it.
        """
        db = self._get_db(db)

        stmt_mat = select(Material).where(Material.id == material_id, Material.tenant_id == tenant_id)
        mat = (await db.execute(stmt_mat)).scalars().first()
        if not mat:
            logger.warning(f"[DELETE_DEBUG] Material {material_id} not found for tenant {tenant_id}")
            raise ValueError("Material not found")

        logger.info(f"[DELETE_DEBUG] Attempting to delete material {material_id} ({mat.name}), type={mat.type}")

        # Check Active Stock
        stmt_stock = select(StockItem).join(Batch).where(
            Batch.material_id == material_id,
            StockItem.quantity > 0
        )
        stock_items = (await db.execute(stmt_stock)).scalars().all()
        has_stock = len(stock_items) > 0
        logger.info(f"[DELETE_DEBUG] Active stock check: {len(stock_items)} items with qty > 0")

        if has_stock:
            raise ValueError(f"Cannot delete material '{mat.name}' with active stock ({len(stock_items)} items). Please consume or adjust stock to zero first.")

        # Check History
        stmt_history = select(func.count(StockMovement.id)).join(StockItem).join(Batch).where(
            Batch.material_id == material_id, Batch.tenant_id == tenant_id
        )
        history_count = await db.scalar(stmt_history) or 0
        logger.info(f"[DELETE_DEBUG] History check: {history_count} movements found")

        if history_count > 0:
            raise ValueError(f"Cannot delete material '{mat.name}' with {history_count} historical movements (Audit trail protected).")

        try:
            from ..models.inventory import ProcedureMaterialWeight, MaterialLearningLog
            from sqlalchemy import delete

            # Delete weights and learning logs
            stmt_pw = delete(ProcedureMaterialWeight).where(ProcedureMaterialWeight.material_id == material_id)
            await db.execute(stmt_pw)
            stmt_ll = delete(MaterialLearningLog).where(MaterialLearningLog.material_id == material_id)
            await db.execute(stmt_ll)

            stmt_batches = select(Batch).where(Batch.material_id == material_id)
            batches = (await db.execute(stmt_batches)).scalars().all()

            for b in batches:
                stmt_si = select(StockItem).where(StockItem.batch_id == b.id)
                stock_items_to_del = (await db.execute(stmt_si)).scalars().all()

                for si in stock_items_to_del:
                    stmt_sess_del = delete(MaterialSession).where(MaterialSession.stock_item_id == si.id)
                    await db.execute(stmt_sess_del)
                    stmt_move_del = delete(StockMovement).where(StockMovement.stock_item_id == si.id)
                    await db.execute(stmt_move_del)

                stmt_si_del = delete(StockItem).where(StockItem.batch_id == b.id)
                await db.execute(stmt_si_del)
                stmt_b_del = delete(Batch).where(Batch.id == b.id)
                await db.execute(stmt_b_del)

            # Finally Delete Material
            await db.delete(mat)
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise

    async def get_cogs_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: int,
        db: AsyncSession = None,
    ) -> float:
        """
        Calculate Cost of Goods Sold (COGS) for a period.
        """
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
        result = await db.execute(stmt)
        movements = result.all()

        total_cogs = 0.0

        for move, batch, mat in movements:
            qty = abs(move.change_amount)
            cost = batch.cost_per_unit
            if cost <= 0:
                cost = mat.standard_price or 0.0

            total_cogs += qty * cost

        return total_cogs

    async def transfer_stock(
        self,
        stock_item_id: int,
        target_warehouse_id: int,
        quantity: float,
        tenant_id: int,
        user_id: int,
        db: AsyncSession = None,
    ) -> StockMovement:
        """
        Transfer stock between warehouses (e.g., MAIN -> CLINIC).
        """
        db = self._get_db(db)

        # 1. Source Item
        stmt_src = select(StockItem).where(StockItem.id == stock_item_id)
        source_item = (await db.execute(stmt_src)).scalars().first()
        if not source_item:
            raise ValueError("Source stock item not found")

        if source_item.quantity < quantity:
            raise ValueError(
                f"Insufficient quantity. Available: {source_item.quantity}"
            )

        # 2. Target Item (Find or Create)
        stmt_target = (
            select(StockItem)
            .where(
                StockItem.warehouse_id == target_warehouse_id,
                StockItem.batch_id == source_item.batch_id,
                StockItem.tenant_id == tenant_id,
            )
        )
        target_item = (await db.execute(stmt_target)).scalars().first()

        if not target_item:
            target_item = StockItem(
                warehouse_id=target_warehouse_id,
                batch_id=source_item.batch_id,
                tenant_id=tenant_id,
                quantity=0,
            )
            db.add(target_item)
            await db.flush()

        # 3. Validation: Non-Divisible Check
        stmt_mat = select(Material).where(Material.id == source_item.batch.material_id)
        mat = (await db.execute(stmt_mat)).scalars().first()
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

        await db.commit()
        return move_in


inventory_service = InventoryService()
