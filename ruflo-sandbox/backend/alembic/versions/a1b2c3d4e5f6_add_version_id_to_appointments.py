"""Add version_id to appointments for optimistic locking

Revision ID: a1b2c3d4e5f6
Revises: e0eb7ca469b9
Create Date: 2026-03-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'e0eb7ca469b9'
branch_labels = None
depends_on = None


def upgrade():
    # Use inspector to check for column existence
    from sqlalchemy.engine.reflection import Inspector
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c["name"] for c in inspector.get_columns("appointments")]
    
    # Add version_id column with default 1 for optimistic locking
    if "version_id" not in columns:
        op.add_column('appointments', sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'))



def downgrade():
    op.drop_column('appointments', 'version_id')
