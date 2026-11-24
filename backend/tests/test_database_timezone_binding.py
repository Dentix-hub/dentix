"""Regression tests for PostgreSQL timezone-aware vs naive bind normalization (QA-24)."""

import datetime
from types import SimpleNamespace

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

from backend.database import _normalize_parameters_for_context


def _compiled_statement(stmt, dialect):
    return stmt.compile(dialect=dialect)


def test_postgres_preserves_aware_utc_for_timestamptz_and_strips_for_naive():
    metadata = sa.MetaData()
    table = sa.Table(
        "tz_probe",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts_naive", sa.DateTime(timezone=False)),
        sa.Column("ts_aware", sa.DateTime(timezone=True)),
    )
    cairo_tz = datetime.timezone(datetime.timedelta(hours=2))
    cairo_dt = datetime.datetime(2026, 11, 23, 14, 30, tzinfo=cairo_tz)
    naive_utc_dt = datetime.datetime(2026, 11, 23, 12, 30)

    insert_stmt = table.insert().values(ts_naive=cairo_dt, ts_aware=cairo_dt)

    # 1. asyncpg positional tuple parameters
    compiled_asyncpg = _compiled_statement(insert_stmt, postgresql.asyncpg.dialect())
    conn_pg = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    ctx_asyncpg = SimpleNamespace(compiled=compiled_asyncpg)

    row_tuple = tuple(cairo_dt if name in ("ts_naive", "ts_aware") else None for name in compiled_asyncpg.positiontup)
    out_tuple = _normalize_parameters_for_context(conn_pg, row_tuple, ctx_asyncpg, executemany=False)
    by_name = dict(zip(compiled_asyncpg.positiontup, out_tuple))

    assert by_name["ts_naive"] == datetime.datetime(2026, 11, 23, 12, 30)
    assert by_name["ts_naive"].tzinfo is None
    assert by_name["ts_aware"] == datetime.datetime(2026, 11, 23, 12, 30, tzinfo=datetime.timezone.utc)
    assert by_name["ts_aware"].tzinfo == datetime.timezone.utc

    # 2. Naive UTC passed to DateTime(timezone=True) gets UTC tzinfo attached so asyncpg won't apply OS TZ
    row_naive = tuple(naive_utc_dt for _ in compiled_asyncpg.positiontup)
    out_naive = _normalize_parameters_for_context(conn_pg, row_naive, ctx_asyncpg, executemany=False)
    by_name_naive = dict(zip(compiled_asyncpg.positiontup, out_naive))
    assert by_name_naive["ts_naive"].tzinfo is None
    assert by_name_naive["ts_aware"] == datetime.datetime(2026, 11, 23, 12, 30, tzinfo=datetime.timezone.utc)

    # 3. psycopg2 named dict parameters and executemany
    compiled_psycopg = _compiled_statement(insert_stmt, postgresql.psycopg2.dialect())
    ctx_psycopg = SimpleNamespace(compiled=compiled_psycopg)
    param_dict = {"ts_naive": cairo_dt, "ts_aware": cairo_dt}
    out_many = _normalize_parameters_for_context(conn_pg, [param_dict], ctx_psycopg, executemany=True)
    assert out_many[0]["ts_naive"] == datetime.datetime(2026, 11, 23, 12, 30)
    assert out_many[0]["ts_naive"].tzinfo is None
    assert out_many[0]["ts_aware"] == datetime.datetime(2026, 11, 23, 12, 30, tzinfo=datetime.timezone.utc)

    # 4. SQLite still receives naive UTC for both column definitions
    compiled_sqlite = _compiled_statement(insert_stmt, sqlite.dialect())
    conn_sqlite = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    ctx_sqlite = SimpleNamespace(compiled=compiled_sqlite)
    out_sqlite = _normalize_parameters_for_context(conn_sqlite, param_dict, ctx_sqlite, executemany=False)
    assert out_sqlite["ts_naive"] == datetime.datetime(2026, 11, 23, 12, 30)
    assert out_sqlite["ts_naive"].tzinfo is None
    assert out_sqlite["ts_aware"] == datetime.datetime(2026, 11, 23, 12, 30)
    assert out_sqlite["ts_aware"].tzinfo is None
