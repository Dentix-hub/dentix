from datetime import datetime, timedelta, timezone

from backend.database import _normalize_db_bind_value


def test_normalizes_nested_executemany_datetimes_to_utc_naive():
    cairo_like = timezone(timedelta(hours=3))
    aware = datetime(2026, 8, 19, 8, 30, tzinfo=cairo_like)
    untouched = datetime(2026, 8, 19, 5, 45)

    params = [
        (1, aware, "first"),
        (2, untouched, "second"),
    ]

    normalized = _normalize_db_bind_value(params)

    assert normalized == [
        (1, datetime(2026, 8, 19, 5, 30), "first"),
        (2, untouched, "second"),
    ]
    assert normalized[0][1].tzinfo is None


def test_normalizes_mapping_parameters_without_mutating_source():
    aware = datetime(2026, 8, 19, 5, 0, tzinfo=timezone.utc)
    params = {"created_at": aware, "amount": 10.0}

    normalized = _normalize_db_bind_value(params)

    assert normalized["created_at"] == datetime(2026, 8, 19, 5, 0)
    assert normalized["created_at"].tzinfo is None
    assert params["created_at"].tzinfo is timezone.utc
