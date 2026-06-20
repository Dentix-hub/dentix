from sqlalchemy import or_, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas


async def get_procedures(db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100):
    stmt = (
        select(models.Procedure)
        .where(
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id.is_(None),
            )
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_procedure(db: AsyncSession, procedure: schemas.ProcedureCreate, tenant_id: int):
    # REGRESSION (2026-06-19): procedures.name is globally unique (models/clinical.py),
    # so a duplicate-name insert raised IntegrityError, leaving the async session in a
    # failed-transaction state with the connection checked out. Under client retry this
    # cascaded into QueuePool exhaustion (pool_size=3, max_overflow=2 on Supabase pooler).
    # Catch IntegrityError explicitly, rollback, and raise a ValueError the router maps
    # to a clean 409 — keeping the session/connection healthy for the next request.
    db_procedure = models.Procedure(**procedure.model_dump(), tenant_id=tenant_id)
    db.add(db_procedure)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # procedures.name is the only unique column on this table (ix_procedures_name);
        # any IntegrityError here is effectively a duplicate-name collision.
        orig = getattr(getattr(e, "orig", None), "__class__", None)
        msg = getattr(orig, "__name__", "") or str(e.orig or e)
        if "name" in str(e.orig or "").lower() or "procedures_name" in str(e.orig or "").lower():
            raise ValueError(f"A procedure named '{procedure.name}' already exists.") from e
        raise ValueError(f"Procedure could not be created (constraint violation: {msg}).") from e
    await db.refresh(db_procedure)
    return db_procedure


async def update_procedure(
    db: AsyncSession, procedure_id: int, procedure: schemas.ProcedureCreate, tenant_id: int
):
    stmt = (
        select(models.Procedure)
        .where(
            models.Procedure.id == procedure_id,
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id.is_(None),
            ),
        )
    )
    result = await db.execute(stmt)
    db_procedure = result.scalars().first()
    if db_procedure:
        # If updating a global procedure, we might want to "fork" it (Copy on Write)
        # But for now, let's allow direct modification as per user request to "fix" the list.
        for key, value in procedure.model_dump().items():
            setattr(db_procedure, key, value)
        await db.commit()
        await db.refresh(db_procedure)
    return db_procedure


async def delete_procedure(db: AsyncSession, procedure_id: int, tenant_id: int):
    stmt = (
        select(models.Procedure)
        .where(
            models.Procedure.id == procedure_id,
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id.is_(None),
            ),
        )
    )
    result = await db.execute(stmt)
    db_procedure = result.scalars().first()
    if db_procedure:
        # Cascade Delete Step 1: Remove from all price lists
        await db.execute(
            delete(models.PriceListItem).where(
                models.PriceListItem.procedure_id == procedure_id
            )
        )

        # Cascade Delete Step 2: Remove from inventory weights (Smart Inventory)
        await db.execute(
            delete(models.ProcedureMaterialWeight).where(
                models.ProcedureMaterialWeight.procedure_id == procedure_id
            )
        )

        await db.delete(db_procedure)
        await db.commit()
    return db_procedure
