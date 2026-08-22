import importlib.util
from pathlib import Path

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

    violations = migration._existing_value_violations()

    assert violations == {}
    assert len(bind.statements) == len(migration.CHECK_CONSTRAINTS)
    assert all("WHERE NOT" in sql for sql, _ in bind.statements)
    assert all(parameters is None for _, parameters in bind.statements)


def test_numeric_migration_reports_business_rule_violations(monkeypatch, capsys):
    migration = _load_migration()
    bind = _PostgresBind("amount > 0")
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    violations = migration._existing_value_violations()
    migration._report_staged_constraints(violations)

    assert violations == {
        "ck_payments_amount_positive": 1,
        "ck_lab_payments_amount_positive": 1,
        "ck_subscription_payments_amount_positive": 1,
    }
    assert (
        "Historical business-rule violations were preserved"
        in capsys.readouterr().err
    )


def test_numeric_conversion_rounds_to_each_declared_scale(monkeypatch):
    migration = _load_migration()
    bind = _PostgresBind()
    altered = []
    constraints = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration.op,
        "alter_column",
        lambda table, column, **kwargs: altered.append((table, column, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "create_check_constraint",
        lambda *args, **kwargs: constraints.append((args, kwargs)),
    )

    migration.upgrade()

    expected = {
        (table, column): f'ROUND("{column}"::numeric, {scale})'
        for table, column, _, scale in migration.MONEY_COLUMNS
    }
    assert {
        (table, column): kwargs["postgresql_using"]
        for table, column, kwargs in altered
    } == expected
    assert all(
        kwargs == {"postgresql_not_valid": True} for _, kwargs in constraints
    )


def test_numeric_migration_stages_all_postgres_constraints(monkeypatch):
    migration = _load_migration()
    bind = _PostgresBind("discount <= cost")
    constraints = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "alter_column", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        migration.op,
        "create_check_constraint",
        lambda *args, **kwargs: constraints.append((args, kwargs)),
    )

    migration.upgrade()

    options_by_name = {args[0]: kwargs for args, kwargs in constraints}
    assert options_by_name["ck_treatments_discount_not_above_cost"] == {
        "postgresql_not_valid": True
    }
    assert options_by_name["ck_treatments_cost_nonnegative"] == {
        "postgresql_not_valid": True
    }
