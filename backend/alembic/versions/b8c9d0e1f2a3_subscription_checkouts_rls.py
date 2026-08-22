"""enforce RLS on subscription checkouts

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-22

Checkout records are server-owned but tenant-scoped.  Keep them behind the
same strict ENABLE + FORCE RLS contract as the rest of the tenant data.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    if "subscription_checkouts" not in inspector.get_table_names():
        raise RuntimeError(
            "subscription_checkouts table is required before installing RLS"
        )

    columns = {
        column["name"] for column in inspector.get_columns("subscription_checkouts")
    }
    if "tenant_id" not in columns:
        raise RuntimeError(
            "subscription_checkouts.tenant_id is required before installing RLS"
        )

    tenant_expr = (
        "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
    )
    bypass_expr = (
        "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
    )

    op.execute('ALTER TABLE "subscription_checkouts" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "subscription_checkouts" FORCE ROW LEVEL SECURITY')
    op.execute(
        'DROP POLICY IF EXISTS "subscription_checkouts_tenant_policy" '
        'ON "subscription_checkouts"'
    )
    op.execute(
        sa.text(
            f'''CREATE POLICY "subscription_checkouts_tenant_policy"
                ON "subscription_checkouts"
                FOR ALL
                USING (({tenant_expr}) OR {bypass_expr})
                WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    if "subscription_checkouts" not in sa.inspect(bind).get_table_names():
        return

    op.execute(
        'DROP POLICY IF EXISTS "subscription_checkouts_tenant_policy" '
        'ON "subscription_checkouts"'
    )
    op.execute('ALTER TABLE "subscription_checkouts" NO FORCE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "subscription_checkouts" DISABLE ROW LEVEL SECURITY')
