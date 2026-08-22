import importlib.util
from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "f6a7b8c9d0e1_use_exact_numeric_money.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "financial_numeric_migration", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class _PostgresBind:
    class dialect:
        name = "postgresql"

    def __init__(self, violation_name=None):
        self.violation_name = violation_name
        self.statements = []

    def execute(self, statement, parameters=None):
        sql = str(statement)
        self.statements.append((sql, parameters))
        value = int(self.violation_name is not None and self.violation_name in sql)
        return _ScalarResult(value)


def test_numeric_migration_accepts_float_precision_drift(monkeypatch):
    migration = _load_migration()
    bind = _PostgresBind()
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    migration._preflight_existing_values()

    assert len(bind.statements) == len(migration.CHECK_CONSTRAINTS)
    assert all("WHERE NOT" in sql for sql, _ in bind.statements)
    assert all(parameters is None for _, parameters in bind.statements)


def test_numeric_migration_still_rejects_business_rule_violations(monkeypatch):
    migration = _load_migration()
    bind = _PostgresBind("amount > 0")
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="business-rule violations"):
        migration._preflight_existing_values()


def test_numeric_conversion_rounds_to_each_declared_scale(monkeypatch):
    migration = _load_migration()
    bind = _PostgresBind()
    altered = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration.op,
        "alter_column",
        lambda table, column, **kwargs: altered.append((table, column, kwargs)),
    )
    monkeypatch.setattr(migration.op, "create_check_constraint", lambda *args: None)

    migration.upgrade()

    expected = {
        (table, column): f'ROUND("{column}"::numeric, {scale})'
        for table, column, _, scale in migration.MONEY_COLUMNS
    }
    assert {
        (table, column): kwargs["postgresql_using"]
        for table, column, kwargs in altered
    } == expected
