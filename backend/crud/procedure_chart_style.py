"""
CRUD operations for ProcedureChartStyle.
"""

from typing import Optional, Sequence
from datetime import datetime, timezone
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas


async def get_procedure_chart_styles(
    db: AsyncSession, tenant_id: int
) -> Sequence[models.ProcedureChartStyle]:
    stmt = (
        select(models.ProcedureChartStyle)
        .where(models.ProcedureChartStyle.tenant_id == tenant_id)
        .order_by(models.ProcedureChartStyle.procedure_name.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_procedure_chart_style_by_id(
    db: AsyncSession, style_id: int, tenant_id: int
) -> Optional[models.ProcedureChartStyle]:
    stmt = select(models.ProcedureChartStyle).where(
        models.ProcedureChartStyle.id == style_id,
        models.ProcedureChartStyle.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def procedure_exists_for_tenant(
    db: AsyncSession, tenant_id: int, procedure_name: str
) -> bool:
    stmt = (
        select(models.Procedure.id)
        .where(
            models.Procedure.name == procedure_name,
            or_(
                models.Procedure.tenant_id == tenant_id,
                models.Procedure.tenant_id.is_(None),
            ),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def upsert_procedure_chart_style(
    db: AsyncSession, tenant_id: int, style_in: schemas.ProcedureChartStyleCreate
) -> models.ProcedureChartStyle:
    stmt = select(models.ProcedureChartStyle).where(
        models.ProcedureChartStyle.tenant_id == tenant_id,
        models.ProcedureChartStyle.procedure_name == style_in.procedure_name,
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing:
        existing.template = style_in.template
        existing.color_key = style_in.color_key
        existing.updated_at = now
        await db.commit()
        await db.refresh(existing)
        return existing

    new_style = models.ProcedureChartStyle(
        tenant_id=tenant_id,
        procedure_name=style_in.procedure_name,
        template=style_in.template,
        color_key=style_in.color_key,
        created_at=now,
        updated_at=now,
    )
    db.add(new_style)
    await db.commit()
    await db.refresh(new_style)
    return new_style


async def delete_procedure_chart_style(
    db: AsyncSession, style_id: int, tenant_id: int
) -> bool:
    stmt = select(models.ProcedureChartStyle).where(
        models.ProcedureChartStyle.id == style_id,
        models.ProcedureChartStyle.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    style = result.scalars().first()
    if not style:
        return False
    await db.delete(style)
    await db.commit()
    return True
