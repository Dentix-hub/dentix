from sqlalchemy import or_, select, delete
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
    db_procedure = models.Procedure(**procedure.dict(), tenant_id=tenant_id)
    db.add(db_procedure)
    await db.commit()
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
        for key, value in procedure.dict().items():
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
