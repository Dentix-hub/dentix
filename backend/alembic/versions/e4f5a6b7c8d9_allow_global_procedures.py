"""allow_global_procedures

Revision ID: e4f5a6b7c8d9
Revises: 0c0c38745bc3
Create Date: 2026-08-16 23:40:00.000000

The Procedure model and the partial unique indexes introduced in
0c0c38745bc3 explicitly support a global catalog using tenant_id IS NULL.
Some deployed databases still retain a NOT NULL constraint on
procedures.tenant_id, which prevents that model from working.

This migration only relaxes the constraint. It deliberately does not rewrite
existing tenant-owned procedures into global rows; data ownership changes must
never be inferred from a tenant id during schema migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "0c0c38745bc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "procedures",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # A downgrade is only safe when no global procedures exist. Fail explicitly
    # instead of silently corrupting ownership semantics.
    conn = op.get_bind()
    global_count = conn.execute(
        sa.text("SELECT COUNT(*) FROM procedures WHERE tenant_id IS NULL")
    ).scalar_one()
    if global_count:
        raise RuntimeError(
            "Cannot restore NOT NULL on procedures.tenant_id while global "
            f"procedures exist ({global_count} rows)."
        )

    op.alter_column(
        "procedures",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
