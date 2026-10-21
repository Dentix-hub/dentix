"""add procedure_chart_styles table

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-10-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, Sequence[str], None] = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "procedure_chart_styles" not in existing_tables:
        op.create_table(
            "procedure_chart_styles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("procedure_name", sa.String(length=255), nullable=False),
            sa.Column("template", sa.String(length=32), nullable=False),
            sa.Column("color_key", sa.String(length=16), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "tenant_id", "procedure_name", name="uq_procedure_chart_styles_tenant_procedure"
            ),
            sa.CheckConstraint(
                "template IN ('REST_COMPOSITE', 'ENDO_RCT', 'PROS_CROWN', 'PROS_BRIDGE', 'IMPLANT_FIXTURE', 'IMPLANT_CROWN', 'SURG_EXTRACTION', 'MARKER', 'NONE')",
                name="ck_procedure_chart_styles_template",
            ),
            sa.CheckConstraint(
                "color_key IS NULL OR color_key IN ('blue', 'teal', 'green', 'lime', 'amber', 'orange', 'purple', 'indigo', 'pink', 'cyan', 'slate', 'brown')",
                name="ck_procedure_chart_styles_color_key",
            ),
            sa.CheckConstraint(
                "template != 'NONE' OR color_key IS NULL",
                name="ck_procedure_chart_styles_none_no_color",
            ),
        )
        op.create_index(
            "ix_procedure_chart_styles_id",
            "procedure_chart_styles",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_procedure_chart_styles_tenant_id",
            "procedure_chart_styles",
            ["tenant_id"],
            unique=False,
        )

    if bind.dialect.name == "postgresql":
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        op.execute('ALTER TABLE "procedure_chart_styles" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "procedure_chart_styles" FORCE ROW LEVEL SECURITY')
        op.execute('DROP POLICY IF EXISTS "procedure_chart_styles_tenant_policy" ON "procedure_chart_styles"')
        op.execute(
            f'''CREATE POLICY "procedure_chart_styles_tenant_policy" ON "procedure_chart_styles"
                FOR ALL
                USING ({tenant_expr})
                WITH CHECK ({tenant_expr})'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "procedure_chart_styles" in existing_tables:
        if bind.dialect.name == "postgresql":
            op.execute('DROP POLICY IF EXISTS "procedure_chart_styles_tenant_policy" ON "procedure_chart_styles"')
        op.drop_table("procedure_chart_styles")
