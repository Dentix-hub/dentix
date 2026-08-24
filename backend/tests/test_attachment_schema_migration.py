import importlib.util
from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "c9d0e1f2a3b4_repair_legacy_attachments_schema.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "legacy_attachment_schema_migration", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Bind:
    pass


class _Inspector:
    def __init__(self, columns, *, has_table=True):
        self._columns = columns
        self._has_table = has_table

    def get_table_names(self):
        return ["attachments"] if self._has_table else []

    def get_columns(self, table):
        assert table == "attachments"
        return [{"name": name} for name in self._columns]


def test_upgrade_adds_note_to_legacy_attachment_table(monkeypatch):
    migration = _load_migration()
    bind = _Bind()
    inspector = _Inspector(
        {"id", "patient_id", "file_path", "filename", "file_type", "created_at"}
    )
    added = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.sa, "inspect", lambda received: inspector)
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: added.append((table, column)),
    )

    migration.upgrade()

    assert len(added) == 1
    table, column = added[0]
    assert table == "attachments"
    assert column.name == "note"
    assert column.nullable is True


def test_upgrade_is_idempotent_when_note_already_exists(monkeypatch):
    migration = _load_migration()
    bind = _Bind()
    inspector = _Inspector(
        {
            "id",
            "patient_id",
            "file_path",
            "filename",
            "file_type",
            "note",
            "created_at",
        }
    )
    added = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.sa, "inspect", lambda received: inspector)
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: added.append((table, column)),
    )

    migration.upgrade()

    assert added == []


def test_upgrade_refuses_unknown_schema_without_attachments(monkeypatch):
    migration = _load_migration()
    bind = _Bind()
    inspector = _Inspector(set(), has_table=False)

    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.sa, "inspect", lambda received: inspector)

    with pytest.raises(RuntimeError, match="attachments table is required"):
        migration.upgrade()
