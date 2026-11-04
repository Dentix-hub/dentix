"""persist commercial policy and tenant overrides

Revision ID: e4a5b6c7d8e9
Revises: d3e4f5a6b7c8
Create Date: 2026-11-04

PR-04: Additive schema for commercial policy persistence:
- subscription_plans: policy_revision (optimistic locking), billing_cycle_unit
- tenants: policy_revision (optimistic locking)
- commercial_tenant_overrides: tenant-scoped capability overrides with RLS, expiry, reason, and audit attribution
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "e4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Additive columns on subscription_plans
    if "subscription_plans" in tables:
        plan_cols = {c["name"] for c in inspector.get_columns("subscription_plans")}
        if "policy_revision" not in plan_cols:
            op.add_column(
                "subscription_plans",
                sa.Column("policy_revision", sa.Integer(), nullable=False, server_default="1"),
            )
        if "billing_cycle_unit" not in plan_cols:
            op.add_column(
                "subscription_plans",
                sa.Column("billing_cycle_unit", sa.String(20), nullable=False, server_default="month"),
            )

    # 2. Additive column on tenants
    if "tenants" in tables:
        tenant_cols = {c["name"] for c in inspector.get_columns("tenants")}
        if "policy_revision" not in tenant_cols:
            op.add_column(
                "tenants",
                sa.Column("policy_revision", sa.Integer(), nullable=False, server_default="1"),
            )

    # 3. Create commercial_tenant_overrides table
    if "commercial_tenant_overrides" not in tables:
        op.create_table(
            "commercial_tenant_overrides",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("capability_key", sa.String(64), nullable=False, index=True),
            sa.Column("override_value", sa.String(16), nullable=False),
            sa.Column("reason", sa.String(500), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_by_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "tenant_id",
                "capability_key",
                name="uq_commercial_tenant_override_tenant_key",
            ),
            sa.CheckConstraint(
                "override_value IN ('allow', 'deny', 'inherit')",
                name="ck_commercial_tenant_override_value",
            ),
        )

    # 4. Enforce RLS on commercial_tenant_overrides for PostgreSQL
    if is_postgres:
        tenant_expr = (
            "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        )
        bypass_expr = (
            "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
        )

        op.execute('ALTER TABLE "commercial_tenant_overrides" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "commercial_tenant_overrides" FORCE ROW LEVEL SECURITY')
        op.execute(
            'DROP POLICY IF EXISTS "commercial_tenant_overrides_tenant_policy" '
            'ON "commercial_tenant_overrides"'
        )
        op.execute(
            sa.text(
                f'''CREATE POLICY "commercial_tenant_overrides_tenant_policy"
                    ON "commercial_tenant_overrides"
                    FOR ALL
                    USING (({tenant_expr}) OR {bypass_expr})
                    WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if is_postgres and "commercial_tenant_overrides" in tables:
        op.execute(
            'DROP POLICY IF EXISTS "commercial_tenant_overrides_tenant_policy" '
            'ON "commercial_tenant_overrides"'
        )
        op.execute('ALTER TABLE "commercial_tenant_overrides" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "commercial_tenant_overrides" DISABLE ROW LEVEL SECURITY')

    if "commercial_tenant_overrides" in tables:
        op.drop_table("commercial_tenant_overrides")

    if "tenants" in tables:
        tenant_cols = {c["name"] for c in inspector.get_columns("tenants")}
        if "policy_revision" in tenant_cols:
            op.drop_column("tenants", "policy_revision")

    if "subscription_plans" in tables:
        plan_cols = {c["name"] for c in inspector.get_columns("subscription_plans")}
        if "billing_cycle_unit" in plan_cols:
            op.drop_column("subscription_plans", "billing_cycle_unit")
        if "policy_revision" in plan_cols:
            op.drop_column("subscription_plans", "policy_revision")
