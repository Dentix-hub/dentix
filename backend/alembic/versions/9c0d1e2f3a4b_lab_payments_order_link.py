"""lab payments order link

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-10-25

Lab debt vs paid: Link lab payments to lab orders (Slice L1)
- Add nullable lab_order_id to lab_payments with FK to lab_orders.id (ondelete=SET NULL)
- Add single column index ix_lab_payments_lab_order_id
- Add composite index ix_lab_payments_tenant_order (tenant_id, lab_order_id)
- Applies R03: Composite indices and PostgreSQL parent-tenant trigger (nullable-parent mode)
- Reversible and does not touch existing rows
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c0d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "8b9c0d1e2f3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "lab_payments" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("lab_payments")}

    with op.batch_alter_table("lab_payments") as batch_op:
        if "lab_order_id" not in columns:
            batch_op.add_column(
                sa.Column("lab_order_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_lab_payments_lab_order_id",
                "lab_orders",
                ["lab_order_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("lab_payments")}

    for idx_name, cols in [
        ("ix_lab_payments_lab_order_id", ["lab_order_id"]),
        ("ix_lab_payments_tenant_order", ["tenant_id", "lab_order_id"]),
    ]:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "lab_payments", cols, unique=False)

    if bind.dialect.name == "postgresql":
        table = "lab_payments"
        trigger_name = "trg_lab_payments_lab_order_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{trigger_name}"
                BEFORE INSERT OR UPDATE OF tenant_id, "lab_order_id" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    'lab_orders', 'lab_order_id', 'true'
                )'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "lab_payments" not in existing_tables:
        return

    table = "lab_payments"
    if bind.dialect.name == "postgresql":
        op.execute(f'DROP TRIGGER IF EXISTS "trg_lab_payments_lab_order_id_parent_tenant" ON "{table}"')

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("lab_payments")}
    for idx_name in [
        "ix_lab_payments_tenant_order",
        "ix_lab_payments_lab_order_id",
    ]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name="lab_payments")

    with op.batch_alter_table("lab_payments") as batch_op:
        batch_op.drop_constraint("fk_lab_payments_lab_order_id", type_="foreignkey")
        batch_op.drop_column("lab_order_id")
