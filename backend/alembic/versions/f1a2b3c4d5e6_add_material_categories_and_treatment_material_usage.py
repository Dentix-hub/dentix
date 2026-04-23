"""Add material_categories, treatment_material_usages, and update materials/weights

Revision ID: f1a2b3c4d5e6
Revises: e146e0d57b66
Create Date: 2026-04-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "4326f6d2f707"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create material_categories table
    op.create_table(
        "material_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=False),
        sa.Column("default_type", sa.String(), server_default="DIVISIBLE", nullable=True),
        sa.Column("default_unit", sa.String(), server_default="g", nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_en"),
    )
    op.create_index(op.f("ix_material_categories_id"), "material_categories", ["id"], unique=False)

    # 2. Add category_id and brand to materials
    op.add_column("materials", sa.Column("category_id", sa.Integer(), nullable=True))
    op.add_column("materials", sa.Column("brand", sa.String(), nullable=True))
    op.create_foreign_key("fk_materials_category_id", "materials", "material_categories", ["category_id"], ["id"])

    # 3. Add category_id to procedure_material_weights + make material_id nullable
    op.add_column("procedure_material_weights", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_proc_weights_category_id", "procedure_material_weights", "material_categories", ["category_id"], ["id"])

    # Make material_id nullable (was NOT NULL)
    op.alter_column("procedure_material_weights", "material_id", nullable=True)

    # Make tenant_id nullable to support global defaults (tenant_id=NULL)
    op.alter_column("procedure_material_weights", "tenant_id", nullable=True)

    # 4. Create treatment_material_usages table
    op.create_table(
        "treatment_material_usages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("treatment_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("weight_score", sa.Float(), server_default="1.0", nullable=True),
        sa.Column("quantity_used", sa.Float(), nullable=True),
        sa.Column("cost_calculated", sa.Float(), nullable=True),
        sa.Column("is_manual_override", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["treatment_id"], ["treatments.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["material_sessions.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_treatment_material_usages_id"), "treatment_material_usages", ["id"], unique=False)
    op.create_index(op.f("ix_treatment_material_usages_treatment_id"), "treatment_material_usages", ["treatment_id"], unique=False)


def downgrade() -> None:
    # Drop treatment_material_usages
    op.drop_index(op.f("ix_treatment_material_usages_treatment_id"), table_name="treatment_material_usages")
    op.drop_index(op.f("ix_treatment_material_usages_id"), table_name="treatment_material_usages")
    op.drop_table("treatment_material_usages")

    # Revert procedure_material_weights: material_id back to NOT NULL, drop category_id
    op.alter_column("procedure_material_weights", "tenant_id", nullable=False)
    op.alter_column("procedure_material_weights", "material_id", nullable=False)
    op.drop_constraint("fk_proc_weights_category_id", "procedure_material_weights", type_="foreignkey")
    op.drop_column("procedure_material_weights", "category_id")

    # Revert materials: drop category_id and brand
    op.drop_constraint("fk_materials_category_id", "materials", type_="foreignkey")
    op.drop_column("materials", "brand")
    op.drop_column("materials", "category_id")

    # Drop material_categories
    op.drop_index(op.f("ix_material_categories_id"), table_name="material_categories")
    op.drop_table("material_categories")
