"""remove_legacy_ai_usage_logs

Revision ID: drop_ai_usage_logs
Revises: a1b2c3d4e5f6
Create Date: 2026-04-14 21:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "drop_ai_usage_logs"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # We do a safe drop.
    try:
        op.drop_table("ai_usage_logs")
    except Exception:
        print("Skipping drop of ai_usage_logs. Table might not exist.")


def downgrade() -> None:
    pass
