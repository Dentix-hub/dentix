# backend/services/subscription_calendar.py
"""
Calendar month recurrence and billing day anchor calculations for PR-06.

Enforces canonical calendar-month progression with preserved billing-day anchor:
e.g. Jan 31 -> Feb 28 (or Feb 29 in leap year) -> Mar 31 -> Apr 30 -> May 31.
Preserves anchor day across renewals to avoid date drift.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Africa/Cairo"


def _as_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def add_calendar_months(
    dt: datetime,
    months: int = 1,
    anchor_day: Optional[int] = None,
    tz_name: str = DEFAULT_TIMEZONE,
) -> Tuple[datetime, int]:
    """
    Advance datetime by N calendar months while preserving the billing day anchor.

    Args:
        dt: Base datetime (UTC or naive assumed UTC).
        months: Number of months to advance (typically 1).
        anchor_day: Preserved billing day anchor (1-31). If None, inferred from dt in clinic timezone.
        tz_name: Clinic timezone name (e.g. 'Africa/Cairo').

    Returns:
        Tuple of (new_datetime_utc_naive, preserved_anchor_day).
    """
    utc_dt = _as_utc(dt)
    try:
        clinic_tz = ZoneInfo(tz_name)
    except Exception:
        clinic_tz = ZoneInfo(DEFAULT_TIMEZONE)

    local_dt = utc_dt.astimezone(clinic_tz)
    anchor = anchor_day if (anchor_day is not None and 1 <= anchor_day <= 31) else local_dt.day

    total_months = (local_dt.year * 12 + local_dt.month - 1) + months
    target_year = total_months // 12
    target_month = (total_months % 12) + 1

    max_days_in_month = calendar.monthrange(target_year, target_month)[1]
    target_day = min(anchor, max_days_in_month)

    target_local = local_dt.replace(
        year=target_year,
        month=target_month,
        day=target_day,
    )

    target_utc = target_local.astimezone(timezone.utc).replace(tzinfo=None)
    return target_utc, anchor


def calculate_subscription_period(
    start_dt: datetime,
    duration_months: int = 1,
    anchor_day: Optional[int] = None,
    tz_name: str = DEFAULT_TIMEZONE,
) -> Tuple[datetime, datetime, int]:
    """
    Calculate start-inclusive, end-exclusive subscription period boundaries.

    Returns:
        (period_start_utc, period_end_utc, preserved_anchor_day)
    """
    utc_start = _as_utc(start_dt).replace(tzinfo=None)
    utc_end, anchor = add_calendar_months(
        utc_start,
        months=duration_months,
        anchor_day=anchor_day,
        tz_name=tz_name,
    )
    return utc_start, utc_end, anchor


def calculate_grace_period(end_dt: datetime, grace_days: int = 7) -> datetime:
    """Return grace period end timestamp (7 calendar days after paid end)."""
    return end_dt + timedelta(days=grace_days)
