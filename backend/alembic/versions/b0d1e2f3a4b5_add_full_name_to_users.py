"""add full_name to users

Revision ID: b0d1e2f3a4b5
Revises: f1a2b3c4d5e6
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b0d1e2f3a4b5'
down_revision = '6ce58b4d24ba'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy.engine.reflection import Inspector
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c["name"] for c in inspector.get_columns("users")]
    if "full_name" not in columns:
        op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'full_name')
