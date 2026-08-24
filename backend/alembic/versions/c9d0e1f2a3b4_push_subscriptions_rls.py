"""add push_subscriptions with RLS

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-24

Per-installation Web Push subscriptions (PWA master plan §12.2).

- One row per installation; re-subscription revokes the previous row for the
  same endpoint/device instead of overwriting a scalar token column.
- Long-lived delivery eligibility is bound to the stable session identity
  (`session_sid` = users.active_session_id), never to the rotating
  user_sessions.id row.
- Tenant-scoped like every end-user table; PostgreSQL gets the same
  ENABLE + FORCE RLS contract as the rest of the tenant data.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "push_subscriptions" in inspector.get_table_names():
        return

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("provider", sa.String(), nullable=False, server_default="web_push"),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh_key", sa.String(), nullable=False),
        sa.Column("auth_key", sa.String(), nullable=False),
        sa.Column("provider_token", sa.String(), nullable=True),
        sa.Column("device_installation_id", sa.String(), nullable=True),
        sa.Column("session_sid", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("browser_family", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"])
    op.create_index("ix_push_subscriptions_session_sid", "push_subscriptions", ["session_sid"])
    op.create_index(
        "ix_push_subscriptions_user_active",
        "push_subscriptions",
        ["user_id", "revoked_at"],
    )
    op.create_index(
        "ix_push_subscriptions_device_installation_id",
        "push_subscriptions",
        ["device_installation_id"],
    )

    if bind.dialect.name != "postgresql":
        return

    tenant_expr = (
        "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
    )
    bypass_expr = (
        "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
    )
    # Rows without a tenant (super-admin installations) are only visible to
    # their owner paths via the bypass flag; tenant sessions never see them.
    op.execute('ALTER TABLE "push_subscriptions" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "push_subscriptions" FORCE ROW LEVEL SECURITY')
    op.execute(
        'DROP POLICY IF EXISTS "push_subscriptions_tenant_policy" '
        'ON "push_subscriptions"'
    )
    op.execute(
        sa.text(
            f'''CREATE POLICY "push_subscriptions_tenant_policy"
                ON "push_subscriptions"
                FOR ALL
                USING (({tenant_expr}) OR {bypass_expr})
                WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "push_subscriptions" not in inspector.get_table_names():
        return

    if bind.dialect.name == "postgresql":
        op.execute(
            'DROP POLICY IF EXISTS "push_subscriptions_tenant_policy" '
            'ON "push_subscriptions"'
        )
        op.execute('ALTER TABLE "push_subscriptions" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "push_subscriptions" DISABLE ROW LEVEL SECURITY')

    op.drop_index("ix_push_subscriptions_device_installation_id", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_active", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_session_sid", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
