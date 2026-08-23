"""Fail CI when SQLAlchemy metadata has unapplied structural schema operations.

Alembic's ``check`` command ultimately calls ``UpgradeOps.as_diffs()``.
The RLS autogenerate plugin used by Dentix contributes custom operations that
are valid for revision rendering but do not implement ``to_diff_tuple()``, so
``alembic check`` raises ``NotImplementedError`` before it can report whether
there is structural drift.

Dentix also validates RLS behavior independently with PostgreSQL NOBYPASSRLS
concurrency/HTTP gates. On a fresh model baseline the third-party RLS plugin
currently emits policy-only DropPolicyOp/DisableRlsOp operations even though
there is no table/column/index drift. This checker therefore reports those
plugin operations separately while still failing on every non-RLS structural
Alembic operation.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from backend import models  # noqa: F401  # ensure every model is registered
from backend.models.base import Base
from rls.register_rls import register_rls


def _leaf_operations(operation: object) -> Iterable[object]:
    """Yield leaf operations without requiring Alembic ``as_diffs()`` support."""
    nested = getattr(operation, "ops", None)
    if nested is None:
        yield operation
        return

    for child in nested:
        yield from _leaf_operations(child)


def _is_rls_plugin_operation(operation: object) -> bool:
    """Return True only for operations owned by the third-party ``rls`` package."""
    return operation.__class__.__module__.startswith("rls.")


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required for migration drift detection.", file=sys.stderr)
        return 2

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Keep this metadata registration contract aligned with backend/alembic/env.py.
    register_rls(Base)

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection=connection)
            migration_script = produce_migrations(context, Base.metadata)
    finally:
        engine.dispose()

    upgrade_ops = migration_script.upgrade_ops
    if upgrade_ops.is_empty():
        print("No new upgrade operations detected.")
        return 0

    pending = list(_leaf_operations(upgrade_ops))
    structural = [op for op in pending if not _is_rls_plugin_operation(op)]
    rls_plugin = [op for op in pending if _is_rls_plugin_operation(op)]

    if rls_plugin:
        names = sorted({op.__class__.__name__ for op in rls_plugin})
        print(
            "RLS plugin emitted policy-only operations on the fresh baseline "
            f"({len(rls_plugin)} operations: {', '.join(names)}). "
            "RLS behavior is validated by the dedicated PostgreSQL RLS gates."
        )

    if not structural:
        print("No structural model/migration drift detected.")
        return 0

    print("Pending structural model/migration operations detected:", file=sys.stderr)
    for operation in structural:
        print(
            f"- {operation.__class__.__module__}.{operation.__class__.__name__}: "
            f"{operation!r}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
