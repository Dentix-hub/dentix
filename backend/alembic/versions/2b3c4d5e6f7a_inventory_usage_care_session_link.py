"""inventory usage care session link

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-10-20

Phase G13 / Slice S26: Inventory Usage care_session_id Schema & History Preservation
- G13-M01: Distinguish material session from care session
- G13-M02: Add care_session_id and work_item_id to treatment_material_usages
- G13-M03: Preserve old usage data by making care_session_id nullable
- Applies PD07: Alter treatment_id to nullable=True and enforce
  CheckConstraint("treatment_id IS NOT NULL OR care_session_id IS NOT NULL")
- Applies R03: Composite indices and PostgreSQL parent-tenant triggers
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "treatment_material_usages" not in existing_tables:
        return

    columns = {c["name"] for c in inspector.get_columns("treatment_material_usages")}

    with op.batch_alter_table("treatment_material_usages") as batch_op:
        if "care_session_id" not in columns:
            batch_op.add_column(
                sa.Column("care_session_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_treatment_material_usages_care_session_id",
                "care_sessions",
                ["care_session_id"],
                ["id"],
                ondelete="SET NULL",
            )

        if "work_item_id" not in columns:
            batch_op.add_column(
                sa.Column("work_item_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_treatment_material_usages_work_item_id",
                "clinical_work_items",
                ["work_item_id"],
                ["id"],
                ondelete="SET NULL",
            )

        batch_op.alter_column(
            "treatment_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_check_constraint(
            "ck_tmu_treatment_or_care_session_required",
            "treatment_id IS NOT NULL OR care_session_id IS NOT NULL",
        )

    # Re-inspect to get current indexes
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("treatment_material_usages")}

    for idx_name, cols in [
        ("ix_treatment_material_usages_care_session_id", ["care_session_id"]),
        ("ix_treatment_material_usages_work_item_id", ["work_item_id"]),
        ("ix_tmu_tenant_care_session", ["tenant_id", "care_session_id"]),
        ("ix_tmu_tenant_work_item", ["tenant_id", "work_item_id"]),
    ]:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "treatment_material_usages", cols, unique=False)

    if bind.dialect.name == "postgresql":
        table = "treatment_material_usages"
        cs_trigger = "trg_treatment_material_usages_care_session_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{cs_trigger}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{cs_trigger}"
                BEFORE INSERT OR UPDATE OF tenant_id, "care_session_id" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    'care_sessions', 'care_session_id', 'true'
                )'''
        )

        wi_trigger = "trg_treatment_material_usages_work_item_id_parent_tenant"
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

    if "treatment_material_usages" not in existing_tables:
        return

    table = "treatment_material_usages"
    if bind.dialect.name == "postgresql":
        op.execute(f'DROP TRIGGER IF EXISTS "trg_treatment_material_usages_work_item_id_parent_tenant" ON "{table}"')
        op.execute(f'DROP TRIGGER IF EXISTS "trg_treatment_material_usages_care_session_id_parent_tenant" ON "{table}"')

    # Data sanitation: remove rows where treatment_id is NULL before restoring NOT NULL
    op.execute("DELETE FROM treatment_material_usages WHERE treatment_id IS NULL")

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("treatment_material_usages")}
    for idx_name in [
        "ix_tmu_tenant_work_item",
        "ix_tmu_tenant_care_session",
        "ix_treatment_material_usages_work_item_id",
        "ix_treatment_material_usages_care_session_id",
    ]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name="treatment_material_usages")

    with op.batch_alter_table("treatment_material_usages") as batch_op:
        batch_op.drop_constraint("ck_tmu_treatment_or_care_session_required", type_="check")
        batch_op.drop_constraint("fk_treatment_material_usages_work_item_id", type_="foreignkey")
        batch_op.drop_constraint("fk_treatment_material_usages_care_session_id", type_="foreignkey")
        batch_op.alter_column(
            "treatment_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_column("work_item_id")
        batch_op.drop_column("care_session_id")
