from sqlalchemy import or_, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas


async def get_procedures(db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100):
    """Return tenant procedures plus read-only global templates."""
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
    db_procedure = models.Procedure(**procedure.model_dump(), tenant_id=tenant_id)
    db.add(db_procedure)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
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
    """Update only a procedure owned by this tenant.

    Global templates (tenant_id=NULL) are intentionally readable but immutable from
    clinic-scoped administration. Platform/global template management belongs to a
    platform boundary, not this tenant CRUD path.
    """
    stmt = select(models.Procedure).where(
        models.Procedure.id == procedure_id,
        models.Procedure.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    db_procedure = result.scalars().first()
    if db_procedure:
        for key, value in procedure.model_dump().items():
            setattr(db_procedure, key, value)
        await db.commit()
        await db.refresh(db_procedure)
    return db_procedure


async def delete_procedure(db: AsyncSession, procedure_id: int, tenant_id: int):
    """Delete one tenant-owned procedure and only this tenant's references."""
    stmt = select(models.Procedure).where(
        models.Procedure.id == procedure_id,
        models.Procedure.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    db_procedure = result.scalars().first()
    if not db_procedure:
        return None

    tenant_price_lists = select(models.PriceList.id).where(
        models.PriceList.tenant_id == tenant_id
    )
    await db.execute(
        delete(models.PriceListItem).where(
            models.PriceListItem.procedure_id == procedure_id,
            models.PriceListItem.price_list_id.in_(tenant_price_lists),
        )
    )

    await db.execute(
        delete(models.ProcedureMaterialWeight).where(
            models.ProcedureMaterialWeight.procedure_id == procedure_id,
            models.ProcedureMaterialWeight.tenant_id == tenant_id,
        )
    )

    await db.delete(db_procedure)
    await db.commit()
    return db_procedure
