"""add durable manual-renewal idempotency records

Revision ID: e2f3a4b5c6d7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_renewal_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_subscription_renewal_tenant_key"
        ),
    )
    op.create_index(
        "ix_subscription_renewal_requests_tenant_id",
        "subscription_renewal_requests",
        ["tenant_id"],
    )
    if op.get_bind().dialect.name == "postgresql":
        tenant = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        op.execute('ALTER TABLE "subscription_renewal_requests" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "subscription_renewal_requests" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'''CREATE POLICY "subscription_renewal_requests_tenant_policy"
                ON "subscription_renewal_requests" FOR ALL
                USING ({tenant}) WITH CHECK ({tenant})'''
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            'DROP POLICY IF EXISTS "subscription_renewal_requests_tenant_policy" '
            'ON "subscription_renewal_requests"'
        )
    op.drop_index(
        "ix_subscription_renewal_requests_tenant_id",
        table_name="subscription_renewal_requests",
    )
    op.drop_table("subscription_renewal_requests")
