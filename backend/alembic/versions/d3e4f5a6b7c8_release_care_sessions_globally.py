"""Release unified care sessions to all existing and future clinics.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7

This one-time product-policy change supersedes the former opt-in rollout.
Later administrative opt-outs remain authoritative; application startup must
not continually reset them. No patient, clinical or financial records change.
"""

from alembic import op
import sqlalchemy as sa

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Require the configured migration owner to see every override. This
        # does NOT bypass RLS: PostgreSQL raises instead of silently filtering
        # rows when the executing role lacks the required migration privilege.
        op.execute("SET LOCAL row_security = off")
    op.execute(sa.text("""
        INSERT INTO feature_flags (key, description, is_global_enabled, rollout_percentage)
        VALUES ('clinical_vnext_native_writes', 'Unified clinical session recording', true, 100)
        ON CONFLICT (key) DO UPDATE
        SET is_global_enabled = true, rollout_percentage = 100
    """))
    op.execute(sa.text("""
        UPDATE tenant_features SET is_enabled = true
        WHERE feature_key = 'clinical_vnext_native_writes'
    """))


def downgrade() -> None:
    # Data-policy activation has no schema to undo. Keep current operator
    # decisions intact; use the existing audited rollout/admin controls for
    # an intentional operational rollback, rather than disabling clinics as
    # a side effect of downgrading unrelated application code.
    pass
