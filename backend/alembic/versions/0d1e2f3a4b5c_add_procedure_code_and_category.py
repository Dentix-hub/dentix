"""add procedure code and category

Revision ID: 0d1e2f3a4b5c
Revises: 9c0d1e2f3a4b
Create Date: 2026-10-26

Default Procedure Catalog:
- Add nullable code and category columns to procedures table.
- Add partial unique index on (tenant_id, code) where code IS NOT NULL.
- Reversible and does not modify existing rows.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0d1e2f3a4b5c"
down_revision: Union[str, Sequence[str], None] = "9c0d1e2f3a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "procedures" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("procedures")}

    with op.batch_alter_table("procedures") as batch_op:
        if "code" not in columns:
            batch_op.add_column(
                sa.Column("code", sa.String(length=64), nullable=True)
            )
        if "category" not in columns:
            batch_op.add_column(
                sa.Column("category", sa.String(length=64), nullable=True)
            )

    indexes = {idx["name"] for idx in inspector.get_indexes("procedures")}
    if "uq_procedures_tenant_code" not in indexes:
        op.create_index(
            "uq_procedures_tenant_code",
            "procedures",
            ["tenant_id", "code"],
            unique=True,
            postgresql_where=sa.text("code IS NOT NULL"),
            sqlite_where=sa.text("code IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "procedures" not in existing_tables:
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("procedures")}
    if "uq_procedures_tenant_code" in indexes:
        op.drop_index("uq_procedures_tenant_code", table_name="procedures")

    columns = {c["name"] for c in inspector.get_columns("procedures")}
    with op.batch_alter_table("procedures") as batch_op:
        if "category" in columns:
            batch_op.drop_column("category")
        if "code" in columns:
            batch_op.drop_column("code")
