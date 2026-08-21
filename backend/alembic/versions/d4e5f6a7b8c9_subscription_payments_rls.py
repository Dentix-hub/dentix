"""enforce RLS on subscription payments

Revision ID: d4e5f6a7b8c9
Revises: f2a4c6e8b0d1
Create Date: 2026-08-21

SubscriptionPayment is tenant-owned and has always carried tenant_id, but the
historical RLS migration predated the current parity audit and omitted this
table. Existing PostgreSQL databases therefore need an explicit forward-only
repair; historical migrations must not be rewritten.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "f2a4c6e8b0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    if "subscription_payments" not in inspector.get_table_names():
        raise RuntimeError("subscription_payments table is required before installing RLS")

    columns = {column["name"] for column in inspector.get_columns("subscription_payments")}
    if "tenant_id" not in columns:
        raise RuntimeError("subscription_payments.tenant_id is required before installing RLS")

    tenant_expr = (
        "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
    )
    bypass_expr = (
        "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
    )

    op.execute('ALTER TABLE "subscription_payments" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "subscription_payments" FORCE ROW LEVEL SECURITY')
    op.execute(
        'DROP POLICY IF EXISTS "subscription_payments_tenant_policy" '
        'ON "subscription_payments"'
    )
    op.execute(
        sa.text(
            f'''CREATE POLICY "subscription_payments_tenant_policy"
                ON "subscription_payments"
                FOR ALL
                USING (({tenant_expr}) OR {bypass_expr})
                WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    if "subscription_payments" not in inspector.get_table_names():
        return

    op.execute(
        'DROP POLICY IF EXISTS "subscription_payments_tenant_policy" '
        'ON "subscription_payments"'
    )
    op.execute('ALTER TABLE "subscription_payments" DISABLE ROW LEVEL SECURITY')
