"""lab orders treatment link

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-10-25

Treatment edit sheet unification + lab link
- Add nullable treatment_id to lab_orders with FK to treatments.id
- Add composite tenant index and single-column index
- Applies R03: Composite indices and PostgreSQL parent-tenant trigger
- Reversible and does not touch existing rows
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f7a8b9c0d1e"
down_revision: Union[str, Sequence[str], None] = "5e6f7a8b9c0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "lab_orders" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("lab_orders")}

    with op.batch_alter_table("lab_orders") as batch_op:
        if "treatment_id" not in columns:
            batch_op.add_column(
                sa.Column("treatment_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_lab_orders_treatment_id",
                "treatments",
                ["treatment_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # Re-inspect to get current indexes
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("lab_orders")}

    for idx_name, cols in [
        ("ix_lab_orders_treatment_id", ["treatment_id"]),
        ("ix_lab_orders_tenant_treatment", ["tenant_id", "treatment_id"]),
    ]:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "lab_orders", cols, unique=False)

    if bind.dialect.name == "postgresql":
        table = "lab_orders"
        trigger_name = "trg_lab_orders_treatment_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{trigger_name}"
                BEFORE INSERT OR UPDATE OF tenant_id, "treatment_id" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    'treatments', 'treatment_id', 'true'
                )'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "lab_orders" not in existing_tables:
        return

    table = "lab_orders"
    if bind.dialect.name == "postgresql":
        op.execute(f'DROP TRIGGER IF EXISTS "trg_lab_orders_treatment_id_parent_tenant" ON "{table}"')

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("lab_orders")}
    for idx_name in [
        "ix_lab_orders_tenant_treatment",
        "ix_lab_orders_treatment_id",
    ]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name="lab_orders")

    with op.batch_alter_table("lab_orders") as batch_op:
        batch_op.drop_constraint("fk_lab_orders_treatment_id", type_="foreignkey")
        batch_op.drop_column("treatment_id")
