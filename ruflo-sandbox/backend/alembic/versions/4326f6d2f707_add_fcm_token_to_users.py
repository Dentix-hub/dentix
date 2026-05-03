"""add fcm_token to users

Revision ID: 4326f6d2f707
Revises: 
Create Date: 2026-04-20 01:21:44.020584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4326f6d2f707'
down_revision = 'e146e0d57b66'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy.engine.reflection import Inspector
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c["name"] for c in inspector.get_columns("users")]
    if "fcm_token" not in columns:
        op.add_column('users', sa.Column('fcm_token', sa.String(), nullable=True))



def downgrade():
    op.drop_column('users', 'fcm_token')
