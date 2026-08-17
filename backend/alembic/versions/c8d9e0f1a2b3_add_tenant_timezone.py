"""add tenant timezone for business-day reporting

Revision ID: c8d9e0f1a2b3
Revises: f7a8b9c0d1e2
Create Date: 2026-08-17 14:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Africa/Cairo",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "timezone")
