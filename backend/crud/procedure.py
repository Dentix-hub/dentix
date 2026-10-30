from sqlalchemy import or_, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas


async def get_procedures(db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100):
    """Return tenant procedures plus read-only global templates.

    If an existing tenant has no procedures yet, lazily seed the default
    procedure catalog so pre-existing clinics automatically receive the
    standard 34 procedures without manual intervention.
    """
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
    procs = result.scalars().all()

    if not procs and skip == 0 and limit > 0 and tenant_id is not None:
        try:
            tenant_exists = (
                await db.execute(
                    select(models.Tenant.id).where(models.Tenant.id == tenant_id)
                )
            ).scalar_one_or_none()
            if tenant_exists is not None:
                await seed_tenant_default_procedures(db, tenant_id)
                await db.commit()
                result = await db.execute(stmt)
                procs = result.scalars().all()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(stmt)
            procs = result.scalars().all()

    return procs


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


async def seed_tenant_default_procedures(db: AsyncSession, tenant_id: int) -> list[models.Procedure]:
    """Copy default procedure catalog and chart styles for a tenant.

    Each tenant receives its own catalog entries at price 0, along with
    initial chart styles, within the caller's transaction boundary.
    Idempotent against pre-existing procedures or chart styles.
    """
    from backend.data.default_procedures import DEFAULT_PROCEDURE_CATALOG

    existing_procs_res = await db.execute(
        select(models.Procedure.name, models.Procedure.code).where(
            models.Procedure.tenant_id == tenant_id
        )
    )
    existing_rows = existing_procs_res.all()
    existing_names = {r[0] for r in existing_rows if r[0]}
    existing_codes = {r[1] for r in existing_rows if r[1]}

    existing_styles_res = await db.execute(
        select(models.ProcedureChartStyle.procedure_name).where(
            models.ProcedureChartStyle.tenant_id == tenant_id
        )
    )
    existing_style_names = {r[0] for r in existing_styles_res.all() if r[0]}

    created_procedures = []
    for entry in DEFAULT_PROCEDURE_CATALOG:
        if entry.name not in existing_names and entry.code not in existing_codes:
            proc = models.Procedure(
                name=entry.name,
                code=entry.code,
                category=entry.category,
                price=entry.default_price,
                tenant_id=tenant_id,
            )
            db.add(proc)
            created_procedures.append(proc)
            existing_names.add(entry.name)
            existing_codes.add(entry.code)

        if (
            entry.chart_template
            and entry.chart_template != "NONE"
            and entry.name not in existing_style_names
        ):
            style = models.ProcedureChartStyle(
                tenant_id=tenant_id,
                procedure_name=entry.name,
                template=entry.chart_template,
                color_key=entry.color_key,
            )
            db.add(style)
            existing_style_names.add(entry.name)

    return created_procedures


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
