"""Persist browser session mode without changing existing sessions.

Revision ID: ed137fa8c304
Revises: 1e2f3a4b5c6d
"""
from alembic import op
import sqlalchemy as sa

revision = "ed137fa8c304"
down_revision = "1e2f3a4b5c6d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_sessions", sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column("user_sessions", "remember_me")
