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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "treatments" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("treatments")}
        if "lab_choice" not in cols:
            op.add_column("treatments", sa.Column("lab_choice", sa.String(24), nullable=True))

    if "clinical_work_items" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("clinical_work_items")}
        if "lab_choice" not in cols:
            op.add_column("clinical_work_items", sa.Column("lab_choice", sa.String(24), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "clinical_work_items" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("clinical_work_items")}
        if "lab_choice" in cols:
            op.drop_column("clinical_work_items", "lab_choice")

    if "treatments" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("treatments")}
        if "lab_choice" in cols:
            op.drop_column("treatments", "lab_choice")
