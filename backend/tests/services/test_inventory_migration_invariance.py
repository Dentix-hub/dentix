"""
Tests for Phase G13 / Slice S31: Inventory Migration Invariance.

Covers:
- G13-M10: every pre-existing ``treatment_material_usages`` row (``treatment_id`` populated,
  ``care_session_id`` NULL) keeps byte-identical ``quantity_used`` / ``cost_calculated`` /
  ``weight_score`` / ``session_id`` / ``is_manual_override`` across the S26 Alembic
  upgrade and downgrade, and the new link columns default to NULL for those rows.
"""

import os
import tempfile
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PARENT_REVISION = "1a2b3c4d5e6f"
S26_REVISION = "2b3c4d5e6f7a"

# (id, treatment_id, material_id, session_id, weight_score, quantity_used, cost_calculated, override)
LEGACY_ROWS = [
    (1, 10, 100, None, 1.0, 3.0, "7.500000", 0),
    (2, 10, 101, 55, 2.5, None, None, 0),
    (3, 11, 100, None, 0.5, 0.125, "0.312500", 1),
    (4, 12, 102, 56, 1.0, 12.75, "1234.567891", 0),
]

SNAPSHOT_COLUMNS = (
    "id, treatment_id, material_id, session_id, weight_score, "
    "quantity_used, cost_calculated, is_manual_override, tenant_id"
)


def _snapshot(conn):
    rows = conn.execute(
        sa.text(f"SELECT {SNAPSHOT_COLUMNS} FROM treatment_material_usages ORDER BY id")
    ).fetchall()
    return [
        tuple(Decimal(str(v)) if i == 6 and v is not None else v for i, v in enumerate(r))
        for r in rows
    ]


def test_g13_m10_legacy_usage_rows_are_invariant_across_s26_migration(monkeypatch, legacy_clinical_schema):
    """Legacy usages keep identical quantity/cost through upgrade, downgrade and re-upgrade."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        engine = sa.create_engine(sqlite_url)
        alembic_cfg_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
        )
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        with engine.connect() as conn:
            legacy_clinical_schema(conn)
            # Head also migrates users.email; keep the legacy prerequisite schema realistic.
            conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"))
            conn.execute(sa.text("CREATE UNIQUE INDEX ix_users_email ON users(email)"))
            conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY, name VARCHAR, google_refresh_token VARCHAR)"))
            conn.execute(sa.text("CREATE TABLE attachments (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE treatments (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE materials (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE material_sessions (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE clinical_work_items (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(
                sa.text(
                    """CREATE TABLE treatment_material_usages (
                        id INTEGER PRIMARY KEY,
                        treatment_id INTEGER NOT NULL,
                        material_id INTEGER NOT NULL,
                        session_id INTEGER,
                        weight_score FLOAT DEFAULT 1.0,
                        quantity_used FLOAT,
                        cost_calculated NUMERIC(18, 6),
                        is_manual_override BOOLEAN DEFAULT 0,
                        tenant_id INTEGER NOT NULL,
                        created_at TIMESTAMP
                    )"""
                )
            )
            for (rid, tid, mid, sid, ws, qty, cost, ovr) in LEGACY_ROWS:
                conn.execute(
                    sa.text(
                        "INSERT INTO treatment_material_usages "
                        "(id, treatment_id, material_id, session_id, weight_score, "
                        "quantity_used, cost_calculated, is_manual_override, tenant_id) "
                        "VALUES (:id, :tid, :mid, :sid, :ws, :qty, :cost, :ovr, 1)"
                    ),
                    {
                        "id": rid, "tid": tid, "mid": mid, "sid": sid,
                        "ws": ws, "qty": qty, "cost": cost, "ovr": ovr,
                    },
                )
            conn.commit()

        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE user_sessions (id INTEGER PRIMARY KEY, user_id INTEGER, token_hash VARCHAR, ip_address VARCHAR, user_agent VARCHAR, device_info VARCHAR, last_active_at DATETIME, expires_at DATETIME, is_active BOOLEAN, created_at DATETIME)"))
            conn.execute(sa.text("INSERT INTO user_sessions (id, user_id, token_hash, is_active) VALUES (1, 1, 'old-session', 1)"))

        command.stamp(config, PARENT_REVISION)

        with engine.connect() as conn:
            before = _snapshot(conn)
        assert len(before) == len(LEGACY_ROWS)

        command.upgrade(config, S26_REVISION)

        with engine.connect() as conn:
            after_upgrade = _snapshot(conn)
            assert after_upgrade == before, "S26 upgrade must not alter legacy usage values"
            link_cols = conn.execute(
                sa.text(
                    "SELECT care_session_id, work_item_id FROM treatment_material_usages ORDER BY id"
                )
            ).fetchall()
            assert all(r[0] is None and r[1] is None for r in link_cols), (
                "legacy rows must keep care_session_id/work_item_id NULL"
            )

        command.downgrade(config, PARENT_REVISION)

        with engine.connect() as conn:
            assert _snapshot(conn) == before, "S26 downgrade must not alter legacy usage values"

        command.upgrade(config, "head")

        with engine.connect() as conn:
            assert _snapshot(conn) == before, "re-upgrade to head must not alter legacy usage values"
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
