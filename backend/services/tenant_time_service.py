"""Async tenant-time context resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.utils.tenant_time import (
    DEFAULT_TENANT_TIMEZONE,
    tenant_day_local_naive_bounds,
    tenant_day_utc_bounds_naive,
    tenant_local_date,
)


@dataclass(frozen=True)
class TenantTimeContext:
    timezone_name: str
    business_date: date
    utc_start: datetime
    utc_end: datetime
    local_start: datetime
    local_end: datetime


async def get_tenant_timezone(db: AsyncSession, tenant_id: int) -> str:
    """Fetch the tenant's persisted IANA timezone with a legacy-safe fallback."""
    stmt = select(models.Tenant.timezone).where(models.Tenant.id == tenant_id)
    value = (await db.execute(stmt)).scalar_one_or_none()
    return value or DEFAULT_TENANT_TIMEZONE


async def get_tenant_time_context(
    db: AsyncSession,
    tenant_id: int,
    *,
    now_utc: datetime | None = None,
) -> TenantTimeContext:
    """Resolve one reusable business-day context for a request path."""
    timezone_name = await get_tenant_timezone(db, tenant_id)
    business_date = tenant_local_date(timezone_name, now_utc=now_utc)
    utc_start, utc_end = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=business_date,
        now_utc=now_utc,
    )
    local_start, local_end = tenant_day_local_naive_bounds(
        timezone_name,
        local_date=business_date,
        now_utc=now_utc,
    )
    return TenantTimeContext(
        timezone_name=timezone_name,
        business_date=business_date,
        utc_start=utc_start,
        utc_end=utc_end,
        local_start=local_start,
        local_end=local_end,
    )
