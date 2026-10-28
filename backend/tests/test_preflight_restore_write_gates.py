import pytest
from unittest.mock import MagicMock, call
from backend.scripts import preflight_migrations as preflight


def test_restore_write_gates_constants():
    assert len(preflight.RESTORE_WRITE_GATE_TABLES) >= 40
    assert "patients" in preflight.RESTORE_WRITE_GATE_TABLES
    assert "users" in preflight.RESTORE_WRITE_GATE_TABLES
    assert "appointments" in preflight.RESTORE_WRITE_GATE_TABLES
    assert preflight.RESTORE_GATE_NAMESPACE == 1146377304


def test_install_postgresql_restore_write_gates_skipped_on_non_postgres():
    conn = MagicMock()
    conn.dialect.name = "sqlite"
    preflight._install_postgresql_restore_write_gates(conn)
    conn.execute.assert_not_called()


def test_install_postgresql_restore_write_gates_installs_functions_and_triggers():
    conn = MagicMock()
    conn.dialect.name = "postgresql"
    # Mock existing tables in current_schema
    conn.execute.return_value.scalars.return_value = ["patients", "users", "price_list_items"]

    preflight._install_postgresql_restore_write_gates(conn)

    # Verify functions and triggers were created via execute
    executed_statements = [str(call_args[0][0]) for call_args in conn.execute.call_args_list]
    combined_sql = " ".join(executed_statements)

    assert "CREATE OR REPLACE FUNCTION dentix_clinic_write_gate()" in combined_sql
    assert "CREATE OR REPLACE FUNCTION dentix_price_item_write_gate()" in combined_sql
    assert 'CREATE TRIGGER clinic_write_gate BEFORE INSERT OR UPDATE OR DELETE ON "patients"' in combined_sql
    assert 'CREATE TRIGGER clinic_write_gate BEFORE INSERT OR UPDATE OR DELETE ON "users"' in combined_sql
    assert 'CREATE TRIGGER clinic_write_gate BEFORE INSERT OR UPDATE OR DELETE ON "price_list_items"' in combined_sql


def test_verify_postgresql_restore_write_gates_detects_missing():
    engine = MagicMock()
    engine.name = "postgresql"

    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn

    # 1. Neither function exists, table patients exists but no trigger
    conn.execute.side_effect = [
        MagicMock(scalars=lambda: []),  # procs
        MagicMock(scalars=lambda: ["patients", "price_list_items"]),  # existing tables
        MagicMock(scalars=lambda: []),  # triggers
    ]

    failures = preflight._verify_postgresql_restore_write_gates(engine)
    assert "function:dentix_clinic_write_gate:missing" in failures
    assert "function:dentix_price_item_write_gate:missing" in failures
    assert "trigger:patients:clinic_write_gate:missing" in failures
    assert "trigger:price_list_items:clinic_write_gate:missing" in failures


def test_verify_postgresql_restore_write_gates_passes_when_present():
    engine = MagicMock()
    engine.name = "postgresql"

    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn

    conn.execute.side_effect = [
        MagicMock(scalars=lambda: ["dentix_clinic_write_gate", "dentix_price_item_write_gate"]),  # procs
        MagicMock(scalars=lambda: ["patients", "price_list_items"]),  # existing tables
        MagicMock(scalars=lambda: ["patients", "price_list_items"]),  # triggers
    ]

    failures = preflight._verify_postgresql_restore_write_gates(engine)
    assert failures == []
