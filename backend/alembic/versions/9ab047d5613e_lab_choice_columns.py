"""Add nullable explicit laboratory choices without backfilling old records.

Revision ID: 9ab047d5613e
Revises: ed137fa8c304
"""
from alembic import op
import sqlalchemy as sa

revision = "9ab047d5613e"
down_revision = "ed137fa8c304"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("treatments", sa.Column("lab_choice", sa.String(24), nullable=True))
    op.add_column("clinical_work_items", sa.Column("lab_choice", sa.String(24), nullable=True))


def downgrade():
    op.drop_column("clinical_work_items", "lab_choice")
    op.drop_column("treatments", "lab_choice")
