from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models
from .dependencies import get_async_db
from backend.services.cache_service import cached
from backend.core.response import success_response

router = APIRouter()


# --- Public System Settings ---
@router.get("/settings/public")
@cached("public_settings", expire=300)  # Cache for 5 minutes
async def get_public_settings(db: AsyncSession = Depends(get_async_db)):
    """Fetch public system settings (e.g. Banner)."""
    stmt = (
        select(models.SystemSetting)
        .where(models.SystemSetting.is_public)
    )
    result = await db.execute(stmt)
    settings = result.scalars().all()

    return success_response(data={s.key: s.value for s in settings}, message="Public settings retrieved")
