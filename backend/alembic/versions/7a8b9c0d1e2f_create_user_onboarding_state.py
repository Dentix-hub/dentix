"""create user_onboarding_state table

Revision ID: 7a8b9c0d1e2f
Revises: 6f7a8b9c0d1e
Create Date: 2026-10-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, Sequence[str], None] = "6f7a8b9c0d1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_onboarding_state" not in existing_tables:
        op.create_table(
            "user_onboarding_state",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("seen_tips", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("events", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "tenant_id", "user_id", name="uq_user_onboarding_state_tenant_user"
            ),
        )
        op.create_index(
            "ix_user_onboarding_state_id",
            "user_onboarding_state",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_user_onboarding_state_tenant_id",
            "user_onboarding_state",
            ["tenant_id"],
            unique=False,
        )
        op.create_index(
            "ix_user_onboarding_state_user_id",
            "user_onboarding_state",
            ["user_id"],
            unique=False,
        )

    if bind.dialect.name == "postgresql":
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        op.execute('ALTER TABLE "user_onboarding_state" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "user_onboarding_state" FORCE ROW LEVEL SECURITY')
        op.execute('DROP POLICY IF EXISTS "user_onboarding_state_tenant_policy" ON "user_onboarding_state"')
        op.execute(
            f'''CREATE POLICY "user_onboarding_state_tenant_policy" ON "user_onboarding_state"
                FOR ALL
                USING ({tenant_expr})
                WITH CHECK ({tenant_expr})'''
        )
        table = "user_onboarding_state"
        trigger_name = "trg_user_onboarding_state_user_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{trigger_name}"
                BEFORE INSERT OR UPDATE OF tenant_id, "user_id" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    'users', 'user_id', 'false'
                )'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_onboarding_state" in existing_tables:
        if bind.dialect.name == "postgresql":
            table = "user_onboarding_state"
            op.execute(f'DROP TRIGGER IF EXISTS "trg_user_onboarding_state_user_id_parent_tenant" ON "{table}"')
            op.execute('DROP POLICY IF EXISTS "user_onboarding_state_tenant_policy" ON "user_onboarding_state"')
        op.drop_table("user_onboarding_state")
