from datetime import date, datetime, timezone

import pytest

from backend.utils.tenant_time import (
    DEFAULT_TENANT_TIMEZONE,
    tenant_day_local_naive_bounds,
    tenant_day_utc_bounds_naive,
    tenant_local_date,
    validate_timezone_name,
)


def test_cairo_business_date_rolls_at_local_midnight():
    assert tenant_local_date(
        "Africa/Cairo",
        now_utc=datetime(2026, 8, 16, 20, 59, tzinfo=timezone.utc),
    ) == date(2026, 8, 16)
    assert tenant_local_date(
        "Africa/Cairo",
        now_utc=datetime(2026, 8, 16, 21, 0, tzinfo=timezone.utc),
    ) == date(2026, 8, 17)


def test_cairo_utc_bounds_are_half_open_business_day():
    start, end = tenant_day_utc_bounds_naive(
        "Africa/Cairo",
        local_date=date(2026, 8, 17),
    )
    assert start == datetime(2026, 8, 16, 21, 0)
    assert end == datetime(2026, 8, 17, 21, 0)


def test_local_naive_bounds_preserve_appointment_wall_time():
    start, end = tenant_day_local_naive_bounds(
        "Asia/Riyadh",
        local_date=date(2026, 8, 17),
    )
    assert start == datetime(2026, 8, 17, 0, 0)
    assert end == datetime(2026, 8, 18, 0, 0)


def test_dst_spring_day_can_be_23_hours():
    start, end = tenant_day_utc_bounds_naive(
        "Europe/London",
        local_date=date(2026, 3, 29),
    )
    assert (end - start).total_seconds() == 23 * 60 * 60


def test_dst_autumn_day_can_be_25_hours():
    start, end = tenant_day_utc_bounds_naive(
        "Europe/London",
        local_date=date(2026, 10, 25),
    )
    assert (end - start).total_seconds() == 25 * 60 * 60


def test_multiple_iana_zones_validate():
    for zone in ("Africa/Cairo", "Asia/Riyadh", "Asia/Dubai", "Europe/London"):
        assert validate_timezone_name(zone) == zone


def test_invalid_timezone_is_rejected_on_write():
    with pytest.raises(ValueError):
        validate_timezone_name("Not/AZone")


def test_missing_runtime_timezone_falls_back_to_default():
    expected = tenant_local_date(
        DEFAULT_TENANT_TIMEZONE,
        now_utc=datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc),
    )
    assert tenant_local_date(
        None,
        now_utc=datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc),
    ) == expected


def test_dashboard_cache_identity_changes_with_business_date():
    from backend.services.cache_service import _build_cache_key

    day_one = _build_cache_key(
        "dashboard_stats",
        (1, None, None, False, "Africa/Cairo", "2026-08-17"),
        {},
    )
    day_two = _build_cache_key(
        "dashboard_stats",
        (1, None, None, False, "Africa/Cairo", "2026-08-18"),
        {},
    )
    assert day_one != day_two
