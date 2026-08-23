"""Fail CI when SQLAlchemy metadata has unapplied schema operations.

Alembic's ``check`` command ultimately calls ``UpgradeOps.as_diffs()``.
The RLS autogenerate plugin used by Dentix contributes custom operations that
are valid for revision rendering but do not implement ``to_diff_tuple()``, so
``alembic check`` raises ``NotImplementedError`` before it can report whether
there is drift.

This checker uses the same Alembic autogenerate comparison and Dentix model/RLS
metadata, but evaluates the generated ``UpgradeOps`` container directly.
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
    print("Pending model/migration operations detected:", file=sys.stderr)
    for operation in pending:
        print(f"- {operation.__class__.__name__}: {operation!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
