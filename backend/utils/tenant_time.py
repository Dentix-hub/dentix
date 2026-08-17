"""Tenant-local business-day helpers.

DENTIX currently stores most financial/clinical event timestamps as UTC by
convention in timezone-naive ``DateTime`` columns, while appointments are
stored as clinic-local wall-clock datetimes.  These helpers keep those two
semantics explicit and DST-safe.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TENANT_TIMEZONE = "Africa/Cairo"


def validate_timezone_name(timezone_name: str) -> str:
    """Validate and return an IANA timezone name.

    Write paths should use this strict validator. Runtime read paths may use
    :func:`resolve_timezone` to preserve legacy tenants if stored data is
    missing or invalid.
    """
    if not timezone_name or not timezone_name.strip():
        raise ValueError("Timezone is required")

    normalized = timezone_name.strip()
    try:
        ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Invalid IANA timezone: {normalized}") from exc
    return normalized


def resolve_timezone(timezone_name: str | None) -> ZoneInfo:
    """Resolve a stored timezone, falling back safely for legacy data."""
    candidate = (timezone_name or DEFAULT_TENANT_TIMEZONE).strip()
    try:
        return ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TENANT_TIMEZONE)


def _normalize_now_utc(now_utc: datetime | None) -> datetime:
    """Return an aware UTC datetime for deterministic calculations."""
    value = now_utc or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def tenant_local_date(
    timezone_name: str | None,
    *,
    now_utc: datetime | None = None,
) -> date:
    """Return the tenant's current calendar date."""
    tz = resolve_timezone(timezone_name)
    return _normalize_now_utc(now_utc).astimezone(tz).date()


def tenant_day_utc_bounds_naive(
    timezone_name: str | None,
    *,
    local_date: date | None = None,
    now_utc: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return ``[start, end)`` UTC bounds for one tenant-local day.

    The project currently persists the affected instant-like timestamps in
    timezone-naive ``DateTime`` columns. Therefore UTC boundaries are returned
    as naive UTC datetimes to match the existing database contract.

    The end boundary is built from *next local midnight* independently instead
    of ``start + timedelta(days=1)`` so DST 23/25-hour days remain correct.
    """
    tz = resolve_timezone(timezone_name)
    business_date = local_date or tenant_local_date(timezone_name, now_utc=now_utc)
    next_date = business_date + timedelta(days=1)

    local_start = datetime.combine(business_date, time.min, tzinfo=tz)
    local_end = datetime.combine(next_date, time.min, tzinfo=tz)

    utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return utc_start, utc_end


def tenant_day_local_naive_bounds(
    timezone_name: str | None,
    *,
    local_date: date | None = None,
    now_utc: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return local-naive ``[start, end)`` bounds for appointment wall time."""
    business_date = local_date or tenant_local_date(timezone_name, now_utc=now_utc)
    next_date = business_date + timedelta(days=1)
    return (
        datetime.combine(business_date, time.min),
        datetime.combine(next_date, time.min),
    )


def serialize_utc_datetime(value: datetime | None) -> str | None:
    """Serialize a UTC-by-convention datetime with an explicit UTC marker."""
    if value is None:
        return None
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return aware.isoformat().replace("+00:00", "Z")


def utc_now_naive() -> datetime:
    """Return the canonical UTC-naive timestamp used by legacy DateTime fields."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
