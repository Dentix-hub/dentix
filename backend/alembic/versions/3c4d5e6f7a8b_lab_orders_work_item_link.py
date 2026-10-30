"""lab orders work item link

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-10-20

Phase G12 / Slice S27: Lab Order work_item_id FK, Legacy Link Backfill & Optional Data
- G12-M01: Add real FK from lab order to work item (lab_orders.work_item_id -> clinical_work_items.id)
- G12-M02: Add exact legacy migration support
- G12-M03: Stop using note-string linkage for new data
- G12-M07: Allow missing optional lab data (shade, material, tooth_number nullable)
- G4-M08: Backfill exact lab relationships
- Applies R03: Composite indices and PostgreSQL parent-tenant trigger
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f7a"
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
        if "work_item_id" not in columns:
            batch_op.add_column(
                sa.Column("work_item_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_lab_orders_work_item_id",
                "clinical_work_items",
                ["work_item_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # Re-inspect to get current indexes
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("lab_orders")}

    for idx_name, cols in [
        ("ix_lab_orders_work_item_id", ["work_item_id"]),
        ("ix_lab_orders_tenant_work_item", ["tenant_id", "work_item_id"]),
    ]:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "lab_orders", cols, unique=False)

    if bind.dialect.name == "postgresql":
        table = "lab_orders"
        wi_trigger = "trg_lab_orders_work_item_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{wi_trigger}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{wi_trigger}"
                BEFORE INSERT OR UPDATE OF tenant_id, "work_item_id" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    'clinical_work_items', 'work_item_id', 'true'
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
        op.execute(f'DROP TRIGGER IF EXISTS "trg_lab_orders_work_item_id_parent_tenant" ON "{table}"')

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("lab_orders")}
    for idx_name in [
        "ix_lab_orders_tenant_work_item",
        "ix_lab_orders_work_item_id",
    ]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name="lab_orders")

    with op.batch_alter_table("lab_orders") as batch_op:
        batch_op.drop_constraint("fk_lab_orders_work_item_id", type_="foreignkey")
        batch_op.drop_column("work_item_id")
