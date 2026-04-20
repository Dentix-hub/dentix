"""add fcm_token to users

Revision ID: 4326f6d2f707
Revises: 
Create Date: 2026-04-20 01:21:44.020584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4326f6d2f707'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Only add if it doesn't already exist (Alembic doesn't natively support IF NOT EXISTS in op.add_column easily without raw SQL or custom logic)
    # But for a clean new migration, we use op.add_column
    op.add_column('users', sa.Column('fcm_token', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'fcm_token')
