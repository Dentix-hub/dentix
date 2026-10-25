"""seed onboarding_checklist feature flag

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b9c0d1e2f3a"
down_revision: Union[str, Sequence[str], None] = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "feature_flags" not in tables:
        return

    metadata = sa.MetaData()
    feature_flags = sa.Table(
        "feature_flags",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String, unique=True),
        sa.Column("description", sa.String),
        sa.Column("is_global_enabled", sa.Boolean),
        sa.Column("rollout_percentage", sa.Integer),
    )

    res = bind.execute(
        sa.select(feature_flags.c.id).where(feature_flags.c.key == "onboarding_checklist")
    ).first()
    if not res:
        op.bulk_insert(
            feature_flags,
            [
                {
                    "key": "onboarding_checklist",
                    "description": "Onboarding checklist and first-visit tooltips",
                    "is_global_enabled": True,
                    "rollout_percentage": 100,
                }
            ],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "feature_flags" in tables:
        op.execute("DELETE FROM feature_flags WHERE key = 'onboarding_checklist'")
