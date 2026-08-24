"""repair legacy attachments schema

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-24

Older Dentix databases were created before ``attachments.note`` was part of
the SQLAlchemy model. The historical production ad-hoc schema helper added
``filename`` and ``file_type`` but never added ``note``. Fresh databases do
not reproduce the defect because the current model baseline already contains
the column.

This forward migration reconciles the legacy production/staging schema without
rewriting historical revisions or existing attachment data.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "attachments" not in tables:
        raise RuntimeError(
            "attachments table is required before repairing the legacy schema"
        )

    columns = {column["name"] for column in inspector.get_columns("attachments")}
    if "note" not in columns:
        op.add_column(
            "attachments",
            sa.Column("note", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "attachments" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("attachments")}
    if "note" in columns:
        op.drop_column("attachments", "note")
