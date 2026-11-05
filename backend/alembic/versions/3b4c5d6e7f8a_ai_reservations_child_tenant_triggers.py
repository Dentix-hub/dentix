"""add child tenant triggers for ai_reservations

Revision ID: 3b4c5d6e7f8a
Revises: 2a3b4c5d6e7f
Create Date: 2026-11-04

Ensure ai_reservations enforces parent-child tenant integrity for
window_id (ai_quota_windows) and user_id (users) in PostgreSQL via
dentix_assert_parent_tenant().
"""

from typing import Sequence, Union

from alembic import op


revision: str = "3b4c5d6e7f8a"
down_revision: Union[str, Sequence[str], None] = "2a3b4c5d6e7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        r"""
        DROP TRIGGER IF EXISTS "trg_ai_reservations_window_id_parent_tenant" ON "ai_reservations";
        CREATE TRIGGER "trg_ai_reservations_window_id_parent_tenant"
            BEFORE INSERT OR UPDATE OF tenant_id, "window_id" ON "ai_reservations"
            FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                'ai_quota_windows', 'window_id', 'false'
            );

        DROP TRIGGER IF EXISTS "trg_ai_reservations_user_id_parent_tenant" ON "ai_reservations";
        CREATE TRIGGER "trg_ai_reservations_user_id_parent_tenant"
            BEFORE INSERT OR UPDATE OF tenant_id, "user_id" ON "ai_reservations"
            FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                'users', 'user_id', 'true'
            );
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        """
        DROP TRIGGER IF EXISTS "trg_ai_reservations_window_id_parent_tenant" ON "ai_reservations";
        DROP TRIGGER IF EXISTS "trg_ai_reservations_user_id_parent_tenant" ON "ai_reservations";
        """
    )
